"""Tests for Nostr event ingestion (apps/poller/nostr_ingest.py).

Covers NIP-01 verification, poll upsert, vote ingestion, and idempotent
duplicate rejection via database unique constraints.
"""

import json
from unittest.mock import patch

import coincurve

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from apps.poller.models import Poll, PollOption, PollType, TemporalPollType, Vote
from apps.poller.nostr_ingest import (
    canonical_serialize_event,
    ingest_poll_event,
    ingest_vote_event,
    verify_nostr_event,
)
from apps.core.verification import _b58encode

User = get_user_model()


def _make_nostr_event(
    kind: int = 30023,
    content: dict | None = None,
    d_tag: str | None = None,
    a_tag: str | None = None,
    private_key: coincurve.PrivateKey | None = None,
    created_at: int | None = None,
) -> tuple[dict, coincurve.PrivateKey]:
    """Build and sign a Nostr event for testing.

    Args:
        kind: Nostr event kind (default 30023).
        content: Event content dict.
        d_tag: Optional ``d`` tag value.
        a_tag: Optional ``a`` tag value.
        private_key: Key to sign with (generated fresh if not given).
        created_at: Explicit Unix timestamp (defaults to ``time.time()``).

    Returns ``(event_dict, private_key)``.
    """
    import hashlib
    import time

    if private_key is None:
        private_key = coincurve.PrivateKey()

    secret_bytes = bytes.fromhex(private_key.to_hex())
    xonly_pk = coincurve.PublicKeyXOnly.from_secret(secret_bytes)
    pubkey_hex = xonly_pk.format().hex()

    tags = []
    if d_tag is not None:
        tags.append(["d", d_tag])
    if a_tag is not None:
        tags.append(["a", a_tag])

    now = created_at if created_at is not None else int(time.time())
    serialized = json.dumps(
        [0, pubkey_hex, now, kind, tags, json.dumps(content or {})],
        separators=(",", ":"),
        ensure_ascii=False,
    )
    event_id = hashlib.sha256(serialized.encode()).hexdigest()
    sig = private_key.sign_schnorr(bytes.fromhex(event_id)).hex()

    event = {
        "id": event_id,
        "pubkey": pubkey_hex,
        "created_at": now,
        "kind": kind,
        "tags": tags,
        "content": json.dumps(content or {}),
        "sig": sig,
    }
    return event, private_key


class NostrIngestionTests(TestCase):
    """Tests for the nostr_ingest module functions."""

    def setUp(self):
        self.user = User.objects.create_user(username="nostr_creator")
        self.sk = coincurve.PrivateKey()
        self.secret = bytes.fromhex(self.sk.to_hex())
        self.xonly_pk = coincurve.PublicKeyXOnly.from_secret(self.secret)

    # ── NIP-01 verification ──────────────────────────────────────────────

    def test_verify_valid_event(self):
        """A properly signed Nostr event passes verification."""
        event, _ = _make_nostr_event(kind=30023, content={"title": "Test"})
        self.assertTrue(verify_nostr_event(event))

    def test_verify_rejects_tampered_id(self):
        """Changing the event ID after signing fails verification."""
        event, _ = _make_nostr_event(kind=30023, content={"title": "Test"})
        event["id"] = "00" + event["id"][2:]
        self.assertFalse(verify_nostr_event(event))

    def test_verify_rejects_tampered_content(self):
        """Changing the content after signing fails verification."""
        event, _ = _make_nostr_event(kind=30023, content={"title": "Test"})
        event["content"] = json.dumps({"title": "Tampered"})
        self.assertFalse(verify_nostr_event(event))

    def test_verify_rejects_wrong_pubkey(self):
        """An event signed by a different key fails verification."""
        event, _ = _make_nostr_event(kind=30023, content={"title": "Test"})
        wrong_sk = coincurve.PrivateKey()
        wrong_secret = bytes.fromhex(wrong_sk.to_hex())
        wrong_xonly = coincurve.PublicKeyXOnly.from_secret(wrong_secret)
        event["pubkey"] = wrong_xonly.format().hex()
        self.assertFalse(verify_nostr_event(event))

    def test_verify_coerces_numeric_content(self):
        """An event with numeric content passes after type coercion.

        Regression test: if ``content`` arrives as a JSON number (``123``)
        instead of a string (``"123"``), the coercion guard in
        ``verify_nostr_event`` casts it to ``str()`` before canonical
        serialisation so the computed hash matches the signer's intent.
        """
        sk = coincurve.PrivateKey()
        secret = bytes.fromhex(sk.to_hex())
        xonly_pk = coincurve.PublicKeyXOnly.from_secret(secret)
        pubkey_hex = xonly_pk.format().hex()

        import hashlib
        import time
        now = int(time.time())

        # Sign over content as the string "123" (the correct NIP-01 encoding)
        serialized = json.dumps(
            [0, pubkey_hex, now, 30023, [], "123"],
            separators=(",", ":"),
            ensure_ascii=False,
        )
        event_id = hashlib.sha256(serialized.encode()).hexdigest()
        sig = sk.sign_schnorr(bytes.fromhex(event_id)).hex()

        # Feed the event with content as int — simulates a JSON wire-format slip
        event = {
            "id": event_id,
            "pubkey": pubkey_hex,
            "created_at": now,
            "kind": 30023,
            "tags": [],
            "content": 123,  # <-- number, not string
            "sig": sig,
        }
        self.assertTrue(verify_nostr_event(event))
        # Guard mutates the dict in-place
        self.assertIsInstance(event["content"], str)
        self.assertEqual(event["content"], "123")

    def test_verify_coercion_is_idempotent(self):
        """Passing already-string content through the guard is a no-op."""
        event, _ = _make_nostr_event(kind=30023, content={"title": "Test"})
        original_content = event["content"]
        self.assertTrue(verify_nostr_event(event))
        self.assertEqual(event["content"], original_content)

    # ── Poll ingestion ───────────────────────────────────────────────────

    def test_ingest_poll_creates_new_poll(self):
        """A valid kind:30023 event creates a new Poll."""
        event, _ = _make_nostr_event(kind=30023, content={
            "title": "Nostr Poll",
            "description": "From the relay",
            "poll_type": "public",
            "is_active": True,
            "options": [{"text": "Yes"}, {"text": "No"}],
        })
        poll = ingest_poll_event(event)
        self.assertIsNotNone(poll)
        self.assertEqual(poll.title, "Nostr Poll")
        self.assertEqual(poll.description, "From the relay")
        self.assertEqual(poll.poll_type, "public")
        self.assertTrue(poll.is_active)
        self.assertEqual(poll.options.count(), 2)
        self.assertEqual(poll.nostr_event_id, event["id"])

    def test_ingest_poll_updates_existing_via_d_tag(self):
        """A kind:30023 with d-tag ``poll:{id}`` upserts an existing poll."""
        existing = Poll.objects.create(
            title="Original",
            created_by=self.user,
            poll_type=PollType.PUBLIC,
        )
        event, _ = _make_nostr_event(
            kind=30023,
            content={"title": "Updated via Nostr"},
            d_tag=f"poll:{existing.id}",
        )
        poll = ingest_poll_event(event)
        self.assertIsNotNone(poll)
        self.assertEqual(poll.id, existing.id)
        self.assertEqual(poll.title, "Updated via Nostr")

    def test_ingest_poll_without_d_tag_creates_new(self):
        """A kind:30023 without a d-tag creates a fresh poll (no upsert)."""
        event, _ = _make_nostr_event(kind=30023, content={"title": "Fresh Poll"})
        poll = ingest_poll_event(event)
        self.assertIsNotNone(poll)
        self.assertEqual(poll.title, "Fresh Poll")

    @patch("apps.poller.nostr_ingest.verify_nostr_event", return_value=False)
    def test_ingest_poll_rejects_invalid_signature(self, _mock_verify):
        """An event with an invalid signature is rejected."""
        event, _ = _make_nostr_event(kind=30023, content={"title": "Bad"})
        result = ingest_poll_event(event)
        self.assertIsNone(result)

    def test_ingest_binds_to_verified_sovereign_identity(self):
        """A poll event whose secp256k1 x-only pubkey matches the Ed25519
        key bytes embedded in a User's ``did:key:z6M...`` username binds
        the poll's ``created_by`` to that User instead of the ``nostr``
        fallback."""
        sk = coincurve.PrivateKey()
        secret_bytes = bytes.fromhex(sk.to_hex())
        xonly_pk = coincurve.PublicKeyXOnly.from_secret(secret_bytes)
        secp256k1_pubkey_bytes = xonly_pk.format()

        multicodec = b"\xed" + secp256k1_pubkey_bytes
        did_username = "did:key:z" + _b58encode(multicodec)
        user = User.objects.create_user(username=did_username)

        event, _ = _make_nostr_event(
            kind=30023,
            content={"title": "Sovereign-Bound Poll", "options": [{"text": "A"}]},
            private_key=sk,
        )

        poll = ingest_poll_event(event)
        self.assertIsNotNone(poll)
        self.assertEqual(poll.created_by.id, user.id)
        self.assertEqual(poll.created_by.username, did_username)

    # ── Clock-skew resilience ────────────────────────────────────────────

    def test_ingest_tolerates_acceptable_clock_skew(self):
        """An event timestamped up to 60s in the future (within the 900s
        grace window) is ingested successfully. A vote event timestamped
        60s past the poll's close is also accepted."""
        import time

        now = int(time.time())

        # ── Future-dated poll event (within grace) ───────────────────────
        future_event, _ = _make_nostr_event(
            kind=30023,
            content={"title": "Future Poll", "options": [{"text": "A"}]},
            created_at=now + 60,
        )
        self.assertTrue(verify_nostr_event(future_event))
        poll = ingest_poll_event(future_event)
        self.assertIsNotNone(poll)
        self.assertEqual(poll.title, "Future Poll")

        # ── Vote event just past poll ends_at (within grace) ──────────
        ends_at_dt = timezone.now() - timezone.timedelta(minutes=5)
        poll_with_end = Poll.objects.create(
            title="Closing Poll",
            created_by=self.user,
            poll_type=PollType.PUBLIC,
            temporal_type=TemporalPollType.TIMED,
            ends_at=ends_at_dt,
        )
        option = PollOption.objects.create(poll=poll_with_end, text="Yes")

        past_event, _ = _make_nostr_event(
            kind=1112,
            created_at=int(ends_at_dt.timestamp()) + 60,
            content={
                "poll_id": poll_with_end.id,
                "option_id": option.id,
                "voter_did": "did:key:z6Mskew",
            },
            a_tag=f"30023:poll:{poll_with_end.id}",
        )
        vote = ingest_vote_event(past_event)
        self.assertIsNotNone(vote)
        self.assertEqual(vote.poll_id, poll_with_end.id)
        self.assertEqual(vote.option_id, option.id)

    # ── Vote ingestion ───────────────────────────────────────────────────

    def test_ingest_vote_creates_vote(self):
        """A valid kind:1112 event creates a new Vote."""
        poll = Poll.objects.create(
            title="Votable Poll",
            created_by=self.user,
            poll_type=PollType.PUBLIC,
            temporal_type=TemporalPollType.ONGOING,
        )
        option = PollOption.objects.create(poll=poll, text="Option A")
        event, _ = _make_nostr_event(
            kind=1112,
            content={
                "poll_id": poll.id,
                "option_id": option.id,
                "voter_did": "did:key:z6Mtest",
                "voter_ed25519_signature": "ab" * 32,
            },
            a_tag=f"30023:poll:{poll.id}",
        )
        vote = ingest_vote_event(event)
        self.assertIsNotNone(vote)
        self.assertEqual(vote.poll_id, poll.id)
        self.assertEqual(vote.option_id, option.id)
        self.assertEqual(vote.voter_did, "did:key:z6Mtest")
        self.assertEqual(vote.nostr_event_id, event["id"])

    # ── Idempotent duplicate rejection ───────────────────────────────────

    def test_duplicate_poll_event_is_idempotent(self):
        """Ingesting the same poll event twice returns the same poll."""
        existing = Poll.objects.create(
            title="Original",
            created_by=self.user,
            poll_type=PollType.PUBLIC,
        )
        event, _ = _make_nostr_event(
            kind=30023,
            content={"title": "Dup Test"},
            d_tag=f"poll:{existing.id}",
        )
        first = ingest_poll_event(event)
        second = ingest_poll_event(event)
        self.assertIsNotNone(first)
        self.assertIsNotNone(second)
        self.assertEqual(first.id, second.id)
        self.assertEqual(Poll.objects.filter(nostr_event_id=event["id"]).count(), 1)

    def test_duplicate_vote_event_is_idempotent(self):
        """Ingesting the same vote event twice silently returns None."""
        poll = Poll.objects.create(
            title="Idempotent Poll",
            created_by=self.user,
            poll_type=PollType.PUBLIC,
            temporal_type=TemporalPollType.ONGOING,
        )
        option = PollOption.objects.create(poll=poll, text="Option A")
        event, _ = _make_nostr_event(
            kind=1112,
            content={
                "poll_id": poll.id,
                "option_id": option.id,
                "voter_did": "did:key:z6Mdup",
                "voter_ed25519_signature": "cd" * 32,
            },
            a_tag=f"30023:poll:{poll.id}",
        )
        first = ingest_vote_event(event)
        self.assertIsNotNone(first)
        # Second ingest returns None due to unique constraint on nostr_event_id
        second = ingest_vote_event(event)
        self.assertIsNone(second)
        self.assertEqual(Vote.objects.filter(nostr_event_id=event["id"]).count(), 1)


class NostrIngestWebhookTests(TestCase):
    """Tests for the NostrIngestWebhook REST endpoint."""

    def setUp(self):
        self.user = User.objects.create_user(username="webhook_tester")
        self.sk = coincurve.PrivateKey()
        self.secret = bytes.fromhex(self.sk.to_hex())
        self.xonly_pk = coincurve.PublicKeyXOnly.from_secret(self.secret)

    def _post_event(self, event: dict, expected_status: int = 201) -> dict:
        url = reverse("nostr_ingest")
        resp = self.client.post(
            url,
            data=json.dumps(event),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, expected_status)
        return resp.json()

    def test_webhook_accepts_poll_event(self):
        """POST a valid poll event returns 201 with poll details."""
        event, _ = _make_nostr_event(kind=30023, content={
            "title": "Webhook Poll",
            "options": [{"text": "A"}],
        })
        data = self._post_event(event)
        self.assertTrue(data["valid"])
        self.assertIn("poll_id", data["details"])
        self.assertEqual(data["details"]["nostr_event_id"], event["id"])

    def test_webhook_accepts_vote_event(self):
        """POST a valid vote event returns 201 with vote details."""
        poll = Poll.objects.create(
            title="Webhook Vote Poll",
            created_by=self.user,
            poll_type=PollType.PUBLIC,
            temporal_type=TemporalPollType.ONGOING,
        )
        option = PollOption.objects.create(poll=poll, text="A")
        event, _ = _make_nostr_event(
            kind=1112,
            content={
                "poll_id": poll.id,
                "option_id": option.id,
                "voter_did": "did:key:z6Mwebhook",
            },
            a_tag=f"30023:poll:{poll.id}",
        )
        data = self._post_event(event)
        self.assertTrue(data["valid"])
        self.assertIn("vote_id", data["details"])
        self.assertEqual(data["details"]["nostr_event_id"], event["id"])

    def test_webhook_rejects_missing_kind(self):
        """POST without kind returns 400."""
        resp = self.client.post(
            reverse("nostr_ingest"),
            data=json.dumps({"foo": "bar"}),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 400)

    def test_webhook_rejects_unsupported_kind(self):
        """POST with unsupported kind returns 400."""
        event, _ = _make_nostr_event(kind=9999, content={"foo": "bar"})
        resp = self.client.post(
            reverse("nostr_ingest"),
            data=json.dumps(event),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 400)
