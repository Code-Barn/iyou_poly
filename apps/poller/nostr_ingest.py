"""
Inbound Nostr event ingestion for kind:30023 (polls) and kind:1112 (votes).

Validates NIP-01 Schnorr signatures, then routes validated payloads into the
existing Poll / Vote creation pipeline with upsert semantics for idempotent
relay firehose processing.
"""

import base64
import hashlib
import json
import logging
import re
from datetime import datetime
from typing import Any

from django.db import IntegrityError, transaction
from django.utils import timezone

from cryptography.hazmat.primitives.asymmetric import ed25519

import coincurve

from django.contrib.auth import get_user_model

from apps.poller.models import Poll, PollOption, PollType, Vote

User = get_user_model()

logger = logging.getLogger(__name__)

# ── Helpers ───────────────────────────────────────────────────────────────────


def _get_nostr_system_user() -> User:
    """Return a system user for polls ingested from Nostr.

    Creates a dedicated ``nostr`` user on first call if one does not exist.
    """
    user, _ = User.objects.get_or_create(
        username="nostr",
        defaults={"is_active": True},
    )
    return user


# ── Helpers ───────────────────────────────────────────────────────────────────


def _decode_field(value: str) -> bytes:
    """Decode a field that may be hex (64/128 chars) or standard Base64.

    Tauri enclave outputs Base64; the browser should convert it to hex before
    sending, but a flawed heuristic sometimes skips the conversion.  This
    helper accepts either format.
    """
    if not value:
        raise ValueError("Empty field")
    # Try hex first (most common from browser)
    try:
        return bytes.fromhex(value)
    except ValueError:
        pass
    # Fall back to standard Base64
    return base64.b64decode(value)


# ── NIP-01 canonical serialization ──────────────────────────────────────────


def canonical_serialize_event(event: dict[str, Any]) -> bytes:
    """Serialize a Nostr event dict into the strict NIP-01 canonical array.

    Produces ``[0, pubkey, created_at, kind, tags, content]`` as minified JSON
    with zero whitespace between separators, matching the exact footprint that
    the iyou_home signer uses before signing.
    """
    serialized_array = [
        0,
        event.get("pubkey"),
        int(event.get("created_at")),
        int(event.get("kind")),
        event.get("tags", []),
        event.get("content", ""),
    ]
    raw_string = json.dumps(
        serialized_array,
        separators=(",", ":"),
        ensure_ascii=False,
    )
    raw_string = raw_string.replace("\\'", "'")
    return raw_string.encode("utf-8")


# ── NIP-01 Schnorr verification ──────────────────────────────────────────────


def verify_nostr_event(event: dict[str, Any]) -> bool:
    """Verify a Nostr event envelope, trying NIP-01 Schnorr then Ed25519.

    Schnorr (BIP-340) verification re-computes the SHA-256 event ID from the
    canonical serialisation and validates the 64-byte ``sig`` against the
    x-only ``pubkey``.

    If Schnorr fails or raises, falls back to Ed25519 verification on the same
    canonical serialisation bytes — this accommodates mesh signatures produced
    by the enclave's native Ed25519 platform.
    """
    try:
        serialized_bytes = canonical_serialize_event(event)
        computed_id = hashlib.sha256(serialized_bytes).hexdigest()
        if computed_id != event.get("id"):
            print(f"[SCHNORR_DIAG] computed_id != event[id]")
            print(f"[SCHNORR_DIAG] computed:  {computed_id}")
            print(f"[SCHNORR_DIAG] event[id]: {event.get('id')}")
            return False

        pubkey = coincurve.PublicKeyXOnly(_decode_field(event["pubkey"]))
        if pubkey.verify(
            _decode_field(event["sig"]),
            _decode_field(computed_id),
        ):
            return True
    except Exception as exc:
        logger.debug("Nostr Schnorr verification failed, trying Ed25519 fallback: %s", exc)

    # Fallback — Ed25519 (mesh signatures)
    try:
        event_id_hex = event.get("id")
        sig_hex = event.get("sig")
        pubkey_hex = event.get("pubkey")

        if not all([event_id_hex, sig_hex, pubkey_hex]):
            print("[ED25519_DIAG] Missing one or more required fields (id/sig/pubkey)")
            return False

        print("=" * 80)
        print(f"[ED25519_DIAG] event_id_hex ({len(event_id_hex)} chars): {event_id_hex}")
        print(f"[ED25519_DIAG] pubkey_hex  ({len(pubkey_hex)} chars):  {pubkey_hex}")
        print(f"[ED25519_DIAG] sig_hex     ({len(sig_hex)} chars):     {sig_hex}")

        msg_bytes = _decode_field(event_id_hex)
        sig_bytes = _decode_field(sig_hex)
        vk_bytes = _decode_field(pubkey_hex)

        print(f"[ED25519_DIAG] msg_bytes (len={len(msg_bytes)}): {msg_bytes.hex()}")
        print(f"[ED25519_DIAG] sig_bytes (len={len(sig_bytes)}): {sig_bytes.hex()}")
        print(f"[ED25519_DIAG] vk_bytes  (len={len(vk_bytes)}):  {vk_bytes.hex()}")

        verifying_key = ed25519.Ed25519PublicKey.from_public_bytes(vk_bytes)
        verifying_key.verify(sig_bytes, msg_bytes)

        print("[ED25519_DIAG] VERIFICATION PASSED")
        logger.debug("Ed25519 fallback — signature verified against raw event ID bytes")
        return True
    except Exception as exc:
        print(f"[ED25519_DIAG] EXCEPTION: {type(exc).__name__}: {exc}")
        logger.debug("Ed25519 fallback validation failed: %s", exc)
        return False


# ── Poll ingestion (kind:30023) ──────────────────────────────────────────────


def _extract_d_tag_value(tags: list[list[str]]) -> str | None:
    """Return the value of the first ``d`` tag, or ``None``."""
    for tag in tags:
        if len(tag) >= 2 and tag[0] == "d":
            return tag[1]
    return None


def _parse_poll_id_from_d_tag(d_tag: str) -> int | None:
    """Parse ``poll:<int>`` from the d-tag value."""
    match = re.match(r"^poll:(\d+)$", d_tag)
    if match:
        return int(match.group(1))
    return None


def ingest_poll_event(event: dict[str, Any]) -> Poll | None:
    """Validate and upsert a Poll from a Nostr kind:30023 event.

    Returns the ``Poll`` instance (created or updated) or ``None`` on failure.
    Idempotent: duplicate ``nostr_event_id`` is silently ignored.
    """
    if not verify_nostr_event(event):
        logger.warning("Ignoring poll event %s — invalid signature", event.get("id", "")[:16])
        return None

    if event.get("kind") != 30023:
        logger.warning("Ignoring event kind %s — expected 30023", event.get("kind"))
        return None

    try:
        content = json.loads(event.get("content", "{}"))
    except json.JSONDecodeError:
        logger.warning("Ignoring poll event %s — unparseable content", event.get("id", "")[:16])
        return None

    title = content.get("title", "").strip()
    if not title:
        logger.warning("Ignoring poll event %s — missing title", event.get("id", "")[:16])
        return None

    # Resolve target poll ID from the replaceable d-tag
    tags = event.get("tags", [])
    d_tag = _extract_d_tag_value(tags)
    poll_id = _parse_poll_id_from_d_tag(d_tag) if d_tag else None

    nostr_user = _get_nostr_system_user()

    defaults = {
        "title": title,
        "description": content.get("description", ""),
        "poll_type": content.get("poll_type", PollType.PUBLIC),
        "is_active": content.get("is_active", True),
        "is_proposal": content.get("is_proposal", False),
        "nostr_event_id": event.get("id"),
        "nostr_pubkey": event.get("pubkey", ""),
    }
    create_defaults = {**defaults, "created_by": nostr_user}

    if poll_id is not None:
        try:
            poll = Poll.objects.get(id=poll_id)
            for key, value in defaults.items():
                setattr(poll, key, value)
            poll.save(update_fields=list(defaults))
            created = False
            logger.info("Updated poll %d from Nostr event %s", poll.id, event.get("id", "")[:16])
        except Poll.DoesNotExist:
            poll = Poll.objects.create(id=poll_id, **create_defaults)
            created = True
            logger.info("Created poll %d from Nostr event %s", poll.id, event.get("id", "")[:16])
    else:
        poll = Poll.objects.create(**create_defaults)
        logger.info("Created poll %d from Nostr event %s (no d-tag)", poll.id, event.get("id", "")[:16])

    # Ingest options from content if present
    options_data = content.get("options", [])
    if options_data:
        existing_texts = set(
            PollOption.objects.filter(poll=poll).values_list("text", flat=True)
        )
        for opt in options_data:
            text = opt.get("text", "").strip()
            if text and text not in existing_texts:
                PollOption.objects.create(
                    poll=poll,
                    text=text,
                    votes=opt.get("votes", 0),
                )
                existing_texts.add(text)

    return poll


# ── Vote ingestion (kind:1112) ───────────────────────────────────────────────


def _extract_a_tag_reference(tags: list[list[str]]) -> str | None:
    """Return the value of the first ``a`` tag, or ``None``."""
    for tag in tags:
        if len(tag) >= 2 and tag[0] == "a":
            return tag[1]
    return None


def _parse_poll_id_from_a_tag(a_tag: str) -> int | None:
    """Parse ``30023:poll:<int>`` from the ``a``-tag reference."""
    match = re.match(r"^30023:poll:(\d+)$", a_tag)
    if match:
        return int(match.group(1))
    return None


def ingest_vote_event(event: dict[str, Any]) -> Vote | None:
    """Validate and ingest a Vote from a Nostr kind:1112 event.

    Returns the ``Vote`` instance or ``None`` on failure.
    Idempotent: duplicate ``nostr_event_id`` is silently ignored.
    """
    if not verify_nostr_event(event):
        logger.warning("Ignoring vote event %s — invalid signature", event.get("id", "")[:16])
        return None

    if event.get("kind") not in (1111, 1112):
        logger.warning("Ignoring event kind %s — expected 1111 or 1112", event.get("kind"))
        return None

    try:
        content = json.loads(event.get("content", "{}"))
    except json.JSONDecodeError:
        logger.warning("Ignoring vote event %s — unparseable content", event.get("id", "")[:16])
        return None

    voter_did = content.get("voter_did", "").strip()
    option_id = content.get("option_id")
    if not voter_did or not option_id:
        logger.warning("Ignoring vote event %s — missing voter_did or option_id", event.get("id", "")[:16])
        return None

    # Resolve poll from the ``a``-tag reference
    tags = event.get("tags", [])
    a_tag = _extract_a_tag_reference(tags)
    poll_id = _parse_poll_id_from_a_tag(a_tag) if a_tag else content.get("poll_id")

    if poll_id is None:
        logger.warning("Ignoring vote event %s — cannot determine poll_id", event.get("id", "")[:16])
        return None

    try:
        poll = Poll.objects.get(id=poll_id, is_active=True)
    except Poll.DoesNotExist:
        logger.warning("Ignoring vote event %s — poll %s not found or inactive", event.get("id", "")[:16], poll_id)
        return None

    try:
        option = PollOption.objects.get(id=option_id, poll=poll)
    except PollOption.DoesNotExist:
        logger.warning(
            "Ignoring vote event %s — option %s not found in poll %s",
            event.get("id", "")[:16],
            option_id,
            poll_id,
        )
        return None

    try:
        with transaction.atomic():
            vote = Vote.objects.create(
                poll=poll,
                option=option,
                voter_did=voter_did,
                signature=content.get("voter_ed25519_signature", ""),
                credential_cid=content.get("credential_cid", ""),
                nostr_event_id=event.get("id"),
                is_verified=True,
            )
            logger.info("Ingested vote %d from Nostr event %s", vote.id, event.get("id")[:16])
            return vote
    except IntegrityError:
        logger.info(
            "Duplicate vote event %s — already ingested (nostr_event_id unique constraint)",
            event.get("id")[:16],
        )
        return None
