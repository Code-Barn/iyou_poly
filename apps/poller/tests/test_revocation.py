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
from apps.poller.models import (
    Poll,
    PollOption,
    PollType,
    RevocationAttestation,
    TemporalPollType,
    Vote,
)

User = get_user_model()


class RevocationGateTests(TestCase):
    """Issuer-revoked credentials are rejected by CastVoteAPIView."""

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
            title="Revocable Gated Poll",
            created_by=self.user,
            poll_type=PollType.PUBLIC,
            temporal_type=TemporalPollType.ONGOING,
            is_mutable=True,
            required_credential_type="municipal_voter",
        )
        self.option = PollOption.objects.create(poll=self.poll, text="Yes")
        self.voter_did = "did:key:z6MvoterToRevoke"

        # --- Create a valid signed credential ---
        self.private_key = Ed25519PrivateKey.generate()
        pubkey_bytes = self.private_key.public_key().public_bytes_raw()
        multicodec = b"\xed\x01" + pubkey_bytes
        self.issuer_did = f"did:key:z{_b58encode(multicodec)}"

        vc_body = {
            "@context": ["https://www.w3.org/2018/credentials/v1"],
            "type": ["municipal_voter"],
            "issuer": self.issuer_did,
            "issuanceDate": "2026-01-01T00:00:00Z",
            "credentialSubject": {"id": self.voter_did},
        }
        canonical = json.dumps(vc_body, sort_keys=False, separators=(",", ":")).encode("utf-8")
        sig_bytes = self.private_key.sign(canonical)
        sig_b58 = _b58encode(sig_bytes)
        vc_body["proof"] = {
            "type": "Ed25519Signature2018",
            "verificationMethod": f"{self.issuer_did}#keys-1",
            "signatureValue": sig_b58,
        }
        self.credential = vc_body

    def tearDown(self):
        self._reconnect_signal()

    def _post_vote(self, **overrides):
        payload = {
            "poll_id": self.poll.id,
            "option_id": self.option.id,
            "voter_did": self.voter_did,
            "signature": "cd" * 64,
            "credential": self.credential,
        }
        payload.update(overrides)
        url = reverse("cast_vote_api", args=[self.poll.id])
        return self.client.post(url, payload, content_type="application/json")

    @patch("apps.poller.views.verify_vote_signature", return_value=True)
    def test_valid_credential_cast_succeeds(self, _mock_sig):
        """A valid credential without a revocation is accepted."""
        response = self._post_vote()
        self.assertEqual(response.status_code, 201)
        vote = Vote.objects.filter(poll=self.poll, voter_did=self.voter_did).first()
        self.assertIsNotNone(vote)

    @patch("apps.poller.views.verify_vote_signature", return_value=True)
    def test_revoked_credential_rejected_with_403(self, _mock_sig):
        """After an issuer publishes a RevocationAttestation, the same
        credential is rejected with 403."""
        # First vote succeeds
        response = self._post_vote()
        self.assertEqual(response.status_code, 201)

        # Issuer publishes revocation
        RevocationAttestation.objects.create(
            issuer_did=self.issuer_did,
            subject_did=self.voter_did,
            signature="revocation_sig_placeholder",
            timestamp=timezone.now(),
        )

        # Second vote attempt is rejected
        response = self._post_vote()
        self.assertEqual(response.status_code, 403)
        data = response.json()
        self.assertFalse(data["valid"])
        self.assertIn("Credential Revoked", data["error"])
