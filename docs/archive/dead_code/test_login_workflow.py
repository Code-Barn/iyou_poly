"""
Comprehensive test for DID-based login functionality.
This test covers the new DID login views and trust management system.
"""

import json
import logging
import os
from unittest.mock import patch

# Configure Django settings
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

from django.test import TestCase, override_settings
from django.urls import reverse

from apps.accounts.models import User
from apps.accounts.utils.did_utils import (
    get_trusted_issuers,
    is_trusted_issuer,
    issue_vc,
    verify_federated_vc,
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DIDLoginTrustManagementTest(TestCase):
    """Test DID login trust management functionality."""

    def setUp(self):
        """Set up test data."""
        import didkit

        # Generate a proper key and DID for testing
        self.test_key = didkit.generateEd25519Key()
        self.test_did = didkit.keyToDID("key", self.test_key)

        # Create test user
        self.user = User.objects.create_user(
            username="testuser_trust",
            did=self.test_did,
            did_method="key",
            did_key=self.test_key,
        )

        # Create valid VC for testing using issue_vc
        credential = {
            "@context": ["https://www.w3.org/2018/credentials/v1"],
            "type": ["VerifiableCredential", "AuthenticationCredential"],
            "issuer": self.test_did,
            "issuanceDate": "2023-01-01T00:00:00Z",
            "credentialSubject": {
                "id": self.test_did,
                "name": "testuser",
            },
        }
        vc_json = issue_vc(credential, self.test_did, self.test_key)
        self.valid_vc = json.loads(vc_json)

    def test_trust_management_open_model(self):
        """Test open trust model (allow all issuers)."""
        # By default, should allow all issuers
        self.assertTrue(is_trusted_issuer("did:key:any_issuer"))
        self.assertTrue(is_trusted_issuer(self.test_did))

        # Trusted issuers list should be empty in open model
        self.assertEqual(len(get_trusted_issuers()), 0)

    @override_settings(
        REQUIRE_TRUSTED_ISSUERS=True, TRUSTED_ISSUERS=["did:key:trusted"]
    )
    def test_trust_management_restricted_model(self):
        """Test restricted trust model (only allow listed issuers)."""
        # Should only allow trusted issuers
        self.assertTrue(is_trusted_issuer("did:key:trusted"))
        self.assertFalse(is_trusted_issuer("did:key:untrusted"))
        self.assertFalse(is_trusted_issuer(self.test_did))

        # Trusted issuers list should contain our trusted issuer
        trusted = get_trusted_issuers()
        self.assertEqual(len(trusted), 1)
        self.assertIn("did:key:trusted", trusted)

    def test_verify_federated_vc_valid(self):
        """Test VC verification with valid VC."""
        vc_json = json.dumps(self.valid_vc)

        # Should verify successfully in open trust model
        self.assertTrue(verify_federated_vc(vc_json, self.test_did))

    def test_verify_federated_vc_invalid_json(self):
        """Test VC verification with invalid JSON."""
        invalid_json = '{"type": "InvalidVC"}'

        # Should fail with invalid VC (missing @context)
        self.assertFalse(verify_federated_vc(invalid_json))

    @override_settings(REQUIRE_TRUSTED_ISSUERS=True, TRUSTED_ISSUERS=["did:key:other"])
    def test_verify_federated_vc_untrusted_issuer(self):
        """Test VC verification with untrusted issuer."""
        vc_json = json.dumps(self.valid_vc)

        # Should fail with untrusted issuer in restricted mode
        self.assertFalse(verify_federated_vc(vc_json, self.test_did))


class DIDLoginViewTest(TestCase):
    """Test DID login view functionality."""

    def setUp(self):
        """Set up test data."""
        self.test_did = "did:key:z6MkTestView123456789"
        self.test_key = json.dumps(
            {
                "kty": "OKP",
                "crv": "Ed25519",
                "x": "view_test_public",
                "d": "view_test_private",
            }
        )

        # Create test user
        self.user = User.objects.create_user(
            username="viewtestuser",
            did=self.test_did,
            did_method="key",
            did_key=self.test_key,
        )

        # Create valid VC
        self.valid_vc = {
            "@context": ["https://www.w3.org/2018/credentials/v1"],
            "type": ["VerifiableCredential", "AuthenticationCredential"],
            "issuer": self.test_did,
            "issuanceDate": "2023-01-01T00:00:00Z",
            "credentialSubject": {
                "id": self.test_did,
                "name": "viewtestuser",
                "email": "viewtest@example.com",
            },
        }

    def test_did_login_get(self):
        """Test GET request to DID login page."""
        response = self.client.get(reverse("did_login"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "registration/did_login.html")

    @patch("apps.accounts.utils.did_utils.verify_federated_vc")
    def test_did_login_post_valid(self, mock_verify):
        """Test POST request with valid VC."""
        mock_verify.return_value = True

        vc_json = json.dumps(self.valid_vc)
        response = self.client.post(
            reverse("did_login"), {"vc": vc_json, "next": "/polls/"}
        )

        # Should redirect to next URL
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, "/polls/")

    @patch("apps.accounts.utils.did_utils.verify_federated_vc")
    def test_did_login_post_invalid(self, mock_verify):
        """Test POST request with invalid VC."""
        mock_verify.return_value = False

        response = self.client.post(
            reverse("did_login"), {"vc": "invalid vc", "next": "/polls/"}
        )

        # Should return form with error
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Invalid JSON format for Verifiable Credential")

    @patch("apps.accounts.utils.did_utils.verify_federated_vc")
    def test_did_login_auto_provisioning(self, mock_verify):
        """Test auto-provisioning of new users."""
        mock_verify.return_value = True

        # Create VC for non-existent user
        new_did = "did:key:z6MkNewUser123456789"
        new_vc = {
            "@context": ["https://www.w3.org/2018/credentials/v1"],
            "type": ["VerifiableCredential", "AuthenticationCredential"],
            "issuer": new_did,
            "issuanceDate": "2023-01-01T00:00:00Z",
            "credentialSubject": {
                "id": new_did,
                "name": "newuser",
                "email": "new@example.com",
            },
        }

        vc_json = json.dumps(new_vc)
        response = self.client.post(
            reverse("did_login"), {"vc": vc_json, "next": "/polls/"}
        )

        # Should redirect (auto-provisioning enabled by default)
        self.assertEqual(response.status_code, 302)

        # Check that user was created
        new_user = User.objects.get(did=new_did)
        self.assertEqual(new_user.username, "newuser")
        self.assertEqual(new_user.email, "new@example.com")
        self.assertFalse(new_user.has_usable_password())

    @override_settings(AUTO_PROVISION_DID_USERS=False)
    @patch("apps.accounts.utils.did_utils.verify_federated_vc")
    def test_did_login_no_auto_provisioning(self, mock_verify):
        """Test that auto-provisioning can be disabled."""
        mock_verify.return_value = True

        # Create VC for non-existent user
        new_did = "did:key:z6MkNoProvision12345"
        new_vc = {
            "@context": ["https://www.w3.org/2018/credentials/v1"],
            "type": ["VerifiableCredential", "AuthenticationCredential"],
            "issuer": new_did,
            "credentialSubject": {
                "id": new_did,
                "name": "noprovision",
            },
        }

        vc_json = json.dumps(new_vc)
        response = self.client.post(
            reverse("did_login"), {"vc": vc_json, "next": "/polls/"}
        )

        # Should return error when auto-provisioning disabled
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "User not found")


if __name__ == "__main__":
    # Run tests with verbose output
    import unittest

    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    suite.addTests(loader.loadTestsFromTestCase(DIDLoginTrustManagementTest))
    suite.addTests(loader.loadTestsFromTestCase(DIDLoginViewTest))

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    if result.wasSuccessful():
        logger.info("🎉 All DID login tests passed!")
    else:
        logger.error("❌ Some DID login tests failed.")
