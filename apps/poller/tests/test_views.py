# Copyright (C) 2026 David Byers dba Byers Brands
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <https://www.gnu.org/licenses/>.

import json
from unittest.mock import patch

from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
)

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from apps.core.verification import _b58encode
from apps.poller.models import (
    Poll,
    PollOption,
    PollType,
    TemporalPollType,
    TrustedIssuer,
    Vote,
)
from apps.poller.serializers import PollResultsSerializer

User = get_user_model()

_no_session_refresh = override_settings(
    MIDDLEWARE=[
        "debug_toolbar.middleware.DebugToolbarMiddleware",
        "django.middleware.security.SecurityMiddleware",
        "django.contrib.sessions.middleware.SessionMiddleware",
        "django.middleware.common.CommonMiddleware",
        "django.middleware.csrf.CsrfViewMiddleware",
        "django.contrib.auth.middleware.AuthenticationMiddleware",
        "django.contrib.messages.middleware.MessageMiddleware",
        "django.middleware.clickjacking.XFrameOptionsMiddleware",
    ]
)


class PollListViewTests(TestCase):

    def test_poll_list_publicly_accessible(self):
        response = self.client.get(reverse("poll_list"))
        self.assertEqual(response.status_code, 200)

    def test_poll_list_shows_polls(self):
        user = User.objects.create_user(username="creator")
        Poll.objects.create(
            title="Visible Poll",
            created_by=user,
            poll_type=PollType.PUBLIC,
        )
        response = self.client.get(reverse("poll_list"))
        self.assertContains(response, "Visible Poll")


class PollDetailViewTests(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(username="creator")
        self.poll = Poll.objects.create(
            title="Detail Test Poll",
            created_by=self.user,
            poll_type=PollType.PUBLIC,
        )
        PollOption.objects.create(poll=self.poll, text="Test Option")

    def test_poll_detail_publicly_accessible(self):
        response = self.client.get(reverse("poll_detail", args=[self.poll.id]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Detail Test Poll")


@_no_session_refresh
class PollCreateViewTests(TestCase):

    def test_poll_create_requires_auth(self):
        response = self.client.get(reverse("poll_create"))
        self.assertEqual(response.status_code, 302)
        self.assertIn("authenticate", response.url)

    def test_poll_create_accessible_when_authenticated(self):
        user = User.objects.create_user(username="creator", password="pass123")
        self.client.force_login(user)
        response = self.client.get(reverse("poll_create"))
        self.assertEqual(response.status_code, 200)


@_no_session_refresh
class VoteAPITests(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(username="voter")
        self.poll = Poll.objects.create(
            title="Votable Poll",
            created_by=self.user,
            poll_type=PollType.PUBLIC,
        )
        self.option = PollOption.objects.create(poll=self.poll, text="Option A")

    def test_authenticated_user_can_vote(self):
        self.client.force_login(self.user)
        response = self.client.post(
            reverse("vote_api", args=[self.poll.id]),
            {"option_id": self.option.id},
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("Vote cast successfully", str(response.content))

    def test_vote_increments_option_counter(self):
        self.client.force_login(self.user)
        self.client.post(
            reverse("vote_api", args=[self.poll.id]),
            {"option_id": self.option.id},
        )
        self.assertEqual(
            Vote.objects.filter(option=self.option, is_current=True).count(), 1
        )

    def test_unauthenticated_user_cannot_vote(self):
        response = self.client.post(
            reverse("vote_api", args=[self.poll.id]),
            {"option_id": self.option.id},
        )
        self.assertEqual(response.status_code, 401)

    def test_duplicate_vote_prevented(self):
        self.client.force_login(self.user)
        self.client.post(
            reverse("vote_api", args=[self.poll.id]),
            {"option_id": self.option.id},
        )
        response = self.client.post(
            reverse("vote_api", args=[self.poll.id]),
            {"option_id": self.option.id},
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("already voted", str(response.content))

    def test_vote_without_option_id_returns_error(self):
        self.client.force_login(self.user)
        response = self.client.post(
            reverse("vote_api", args=[self.poll.id]),
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("Option ID is required", str(response.content))

    def test_public_poll_does_not_require_credential(self):
        self.client.force_login(self.user)
        response = self.client.post(
            reverse("vote_api", args=[self.poll.id]),
            {"option_id": self.option.id},
        )
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("requires_credential", str(response.content))

    def test_vote_api_htmx_success_returns_html(self):
        self.client.force_login(self.user)
        response = self.client.post(
            reverse("vote_api", args=[self.poll.id]),
            {"option_id": self.option.id},
            HTTP_HX_REQUEST="true",
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "You voted for")


class TemporalPollingTests(TestCase):
    """Temporal validation: TIMED / SCHEDULED / ONGOING polls."""

    def setUp(self):
        self.user = User.objects.create_user(username="creator")

    def _make_vote_data(self, option_id):
        return {"option_id": option_id}

    # --- Scheduled poll: reject before start ---

    def test_scheduled_poll_rejects_vote_before_start(self):
        poll = Poll.objects.create(
            title="Future Poll",
            created_by=self.user,
            poll_type=PollType.PUBLIC,
            temporal_type=TemporalPollType.SCHEDULED,
            starts_at=timezone.now() + timezone.timedelta(hours=1),
            ends_at=timezone.now() + timezone.timedelta(hours=2),
        )
        option = PollOption.objects.create(poll=poll, text="Later")
        self.client.force_login(self.user)
        response = self.client.post(
            reverse("vote_api", args=[poll.id]),
            {"option_id": option.id},
        )
        self.assertIn("not started yet", str(response.content).lower())

    # --- Timed poll: reject after end ---

    def test_timed_poll_rejects_vote_after_end(self):
        poll = Poll.objects.create(
            title="Expired Poll",
            created_by=self.user,
            poll_type=PollType.PUBLIC,
            temporal_type=TemporalPollType.TIMED,
            starts_at=timezone.now() - timezone.timedelta(hours=2),
            ends_at=timezone.now() - timezone.timedelta(hours=1),
        )
        option = PollOption.objects.create(poll=poll, text="Too Late")
        self.client.force_login(self.user)
        response = self.client.post(
            reverse("vote_api", args=[poll.id]),
            {"option_id": option.id},
        )
        self.assertIn("ended", str(response.content).lower())

    # --- Ongoing poll: always active ---

    def test_ongoing_poll_accepts_vote_anytime(self):
        poll = Poll.objects.create(
            title="Evergreen Poll",
            created_by=self.user,
            poll_type=PollType.PUBLIC,
            temporal_type=TemporalPollType.ONGOING,
        )
        option = PollOption.objects.create(poll=poll, text="Forever")
        self.client.force_login(self.user)
        response = self.client.post(
            reverse("vote_api", args=[poll.id]),
            {"option_id": option.id},
        )
        self.assertEqual(response.status_code, 200)

    # --- Immutable poll rejects duplicate ---

    def test_immutable_poll_rejects_duplicate_vote(self):
        poll = Poll.objects.create(
            title="Immutable Poll",
            created_by=self.user,
            poll_type=PollType.PUBLIC,
            temporal_type=TemporalPollType.TIMED,
            is_mutable=False,
            starts_at=timezone.now() - timezone.timedelta(hours=1),
            ends_at=timezone.now() + timezone.timedelta(hours=1),
        )
        option = PollOption.objects.create(poll=poll, text="One Shot")
        self.client.force_login(self.user)
        self.client.post(
            reverse("vote_api", args=[poll.id]),
            {"option_id": option.id},
        )
        response = self.client.post(
            reverse("vote_api", args=[poll.id]),
            {"option_id": option.id},
        )
        self.assertEqual(response.status_code, 400)

    # --- Mutable (ongoing) poll allows re-vote ---

    def test_mutable_poll_allows_revote(self):
        poll = Poll.objects.create(
            title="Mutable Poll",
            created_by=self.user,
            poll_type=PollType.PUBLIC,
            temporal_type=TemporalPollType.ONGOING,
            is_mutable=True,
        )
        option_a = PollOption.objects.create(poll=poll, text="Option A")
        option_b = PollOption.objects.create(poll=poll, text="Option B")

        self.client.force_login(self.user)

        # First vote
        self.client.post(
            reverse("vote_api", args=[poll.id]),
            {"option_id": option_a.id},
        )
        self.assertEqual(
            Vote.objects.filter(poll=poll, voter_did=self.user.username, is_current=True).count(),
            1,
        )

        # Re-vote on different option
        self.client.post(
            reverse("vote_api", args=[poll.id]),
            {"option_id": option_b.id},
        )
        current_vote = Vote.objects.filter(
            poll=poll, voter_did=self.user.username, is_current=True
        ).first()
        self.assertIsNotNone(current_vote)
        self.assertEqual(current_vote.option_id, option_b.id)

        # Old vote is still in the DB (historical record) but not current
        old_votes = Vote.objects.filter(
            poll=poll, voter_did=self.user.username, is_current=False
        )
        self.assertEqual(old_votes.count(), 1)
        self.assertEqual(old_votes.first().option_id, option_a.id)

        # Dynamic tally reflects only the current vote
        self.assertEqual(
            Vote.objects.filter(option=option_a, is_current=True).count(), 0
        )
        self.assertEqual(
            Vote.objects.filter(option=option_b, is_current=True).count(), 1
        )

    # --- Model validation ---

    def test_timed_poll_must_have_ends_at(self):
        from django.core.exceptions import ValidationError

        poll = Poll(
            title="Bad Timed Poll",
            created_by=self.user,
            temporal_type=TemporalPollType.TIMED,
            ends_at=None,
        )
        with self.assertRaises(ValidationError):
            poll.clean()

    def test_scheduled_poll_must_have_starts_at(self):
        from django.core.exceptions import ValidationError

        poll = Poll(
            title="Bad Scheduled Poll",
            created_by=self.user,
            temporal_type=TemporalPollType.SCHEDULED,
            starts_at=None,
            ends_at=timezone.now() + timezone.timedelta(hours=1),
        )
        with self.assertRaises(ValidationError):
            poll.clean()

    # --- Ongoing poll is_expired is always False ---

    def test_ongoing_poll_never_expires(self):
        poll = Poll.objects.create(
            title="Forever Poll",
            created_by=self.user,
            temporal_type=TemporalPollType.ONGOING,
        )
        self.assertFalse(poll.is_expired)
        self.assertTrue(poll.is_active_now)

    # --- Dynamic tally vs deprecated counter ---

    def test_dynamic_vote_count_matches_active_votes(self):
        poll = Poll.objects.create(
            title="Dynamic Tally Poll",
            created_by=self.user,
            poll_type=PollType.PUBLIC,
            temporal_type=TemporalPollType.ONGOING,
            is_mutable=True,
        )
        option = PollOption.objects.create(poll=poll, text="Tally Me")

        self.client.force_login(self.user)
        self.client.post(
            reverse("vote_api", args=[poll.id]),
            {"option_id": option.id},
        )

        option.refresh_from_db()
        # Deprecated field stays at 0
        self.assertEqual(option.votes, 0)
        # Dynamic property returns correct value
        self.assertEqual(option.dynamic_vote_count, 1)

    def test_aggregation_uses_latest_id_not_stale_is_current(self):
        """Timestamp-derived aggregation ignores a stale ``is_current`` flag.

        Simulates out-of-order federation arrival: the previous vote has
        a higher PK (arrived later) but ``is_current`` incorrectly
        remained True.  Aggregation must still pick the **latest id**
        as the active checkpoint.
        """
        poll = Poll.objects.create(
            title="Reorder Test",
            created_by=self.user,
            poll_type=PollType.PUBLIC,
            temporal_type=TemporalPollType.ONGOING,
            is_mutable=True,
        )
        option_a = PollOption.objects.create(poll=poll, text="A")
        option_b = PollOption.objects.create(poll=poll, text="B")
        voter = "did:key:z6Mreorder"

        # Vote 1 — ingested first (lower PK)
        v1 = Vote.objects.create(
            poll=poll, option=option_a, voter_did=voter,
            signature="sig1", is_verified=True,
        )
        # Vote 2 — ingested later (higher PK), but is_current=False
        # (simulates out-of-order where the cache flag missed the flip)
        Vote.objects.create(
            poll=poll, option=option_b, voter_did=voter,
            signature="sig2", is_verified=True, is_current=False,
        )

        # Correct: latest id = vote 2, which voted for option_b
        self.assertEqual(poll.total_votes, 1)
        self.assertEqual(option_a.dynamic_vote_count, 0)
        self.assertEqual(option_b.dynamic_vote_count, 1)


class WriteInBallotTests(TestCase):
    """Write-in ballot option and leaderboard tests."""

    def setUp(self):
        # Disconnect a pre-existing DataSyncLog signal that crashes on INSERT
        # with F() version expressions.  Restored in tearDown.
        from django.db.models.signals import post_save
        from apps.core.models import FederatedData
        from apps.core.signals import log_federated_data_on_save

        post_save.disconnect(log_federated_data_on_save, sender=FederatedData)
        self._reconnect_signal = lambda: post_save.connect(
            log_federated_data_on_save, sender=FederatedData
        )

        self.user = User.objects.create_user(username="creator")
        self.poll = Poll.objects.create(
            title="Write-In Poll",
            created_by=self.user,
            poll_type=PollType.PUBLIC,
            temporal_type=TemporalPollType.ONGOING,
            allow_write_ins=True,
        )
        self.authored = PollOption.objects.create(
            poll=self.poll, text="Official Option"
        )

    def tearDown(self):
        self._reconnect_signal()

    def _post_vote(self, payload):
        payload.setdefault("voter_did", "did:key:z6Mtest")
        payload.setdefault("signature", "ab" * 64)
        url = reverse("cast_vote_api", args=[self.poll.id])
        return self.client.post(
            url, payload, content_type="application/json"
        )

    # --- Test 1: write-in on disabled poll rejected ---

    @patch("apps.poller.views.verify_vote_signature", return_value=True)
    def test_write_in_on_disabled_poll_rejected(self, _mock_sig):
        self.poll.allow_write_ins = False
        self.poll.save(update_fields=["allow_write_ins"])
        response = self._post_vote({
            "poll_id": self.poll.id,
            "option_id": 0,
            "write_in_text": "Nope",
        })
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertFalse(data["valid"])
        self.assertIn("not enabled", data["error"].lower())

    # --- Test 2: write-in normalization coalesces ---

    @patch("apps.poller.views.verify_vote_signature", return_value=True)
    def test_write_in_normalization_coalesces(self, _mock_sig):
        # First voter: "Donald  Duck" (extra spaces)
        r1 = self._post_vote({
            "poll_id": self.poll.id,
            "option_id": 0,
            "write_in_text": "Donald  Duck",
            "voter_did": "did:key:z6Mvoter1",
        })
        self.assertEqual(r1.status_code, 201)
        options_a = PollOption.objects.filter(
            poll=self.poll, text__iexact="donald duck"
        )
        self.assertEqual(options_a.count(), 1)
        opt = options_a.first()
        self.assertTrue(opt.is_write_in)
        self.assertEqual(opt.nominated_by, "did:key:z6Mvoter1")

        # Second voter: "donald duck" (lowercase)
        r2 = self._post_vote({
            "poll_id": self.poll.id,
            "option_id": 0,
            "write_in_text": "donald duck",
            "voter_did": "did:key:z6Mvoter2",
        })
        self.assertEqual(r2.status_code, 201)
        # Still exactly one PollOption for this text
        self.assertEqual(
            PollOption.objects.filter(poll=self.poll, text__iexact="donald duck").count(),
            1,
        )

    # --- Test 3: write-in creates option on first use ---

    @patch("apps.poller.views.verify_vote_signature", return_value=True)
    def test_write_in_creates_option_on_first_use(self, _mock_sig):
        response = self._post_vote({
            "poll_id": self.poll.id,
            "option_id": 0,
            "write_in_text": "Brand New Write-In",
        })
        self.assertEqual(response.status_code, 201)
        opt = PollOption.objects.filter(
            poll=self.poll, text="Brand New Write-In"
        ).first()
        self.assertIsNotNone(opt)
        self.assertTrue(opt.is_write_in)

    # --- Test 4: write-in coalesces to authored option ---

    @patch("apps.poller.views.verify_vote_signature", return_value=True)
    def test_write_in_coalesces_to_authored_option(self, _mock_sig):
        # Match the authored option from setUp case-insensitively
        response = self._post_vote({
            "poll_id": self.poll.id,
            "option_id": 0,
            "write_in_text": "official option",
        })
        self.assertEqual(response.status_code, 201)
        vote = Vote.objects.filter(poll=self.poll).first()
        self.assertEqual(vote.option_id, self.authored.id)
        self.assertFalse(vote.option.is_write_in)

    # --- Test 5: write-in on mutable poll + re-vote ---

    @patch("apps.poller.views.verify_vote_signature", return_value=True)
    def test_write_in_revote_mutable_poll(self, _mock_sig):
        self.poll.is_mutable = True
        self.poll.save(update_fields=["is_mutable"])

        # Vote for write-in "Alpha"
        r1 = self._post_vote({
            "poll_id": self.poll.id,
            "option_id": 0,
            "write_in_text": "Alpha",
        })
        self.assertEqual(r1.status_code, 201)
        alpha = PollOption.objects.get(poll=self.poll, text="Alpha")

        # Re-vote for write-in "Beta"
        r2 = self._post_vote({
            "poll_id": self.poll.id,
            "option_id": 0,
            "write_in_text": "Beta",
        })
        self.assertEqual(r2.status_code, 201)
        beta = PollOption.objects.get(poll=self.poll, text="Beta")

        current_vote = Vote.objects.filter(
            poll=self.poll, voter_did="did:key:z6Mtest", is_current=True
        ).first()
        self.assertEqual(current_vote.option_id, beta.id)

        old_votes = Vote.objects.filter(
            poll=self.poll, voter_did="did:key:z6Mtest", is_current=False
        )
        self.assertEqual(old_votes.count(), 1)
        self.assertEqual(old_votes.first().option_id, alpha.id)

    # --- Test 6: serializer splits core vs write-in buckets ---

    def test_results_serializer_splits_core_and_write_ins(self):
        PollOption.objects.create(poll=self.poll, text="Core A")
        PollOption.objects.create(
            poll=self.poll, text="Write A", is_write_in=True
        )
        PollOption.objects.create(
            poll=self.poll, text="Write B", is_write_in=True
        )
        serializer = PollResultsSerializer(self.poll)
        data = serializer.data
        self.assertIn("core_options", data)
        self.assertIn("write_in_leaderboard", data)
        core_texts = {o["option"] for o in data["core_options"]}
        write_texts = {o["option"] for o in data["write_in_leaderboard"]}
        self.assertIn("Core A", core_texts)
        self.assertIn("Write A", write_texts)
        self.assertIn("Write B", write_texts)
        # Authored option should NOT appear in write-in leaderboard
        self.assertNotIn("Core A", write_texts)

    # --- Test 7: write-in leaderboard truncated to display_limit ---

    def test_write_in_leaderboard_truncated(self):
        self.poll.write_in_display_limit = 3
        self.poll.save(update_fields=["write_in_display_limit"])
        for i in range(5):
            PollOption.objects.create(
                poll=self.poll,
                text=f"Write-in {i}",
                is_write_in=True,
            )
        serializer = PollResultsSerializer(self.poll)
        self.assertLessEqual(
            len(serializer.data["write_in_leaderboard"]), 3
        )


class CredentialGateTests(TestCase):
    """Credential gate verification for headless CastVoteAPIView."""

    def setUp(self):
        from django.db.models.signals import post_save
        from apps.core.models import FederatedData
        from apps.core.signals import log_federated_data_on_save

        post_save.disconnect(log_federated_data_on_save, sender=FederatedData)
        self._reconnect_signal = lambda: post_save.connect(
            log_federated_data_on_save, sender=FederatedData
        )

        self.user = User.objects.create_user(username="creator")
        self.poll = Poll.objects.create(
            title="Gated Poll",
            created_by=self.user,
            poll_type=PollType.PUBLIC,
            temporal_type=TemporalPollType.ONGOING,
        )
        self.option = PollOption.objects.create(poll=self.poll, text="Yes")

    def tearDown(self):
        self._reconnect_signal()

    def _post_vote(self, payload):
        payload.setdefault("voter_did", "did:key:z6Mgated")
        payload.setdefault("signature", "cd" * 64)
        url = reverse("cast_vote_api", args=[self.poll.id])
        return self.client.post(url, payload, content_type="application/json")

    # --- Test 1: blank gate accepts vote without credential ---

    @patch("apps.poller.views.verify_vote_signature", return_value=True)
    def test_credential_gate_blank_accepts_vote(self, _mock_sig):
        self.poll.required_credential_type = ""
        self.poll.save(update_fields=["required_credential_type"])
        response = self._post_vote({
            "poll_id": self.poll.id,
            "option_id": self.option.id,
        })
        self.assertEqual(response.status_code, 201)

    # --- Test 2: gated poll rejects missing credential ---

    @patch("apps.poller.views.verify_vote_signature", return_value=True)
    def test_credential_gate_rejects_missing_credential(self, _mock_sig):
        self.poll.required_credential_type = "municipal_voter"
        self.poll.save(update_fields=["required_credential_type"])
        response = self._post_vote({
            "poll_id": self.poll.id,
            "option_id": self.option.id,
        })
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertFalse(data["valid"])
        self.assertIn("Missing or invalid identity credential", data["error"])

    # --- Test 3: valid credential stored in credential_data ---

    @patch("apps.poller.views.verify_vote_signature", return_value=True)
    def test_credential_gate_stores_valid_credential(self, _mock_sig):
        self.poll.required_credential_type = "municipal_voter"
        self.poll.save(update_fields=["required_credential_type"])

        private_key = Ed25519PrivateKey.generate()
        pubkey_bytes = private_key.public_key().public_bytes_raw()
        multicodec = b"\xed\x01" + pubkey_bytes
        issuer_did = f"did:key:z{_b58encode(multicodec)}"

        vc_body = {
            "@context": ["https://www.w3.org/2018/credentials/v1"],
            "type": ["municipal_voter"],
            "issuer": issuer_did,
            "issuanceDate": "2026-01-01T00:00:00Z",
            "credentialSubject": {"id": "did:key:z6Mgated"},
        }
        canonical = json.dumps(vc_body, sort_keys=False, separators=(",", ":")).encode("utf-8")
        sig_bytes = private_key.sign(canonical)
        sig_b58 = _b58encode(sig_bytes)
        vc_body["proof"] = {
            "type": "Ed25519Signature2018",
            "verificationMethod": f"{issuer_did}#keys-1",
            "signatureValue": sig_b58,
        }

        response = self._post_vote({
            "poll_id": self.poll.id,
            "option_id": self.option.id,
            "credential": vc_body,
        })
        self.assertEqual(response.status_code, 201)
        vote = Vote.objects.filter(poll=self.poll).first()
        self.assertIsNotNone(vote)
        self.assertIsNotNone(vote.credential_data)
        self.assertEqual(vote.credential_data["type"], "municipal_voter")
        self.assertEqual(vote.credential_data["issuer"], issuer_did)

    # --- Test 4: credential from a non-whitelisted issuer is rejected ---

    @patch("apps.poller.views.verify_vote_signature", return_value=True)
    def test_credential_from_non_whitelisted_issuer_rejected(self, _mock_sig):
        self.poll.required_credential_type = "municipal_voter"
        self.poll.save(update_fields=["required_credential_type"])

        private_key = Ed25519PrivateKey.generate()
        pubkey_bytes = private_key.public_key().public_bytes_raw()
        multicodec = b"\xed\x01" + pubkey_bytes
        issuer_did = f"did:key:z{_b58encode(multicodec)}"

        vc_body = {
            "@context": ["https://www.w3.org/2018/credentials/v1"],
            "type": ["municipal_voter"],
            "issuer": issuer_did,
            "issuanceDate": "2026-01-01T00:00:00Z",
            "credentialSubject": {"id": "did:key:z6Mgated"},
        }
        canonical = json.dumps(vc_body, sort_keys=False, separators=(",", ":")).encode("utf-8")
        sig_bytes = private_key.sign(canonical)
        sig_b58 = _b58encode(sig_bytes)
        vc_body["proof"] = {
            "type": "Ed25519Signature2018",
            "verificationMethod": f"{issuer_did}#keys-1",
            "signatureValue": sig_b58,
        }

        # Whitelist a *different* issuer so this one is unauthorised
        TrustedIssuer.objects.create(
            poll=self.poll,
            issuer_did="did:key:z6MwhitelistedOnly",
        )

        response = self._post_vote({
            "poll_id": self.poll.id,
            "option_id": self.option.id,
            "credential": vc_body,
        })
        self.assertEqual(response.status_code, 403)
        data = response.json()
        self.assertFalse(data["valid"])
        self.assertIn("Issuer not authorized", data["error"])

    # --- Test 5: whitelisted issuer is accepted ---

    @patch("apps.poller.views.verify_vote_signature", return_value=True)
    def test_whitelisted_issuer_accepted(self, _mock_sig):
        self.poll.required_credential_type = "municipal_voter"
        self.poll.save(update_fields=["required_credential_type"])

        private_key = Ed25519PrivateKey.generate()
        pubkey_bytes = private_key.public_key().public_bytes_raw()
        multicodec = b"\xed\x01" + pubkey_bytes
        issuer_did = f"did:key:z{_b58encode(multicodec)}"

        # Add issuer to the whitelist
        TrustedIssuer.objects.create(poll=self.poll, issuer_did=issuer_did)

        vc_body = {
            "@context": ["https://www.w3.org/2018/credentials/v1"],
            "type": ["municipal_voter"],
            "issuer": issuer_did,
            "issuanceDate": "2026-01-01T00:00:00Z",
            "credentialSubject": {"id": "did:key:z6Mgated"},
        }
        canonical = json.dumps(vc_body, sort_keys=False, separators=(",", ":")).encode("utf-8")
        sig_bytes = private_key.sign(canonical)
        sig_b58 = _b58encode(sig_bytes)
        vc_body["proof"] = {
            "type": "Ed25519Signature2018",
            "verificationMethod": f"{issuer_did}#keys-1",
            "signatureValue": sig_b58,
        }

        response = self._post_vote({
            "poll_id": self.poll.id,
            "option_id": self.option.id,
            "credential": vc_body,
        })
        self.assertEqual(response.status_code, 201)
        vote = Vote.objects.filter(poll=self.poll).first()
        self.assertEqual(vote.credential_data["issuer"], issuer_did)

    # --- Test 6: mandatory issuer bypasses whitelist ---

    @patch("apps.poller.views.verify_vote_signature", return_value=True)
    def test_mandatory_issuer_accepted_even_if_not_in_whitelist(self, _mock_sig):
        self.poll.required_credential_type = "municipal_voter"
        self.poll.save(update_fields=["required_credential_type"])

        # Build a real keypair — the registrar's DID is derived from its key
        registrar_key = Ed25519PrivateKey.generate()
        registrar_pubkey_bytes = registrar_key.public_key().public_bytes_raw()
        registrar_multicodec = b"\xed\x01" + registrar_pubkey_bytes
        registrar_did = f"did:key:z{_b58encode(registrar_multicodec)}"

        # Whitelist only Bob's server (not the registrar)
        TrustedIssuer.objects.create(
            poll=self.poll,
            issuer_did="did:key:z6MBobsServer",
        )

        # Sign a credential as the registrar (mandatory issuer)
        vc_body = {
            "@context": ["https://www.w3.org/2018/credentials/v1"],
            "type": ["municipal_voter"],
            "issuer": registrar_did,
            "issuanceDate": "2026-01-01T00:00:00Z",
            "credentialSubject": {"id": "did:key:z6Mgated"},
        }
        canonical = json.dumps(vc_body, sort_keys=False, separators=(",", ":")).encode("utf-8")
        sig_bytes = registrar_key.sign(canonical)
        sig_b58 = _b58encode(sig_bytes)
        vc_body["proof"] = {
            "type": "Ed25519Signature2018",
            "verificationMethod": f"{registrar_did}#keys-1",
            "signatureValue": sig_b58,
        }

        with self.settings(MANDATORY_ISSUER_DIDS=[registrar_did]):
            response = self._post_vote({
                "poll_id": self.poll.id,
                "option_id": self.option.id,
                "credential": vc_body,
            })
        self.assertEqual(response.status_code, 201)
        vote = Vote.objects.filter(poll=self.poll).first()
        self.assertEqual(vote.credential_data["issuer"], registrar_did)