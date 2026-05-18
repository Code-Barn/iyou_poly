"""
Test script to verify DID and VC functionality in Poly.

This script tests:
1. DID generation using didkit.keyToDID
2. VC issuance using issue_vc
3. VC verification using verify_vc
"""

import json
import logging

import didkit
from django.test import TestCase

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DIDVCTest(TestCase):
    """Test DID and VC functionality."""

    def setUp(self):
        """Set up test data."""
        # Generate a key and DID
        self.key = didkit.generateEd25519Key()
        self.did = didkit.keyToDID("key", self.key)
        logger.info(f"Generated DID: {self.did}")
        logger.info(f"Key: {self.key}")

    def test_did_generation(self):
        """Test DID generation using didkit.keyToDID."""
        self.assertTrue(self.did.startswith("did:key:z"))
        self.assertEqual(len(self.did.split(":")), 3)

    def test_vc_issuance(self):
        """Test VC issuance using issue_vc."""
        from apps.accounts.utils.did_utils import issue_vc

        credential = {
            "@context": ["https://www.w3.org/2018/credentials/v1"],
            "type": ["VerifiableCredential", "AuthenticationCredential"],
            "issuer": self.did,
            "issuanceDate": "2023-01-01T00:00:00Z",
            "credentialSubject": {
                "id": self.did,
                "name": "testuser",
            },
        }

        vc = issue_vc(credential, self.did, self.key)
        self.assertIsNotNone(vc)
        vc_data = json.loads(vc)
        self.assertEqual(vc_data["issuer"], self.did)
        self.assertEqual(vc_data["credentialSubject"]["id"], self.did)
        self.assertEqual(vc_data["credentialSubject"]["name"], "testuser")
        logger.info("VC issued successfully")

    def test_vc_verification(self):
        """Test VC verification using verify_vc."""
        from apps.accounts.utils.did_utils import issue_vc, verify_vc

        credential = {
            "@context": ["https://www.w3.org/2018/credentials/v1"],
            "type": ["VerifiableCredential", "AuthenticationCredential"],
            "issuer": self.did,
            "issuanceDate": "2023-01-01T00:00:00Z",
            "credentialSubject": {
                "id": self.did,
                "name": "testuser",
            },
        }

        vc = issue_vc(credential, self.did, self.key)
        self.assertIsNotNone(vc)

        # Verify the VC using the did_key
        is_valid = verify_vc(vc, did_key=json.loads(self.key))
        self.assertTrue(is_valid)
        logger.info("VC verified successfully")

    def test_vc_verification_failure(self):
        """Test VC verification failure with an invalid did_key."""
        from apps.accounts.utils.did_utils import issue_vc, verify_vc

        credential = {
            "@context": ["https://www.w3.org/2018/credentials/v1"],
            "type": ["VerifiableCredential", "AuthenticationCredential"],
            "issuer": self.did,
            "issuanceDate": "2023-01-01T00:00:00Z",
            "credentialSubject": {
                "id": self.did,
                "name": "testuser",
            },
        }

        vc = issue_vc(credential, self.did, self.key)
        self.assertIsNotNone(vc)

        # Verify the VC with an invalid did_key
        invalid_key = didkit.generateEd25519Key()
        is_valid = verify_vc(vc, did_key=json.loads(invalid_key))
        self.assertFalse(is_valid)
        logger.info("VC verification correctly failed with invalid did_key")


if __name__ == "__main__":
    import unittest

    unittest.main()
