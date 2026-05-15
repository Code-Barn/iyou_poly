"""
Bridge-dependent tests: require the Tauri bridge at ws://127.0.0.1:9001.

These tests will fail until the bridge implements sign and sign_credential
message types. Run with: pytest -m bridge
Or skip them: pytest -m "not bridge"
"""

import json
from unittest.mock import patch

import pytest
from django.test import TestCase
from django.urls import reverse

from apps.accounts.models import User


@pytest.mark.bridge
class BridgeSigningTests(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser", password="testpass123"
        )
        self.client.login(username="testuser", password="testpass123")

    @pytest.mark.xfail(
        reason="Bridge does not implement sign_credential message type"
    )
    def test_full_credential_issuance_flow(self):
        """
        Expected flow:
        1. POST to generate_credential → get unsigned credential JSON
        2. Send to bridge via WebSocket → get signed credential
        3. POST signed credential to store_signed_credential → stored in user.vcs
        """
        credential_name = "Bridge Signed Credential"
        credential_type = "MembershipCredential"

        generate_resp = self.client.post(
            reverse("generate_credential"),
            {
                "credential_name": credential_name,
                "credential_type": credential_type,
                "scope_value": "",
            },
        )
        self.assertEqual(generate_resp.status_code, 200)
        data = generate_resp.json()
        self.assertIn("unsigned_credential", data)

        unsigned = data["unsigned_credential"]
        # This is where signCredentialViaBridge() would be called
        # Bridge sends back: { type: "signed_credential", credential: {...} }
        signed = {**unsigned, "proof": {"type": "Ed25519Signature2018"}}

        store_resp = self.client.post(
            reverse("store_signed_credential"),
            json.dumps({
                "signed_credential": signed,
                "credential_name": credential_name,
                "credential_type": credential_type,
                "scope_value": "",
            }),
            content_type="application/json",
        )
        self.assertEqual(store_resp.status_code, 200)
        self.assertEqual(store_resp.json(), {"success": True})

    @pytest.mark.xfail(
        reason="Vote signing still uses SHA-256 placeholder; bridge signing pending"
    )
    def test_vote_signing_via_bridge(self):
        """Vote signatures should come from the bridge, not SHA-256."""
        from apps.poller.models import Poll, PollOption, Vote

        poll = Poll.objects.create(
            title="Bridge Vote Test",
            created_by=self.user,
            poll_type=Poll.PollType.PUBLIC,
        )
        option = PollOption.objects.create(poll=poll, text="Yes")

        vote = Vote.objects.create(
            poll=poll,
            option=option,
            voter_id=self.user.username,
        )

        # Once bridge-based signing is implemented, vote.signature
        # should contain an Ed25519 signature, not a SHA-256 hash
        self.assertIsNotNone(vote.signature)
        self.assertNotIn("sha256", vote.signature.lower())


@pytest.mark.bridge
class BridgeConnectionTests(TestCase):

    @pytest.mark.xfail(reason="Bridge does not respond to WebSocket messages")
    def test_bridge_websocket_connectivity(self):
        import websocket

        ws = websocket.create_connection(
            "ws://127.0.0.1:9001", timeout=5
        )

        ws.send(json.dumps({
            "type": "sign_credential",
            "credential": {"test": True},
        }))
        resp = ws.recv(timeout=5)
        ws.close()

        msg = json.loads(resp)
        self.assertEqual(msg.get("type"), "signed_credential")
        self.assertIn("credential", msg)
