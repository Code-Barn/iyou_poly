#!/usr/bin/env python3
"""
Test script to verify the provided VC and key pair.

This script:
1. Tests the provided VC and key pair using manual JWS verification.
"""

import logging
import sys

from apps.accounts.utils.did_utils import verify_vc

# Add the project root to the Python path
sys.path.append("/home/user/CODE_BASE/polly")


# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


def test_provided_vc():
    """Test the provided VC and key pair."""
    logger.info("Testing provided VC and key pair")

    # Test VC and key pair
    vc_str = """{
        "@context": ["https://www.w3.org/2018/credentials/v1"],
        "type": ["VerifiableCredential"],
        "issuer": "did:key:z6MkqYDbJ5yVgg5U7dMZb9oUNAkqo2bzPLMDjr4eh1rNMxNv",
        "issuanceDate": "2023-01-01T00:00:00Z",
        "credentialSubject": {
            "id": "did:key:z6MkqYDbJ5yVgg5U7dMZb9oUNAkqo2bzPLMDjr4eh1rNMxNv",
            "name": "Test User"
        },
        "proof": {
            "type": "Ed25519Signature2018",
            "created": "2023-01-01T00:00:00Z",
            "verificationMethod": "did:key:z6MkqYDbJ5yVgg5U7dMZb9oUNAkqo2bzPLMDjr4eh1rNMxNv#z6MkqYDbJ5yVgg5U7dMZb9oUNAkqo2bzPLMDjr4eh1rNMxNv",
            "proofPurpose": "assertionMethod",
            "jws": "eyJhbGciOiJFZERTQSIsImI2NCI6ZmFsc2UsImNyaXQiOlsiYjY0Il19..DnK5Uj2X23x3z6MpS4m56Z-8Vv5eF8L9R_tX1X0Y1X2X3X4X5X6X7X8X9X0X1X2X3X4X5X6X7X8X9X0X1XAA"
        }
    }"""

    did_key = {
        "kty": "OKP",
        "d": "oI-SSP4uw714VeX6T6L2NPeujDtGeC8JqkqS2yjh2bQ",
        "crv": "Ed25519",
        "x": "aSSepUhfGWlSXkqIT_ejwxReOaX_V7WHDBWVdIAPSqs",
    }

    # Verify the VC with the did_key (manual JWS verification)
    logger.info("Verifying provided VC with did_key")
    if not verify_vc(vc_str, did_key=did_key):
        logger.error("Provided VC verification failed with did_key")
        return False

    logger.info("Provided VC verification successful")
    return True


if __name__ == "__main__":
    test_provided_vc()
