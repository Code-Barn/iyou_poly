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
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.core.verification import _b58encode
from apps.poller.models import Poll, PollOption, PollType, TemporalPollType, Vote

User = get_user_model()


def _build_signed_vc(
    private_key: Ed25519PrivateKey | None = None,
    issuer_did: str | None = None,
    subject_did: str = "did:key:z6Msubject",
    cred_type: str = "municipal_voter",
    fidelity_score: int | None = None,
) -> tuple[dict, Ed25519PrivateKey, str]:
    """Build a valid Ed25519-signed W3C Verifiable Credential.

    Returns ``(vc_dict, private_key, issuer_did)``.
    """
    if private_key is None:
        private_key = Ed25519PrivateKey.generate()
    pubkey_bytes = private_key.public_key().public_bytes_raw()
    multicodec = b"\xed\x01" + pubkey_bytes
    if issuer_did is None:
        issuer_did = f"did:key:z{_b58encode(multicodec)}"

    vc_body = {
        "@context": ["https://www.w3.org/2018/credentials/v1"],
        "type": [cred_type],
        "issuer": issuer_did,
        "issuanceDate": "2026-01-01T00:00:00Z",
        "credentialSubject": {"id": subject_did},
    }
    if fidelity_score is not None:
        vc_body["fidelity_score"] = fidelity_score

    canonical = json.dumps(vc_body, sort_keys=False, separators=(",", ":")).encode("utf-8")
    sig_bytes = private_key.sign(canonical)
    sig_b58 = _b58encode(sig_bytes)
    vc_body["proof"] = {
        "type": "Ed25519Signature2018",
        "verificationMethod": f"{issuer_did}#keys-1",
        "signatureValue": sig_b58,
    }
    return vc_body, private_key, issuer_did


def _build_vp(
    inner_vc: dict,
    holder_private_key: Ed25519PrivateKey,
    holder_did: str,
    challenge: str,
) -> dict:
    """Wrap a Verifiable Credential in a signed Verifiable Presentation."""
    vp_body = {
        "@context": ["https://www.w3.org/2018/credentials/v1"],
        "type": ["VerifiablePresentation"],
        "holder": holder_did,
        "verifiableCredential": [inner_vc],
    }
    # VP envelope signed with sort_keys=True (see verify_credential_presentation)
    canonical = json.dumps(vp_body, sort_keys=True, separators=(",", ":")).encode("utf-8")
    sig_bytes = holder_private_key.sign(canonical)
    sig_b58 = _b58encode(sig_bytes)
    vp_body["proof"] = {
        "type": "Ed25519Signature2018",
        "verificationMethod": f"{holder_did}#keys-1",
        "challenge": challenge,
        "signatureValue": sig_b58,
    }
    return vp_body


class VpCredentialGateTests(TestCase):
    """Verifiable Presentation credential gate tests for CastVoteAPIView."""

    def setUp(self):
        from django.db.models.signals import post_save
        from apps.core.models import FederatedData
        from apps.core.signals import log_federated_data_on_save

        post_save.disconnect(log_federated_data_on_save, sender=FederatedData)
        self._reconnect_signal = lambda: post_save.connect(
            log_federated_data_on_save, sender=FederatedData
        )

        self.user = User.objects.create_user(username="did:key:z6MholderUser")
        self.poll = Poll.objects.create(
            title="VP Gated Poll",
            created_by=self.user,
            poll_type=PollType.PUBLIC,
            temporal_type=TemporalPollType.ONGOING,
            is_mutable=True,
            required_credential_type="municipal_voter",
        )
        self.option = PollOption.objects.create(poll=self.poll, text="Yes")

        # Holder (voter) keypair
        self.holder_key = Ed25519PrivateKey.generate()
        holder_pubkey = self.holder_key.public_key().public_bytes_raw()
        holder_multicodec = b"\xed\x01" + holder_pubkey
        self.holder_did = f"did:key:z{_b58encode(holder_multicodec)}"

    def tearDown(self):
        self._reconnect_signal()

    def _challenge_response(self):
        url = reverse("credential_request_api", args=[self.poll.id])
        return self.client.post(url, {"voter_did": self.holder_did},
                                content_type="application/json")

    def _cast_vote(self, **overrides):
        payload = {
            "poll_id": self.poll.id,
            "option_id": self.option.id,
            "voter_did": self.holder_did,
            "signature": "cd" * 64,
        }
        payload.update(overrides)
        url = reverse("cast_vote_api", args=[self.poll.id])
        return self.client.post(url, payload, content_type="application/json")

    # --- Test 1: Full VP handshake succeeds ---

    @patch("apps.poller.views.verify_vote_signature", return_value=True)
    def test_full_vp_handshake_succeeds(self, _mock_sig):
        """Request a challenge → build VP → cast vote → 201."""
        resp1 = self._challenge_response()
        self.assertEqual(resp1.status_code, 201)
        challenge = resp1.json()["details"]["challenge"]

        # Build a VC signed by a separate issuer
        issuer_key = Ed25519PrivateKey.generate()
        inner_vc, _, _ = _build_signed_vc(
            private_key=issuer_key,
            subject_did=self.holder_did,
        )

        # Wrap it in a VP signed by the holder
        vp = _build_vp(inner_vc, self.holder_key, self.holder_did, challenge)

        response = self._cast_vote(credential_presentation=vp)
        self.assertEqual(response.status_code, 201)
        vote = Vote.objects.filter(poll=self.poll, voter_did=self.holder_did).first()
        self.assertIsNotNone(vote)

    # --- Test 2: Expired / missing challenge → 403 ---

    @patch("apps.poller.views.verify_vote_signature", return_value=True)
    def test_rejects_missing_challenge(self, _mock_sig):
        """No challenge issued → VP mode returns 403."""
        issuer_key = Ed25519PrivateKey.generate()
        inner_vc, _, _ = _build_signed_vc(
            private_key=issuer_key,
            subject_did=self.holder_did,
        )
        vp = _build_vp(inner_vc, self.holder_key, self.holder_did, "bogus-challenge")

        response = self._cast_vote(credential_presentation=vp)
        self.assertEqual(response.status_code, 403)
        data = response.json()
        self.assertFalse(data["valid"])

    # --- Test 3: Wrong challenge → 403 (VP crypto failure) ---

    @patch("apps.poller.views.verify_vote_signature", return_value=True)
    def test_rejects_wrong_challenge(self, _mock_sig):
        """Challenge in VP does not match the server-issued one."""
        resp1 = self._challenge_response()
        self.assertEqual(resp1.status_code, 201)

        issuer_key = Ed25519PrivateKey.generate()
        inner_vc, _, _ = _build_signed_vc(
            private_key=issuer_key,
            subject_did=self.holder_did,
        )
        vp = _build_vp(inner_vc, self.holder_key, self.holder_did, "wrong-nonce")

        response = self._cast_vote(credential_presentation=vp)
        self.assertEqual(response.status_code, 403)

    # --- Test 4: Bad holder signature → 403 ---

    @patch("apps.poller.views.verify_vote_signature", return_value=True)
    def test_rejects_bad_holder_signature(self, _mock_sig):
        """VP envelope signed by a different key than the holder DID."""
        resp1 = self._challenge_response()
        self.assertEqual(resp1.status_code, 201)
        challenge = resp1.json()["details"]["challenge"]

        issuer_key = Ed25519PrivateKey.generate()
        inner_vc, _, _ = _build_signed_vc(
            private_key=issuer_key,
            subject_did=self.holder_did,
        )

        # Sign the VP with a *different* key (not the holder's)
        wrong_key = Ed25519PrivateKey.generate()
        vp = _build_vp(inner_vc, wrong_key, self.holder_did, challenge)

        response = self._cast_vote(credential_presentation=vp)
        self.assertEqual(response.status_code, 403)

    # --- Test 5: Missing credential fields → 400 ---

    @patch("apps.poller.views.verify_vote_signature", return_value=True)
    def test_rejects_missing_credential_fields(self, _mock_sig):
        """No credential_presentation and no credential → 400."""
        response = self._cast_vote()
        self.assertEqual(response.status_code, 400)

    # --- Test 6: Legacy bare-VC mode still works ---

    @patch("apps.poller.views.verify_vote_signature", return_value=True)
    def test_legacy_bare_vc_still_works(self, _mock_sig):
        """Existing bare-VC credential gate continues to function."""
        issuer_key = Ed25519PrivateKey.generate()
        inner_vc, _, _ = _build_signed_vc(
            private_key=issuer_key,
            subject_did=self.holder_did,
        )
        response = self._cast_vote(credential=inner_vc)
        self.assertEqual(response.status_code, 201)
        vote = Vote.objects.filter(poll=self.poll, voter_did=self.holder_did).first()
        self.assertIsNotNone(vote)

    # --- Test 7: Challenge consumed after use ---

    @patch("apps.poller.views.verify_vote_signature", return_value=True)
    def test_challenge_consumed_after_use(self, _mock_sig):
        """A challenge can only be used once."""
        resp1 = self._challenge_response()
        challenge = resp1.json()["details"]["challenge"]

        issuer_key = Ed25519PrivateKey.generate()
        inner_vc, _, _ = _build_signed_vc(
            private_key=issuer_key,
            subject_did=self.holder_did,
        )
        vp = _build_vp(inner_vc, self.holder_key, self.holder_did, challenge)

        # First use — succeeds
        r1 = self._cast_vote(credential_presentation=vp)
        self.assertEqual(r1.status_code, 201)

        # Second use with same VP (challenge already consumed) — fails
        r2 = self._cast_vote(credential_presentation=vp)
        self.assertEqual(r2.status_code, 403)
