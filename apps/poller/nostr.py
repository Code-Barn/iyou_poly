import asyncio
import hashlib
import json
import logging
import time
from typing import Any, Callable

from django.conf import settings

import coincurve
import websockets

logger = logging.getLogger(__name__)


def get_instance_keypair() -> tuple[coincurve.PrivateKey, str]:
    """Load the instance Nostr keypair from settings.

    Returns (private_key, x_only_pubkey_hex).
    If NOSTR_PRIVATE_KEY is not set, generates an ephemeral key (dev only).
    """
    privkey_hex = settings.NOSTR_PRIVATE_KEY
    if privkey_hex:
        private_key = coincurve.PrivateKey.from_hex(privkey_hex)
    else:
        private_key = coincurve.PrivateKey()
    x_only = private_key.public_key.format()[1:]
    return private_key, x_only.hex()


def make_event(
    kind: int,
    content: str,
    tags: list[list[str]],
    private_key: coincurve.PrivateKey,
    pubkey_hex: str,
) -> dict[str, Any]:
    """Construct and sign a Nostr event using Schnorr (secp256k1/BIP-340)."""
    created_at = int(time.time())
    serialized = json.dumps(
        [0, pubkey_hex, created_at, kind, tags, content],
        separators=(",", ":"),
        ensure_ascii=False,
    )
    event_id = hashlib.sha256(serialized.encode()).hexdigest()
    signature = private_key.sign_schnorr(bytes.fromhex(event_id)).hex()

    return {
        "id": event_id,
        "pubkey": pubkey_hex,
        "created_at": created_at,
        "kind": kind,
        "tags": tags,
        "content": content,
        "sig": signature,
    }


def make_poll_event(poll, private_key, pubkey_hex) -> dict[str, Any]:
    """Build kind:30023 Parameterized Replaceable Event for a poll."""
    options = list(poll.options.all())
    tags = [
        ["d", f"poll:{poll.id}"],
        ["geohash", poll.required_scope.value if poll.required_scope else ""],
        ["rule", poll.vote_power_rule, str(poll.vote_power_ratio)],
    ]
    for opt in options:
        tags.append(["p", opt.text])
    if poll.required_scope_type:
        tags.append(["scope_type", poll.required_scope_type.name])
    if poll.required_credential_type:
        tags.append(["credential_type", poll.required_credential_type.name])

    content = json.dumps({
        "title": poll.title,
        "description": poll.description,
        "poll_type": poll.poll_type,
        "is_active": poll.is_active,
        "is_proposal": poll.is_proposal,
        "options": [{"text": o.text, "votes": o.votes} for o in options],
    })
    return make_event(30023, content, tags, private_key, pubkey_hex)


def make_vote_event(vote, poll_id: int, private_key, pubkey_hex) -> dict[str, Any]:
    """Build kind:1111 immutable vote envelope.

    Outer container uses standard Nostr Schnorr (secp256k1) for relay transport.
    Inner content carries the voter's Ed25519 DID signature for application-level verification.
    """
    content = json.dumps({
        "poll_id": poll_id,
        "option_id": vote.option_id,
        "option_text": vote.option.text,
        "voter_did": vote.voter_did,
        "voter_ed25519_signature": vote.signature or "",
        "timestamp": vote.created_at.isoformat() if vote.created_at else None,
        "credential_cid": vote.credential_cid or "",
    })
    tags = [
        ["a", f"30023:poll:{poll_id}"],
        ["e", vote.signature or ""],
        ["p", vote.voter_did],
    ]
    return make_event(1111, content, tags, private_key, pubkey_hex)


async def _publish_to_relay(relay_url: str, event: dict[str, Any]) -> bool:
    """Publish a single event to one relay via WebSocket (NIP-01)."""
    try:
        async with websockets.connect(relay_url, open_timeout=5) as ws:
            msg = json.dumps(["EVENT", event])
            await ws.send(msg)
            response = await asyncio.wait_for(ws.recv(), timeout=10)
            resp = json.loads(response)
            if resp[0] == "OK" and resp[1] == event["id"]:
                return True
            logger.warning("Relay %s rejected event: %s", relay_url, resp)
            return False
    except Exception as e:
        logger.error("Failed to publish to relay %s: %s", relay_url, e)
        return False


def publish_event(event: dict[str, Any]) -> list[str]:
    """Publish a Nostr event to all configured relays. Returns accepted relays."""
    if not settings.NOSTR_ENABLED:
        logger.debug("Nostr disabled; skipping publish")
        return []

    relays = settings.NOSTR_RELAYS

    async def _publish_all():
        results = await asyncio.gather(
            *[_publish_to_relay(r, event) for r in relays],
            return_exceptions=True,
        )
        return [r for r, ok in zip(relays, results) if ok is True]

    return asyncio.run(_publish_all())


def publish_poll(poll) -> list[str]:
    """Broadcast poll definition as kind:30023 to all Nostr relays."""
    try:
        private_key, pubkey_hex = get_instance_keypair()
        event = make_poll_event(poll, private_key, pubkey_hex)
        return publish_event(event)
    except Exception as e:
        logger.error("Failed to publish poll event: %s", e)
        return []


def publish_vote(vote, poll_id: int) -> list[str]:
    """Broadcast vote envelope as kind:1111 to all Nostr relays."""
    try:
        private_key, pubkey_hex = get_instance_keypair()
        event = make_vote_event(vote, poll_id, private_key, pubkey_hex)
        return publish_event(event)
    except Exception as e:
        logger.error("Failed to publish vote event: %s", e)
        return []


async def subscribe_loop(
    relay_url: str,
    kinds: list[int],
    on_event: Callable[[dict[str, Any]], None],
    sub_id: str = "iyou_poly",
):
    """Long-lived subscription to a Nostr relay (NIP-01 REQ).

    Intended for use in the gossip worker management command.
    Reconnects on failure with a 30s backoff.
    """
    while True:
        try:
            async with websockets.connect(relay_url, open_timeout=10) as ws:
                filter_msg = json.dumps(["REQ", sub_id, {"kinds": kinds}])
                await ws.send(filter_msg)
                async for raw in ws:
                    try:
                        msg = json.loads(raw)
                        if msg[0] == "EVENT" and msg[1].get("kind") in kinds:
                            on_event(msg[1])
                    except (json.JSONDecodeError, IndexError):
                        continue
        except Exception as e:
            logger.error(
                "Subscription to %s failed: %s; reconnecting in 30s", relay_url, e
            )
            await asyncio.sleep(30)
