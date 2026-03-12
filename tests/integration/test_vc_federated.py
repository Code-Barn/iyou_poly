#!/usr/bin/env python
"""
Test script to verify the VC using the verify_federated_vc function.
"""

import json
import os

# Configure Django settings
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
import django

from apps.accounts.utils.did_utils import verify_federated_vc

django.setup()


def test_verify_federated_vc():
    """Test VC verification using verify_federated_vc."""
    # Read the test VC from the file
    vc = {
        "@context": ["https://www.w3.org/2018/credentials/v1"],
        "type": ["VerifiableCredential"],
        "issuer": "did:key:z6MkqYDbJ5yVgg5U7dMZb9oUNAkqo2bzPLMDjr4eh1rNMxNv",
        "issuanceDate": "2023-01-01T00:00:00Z",
        "credentialSubject": {
            "id": "did:key:z6MkqYDbJ5yVgg5U7dMZb9oUNAkqo2bzPLMDjr4eh1rNMxNv",
            "name": "Test User",
        },
        "proof": {
            "type": "Ed25519Signature2018",
            "created": "2023-01-01T00:00:00Z",
            "verificationMethod": "did:key:z6MkqYDbJ5yVgg5U7dMZb9oUNAkqo2bzPLMDjr4eh1rNMxNv#z6MkqYDbJ5yVgg5U7dMZb9oUNAkqo2bzPLMDjr4eh1rNMxNv",
            "proofPurpose": "assertionMethod",
            "jws": "eyJhbGciOiJFZERTQSIsImI2NCI6ZmFsc2UsImNyaXQiOlsiYjY0Il19..DnK5Uj2X23x3z6MpS4m56Z-8Vv5eF8L9R_tX1X0Y1X2X3X4X5X6X7X8X9X0X1X2X3X4X5X6X7X8X9X0X1XAA",
        },
    }

    vc_json = json.dumps(vc)
    issuer_did = vc.get("issuer")

    # Test verification
    result = verify_federated_vc(vc_json, issuer_did)
    print(f"Verification result: {result}")


if __name__ == "__main__":
    test_verify_federated_vc()
