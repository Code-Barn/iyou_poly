#!/usr/bin/env python3
"""
Test script to verify the provided VC and key pair.

This script:
1. Tests the provided VC and key pair using manual JWS verification.
"""

import json
import logging
import sys

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Add the project root to the Python path
sys.path.append("/home/user/CODE_BASE/polly")

from apps.accounts.utils.did_utils import verify_vc


def test_provided_vc():
    """Test the provided VC and key pair."""
    logger.info("Testing provided VC and key pair")

    # Provided VC and key pair
    vc_str = """{
        "@context": ["https://www.w3.org/2018/credentials/v1"],
        "type": ["VerifiableCredential", "AuthenticationCredential"],
        "credentialSubject": {
            "id": "did:key:z6MkoBT32xB9VQHhF9r3gdNTY6a9WWoCSAHBzLQwWMX5VGLa",
            "name": "kdalfkjsd"
        },
        "issuer": "did:key:z6MkoBT32xB9VQHhF9r3gdNTY6a9WWoCSAHBzLQwWMX5VGLa",
        "issuanceDate": "2023-01-01T00:00:00Z",
        "proof": {
            "type": "Ed25519Signature2018",
            "proofPurpose": "assertionMethod",
            "verificationMethod": "did:key:z6MkoBT32xB9VQHhF9r3gdNTY6a9WWoCSAHBzLQwWMX5VGLa#z6MkoBT32xB9VQHhF9r3gdNTY6a9WWoCSAHBzLQwWMX5VGLa",
            "created": "2026-01-13T01:23:24.478Z",
            "jws": "eyJhbGciOiJFZERTQSIsImNyaXQiOlsiYjY0Il0sImI2NCI6ZmFsc2V9..N-EWBQVYwiwT7VkJJQMpeaDO-oSAC0xnXzouBJJ0J6tw5ZBCARVcs5cCMhujI2YUSI08j7uy8z0ejZ_2YZxMBw"
        }
    }"""

    did_key = {
        "kty": "OKP",
        "crv": "Ed25519",
        "x": "aSSepUhfGWlSXkqIT_ejwxReOaX_V7WHDBWVdIAPSqs",
        "d": "oI-SSP4uw714VeX6T6L2NPeujDtGeC8JqkqS2yjh2bQ",
    }

    vc_data = json.loads(vc_str)

    # Verify the VC with the did_key (manual JWS verification)
    logger.info("Verifying provided VC with did_key")
    if not verify_vc(vc_str, did_key=did_key):
        logger.error("Provided VC verification failed with did_key")
        return False

    # Verify the VC with the did_key (manual JWS verification)
    logger.info("Verifying provided VC with did_key")
    if not verify_vc(vc_str, did_key=did_key):
        logger.error("Provided VC verification failed with did_key")
        return False

    logger.info("Provided VC verification succeeded")
    return True


if __name__ == "__main__":
    # Test the provided VC
    logger.info("=== Testing provided VC ===")
    success = test_provided_vc()
    if success:
        logger.info("Provided VC test passed")
        sys.exit(0)
    else:
        logger.error("Provided VC test failed")
        sys.exit(1)
