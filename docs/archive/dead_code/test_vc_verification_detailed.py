#!/usr/bin/env python3
"""
Test script for VC verification using DIDKit.

This script tests the full VC lifecycle:
1. Generate a DID and key
2. Issue a VC
3. Verify the VC
4. Debug the verification process
"""

import json
import logging
import sys

import didkit

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


def generate_did_and_key():
    """Generate a DID and key for testing."""
    logger.info("Generating DID and key")
    key = didkit.generateEd25519Key()
    did = didkit.keyToDID("key", key)
    logger.debug(f"Generated DID: {did}")
    logger.debug(f"Generated key: {key}")
    return did, key


def issue_test_vc(did, key):
    """Issue a test VC using the generated DID and key."""
    logger.info("Issuing test VC")

    # Store extra fields to restore after issuance
    credential_subject = {
        "id": did,
        "name": "Test User",
    }
    extra_fields = {}
    for field_name in list(credential_subject.keys()):
        if field_name != "id":
            extra_fields[field_name] = credential_subject.pop(field_name)

    credential = {
        "@context": ["https://www.w3.org/2018/credentials/v1"],
        "type": ["VerifiableCredential", "AuthenticationCredential"],
        "issuer": did,
        "issuanceDate": "2023-01-01T00:00:00Z",
        "credentialSubject": credential_subject,
    }

    options = {
        "proofPurpose": "assertionMethod",
        "verificationMethod": f"{did}#{did.split(':')[-1]}",
    }

    vc = didkit.issueCredential(json.dumps(credential), json.dumps(options), key)
    vc_data = json.loads(vc)

    # Restore extra fields after issuance
    if extra_fields:
        vc_data["credentialSubject"].update(extra_fields)
        logger.debug(f"Restored extra fields: {list(extra_fields.keys())}")

    logger.debug(f"Issued VC: {json.dumps(vc_data, indent=2)}")
    return vc_data


def verify_vc(vc_data, did_key=None):
    """Verify a VC using DIDKit.

    Args:
        vc_data: The VC to verify (as a dictionary).
        did_key: Optional private key (JWK format) to use for verification.
    """
    logger.info("Verifying VC")

    # Import the verify_vc function from the Polly project
    sys.path.append("/home/user/CODE_BASE/polly")
    from apps.accounts.utils.did_utils import verify_vc as polly_verify_vc

    # Test 1: Verify with the updated verify_vc function from Polly
    try:
        vc_str = json.dumps(vc_data)
        result = polly_verify_vc(vc_str, did_key=did_key)
        logger.info(f"VC verification result: {result}")
        return result
    except Exception as e:
        logger.error(f"Failed to verify VC: {e}")
        return False


def debug_did_resolution(did):
    """Debug DID resolution."""
    logger.info(f"Debugging DID resolution for: {did}")

    try:
        did_document = didkit.resolveDID(did, "application/did+ld+json")
        did_document = json.loads(did_document)
        logger.debug(f"Resolved DID document: {json.dumps(did_document, indent=2)}")
        return did_document
    except Exception as e:
        logger.error(f"Failed to resolve DID: {e}")
        return None


def debug_jws_verification(vc_data):
    """Debug JWS verification."""
    logger.info("Debugging JWS verification")

    try:
        # Get the public key from the DID document
        did = vc_data["issuer"]
        did_document = debug_did_resolution(did)
        if not did_document:
            return False

        verification_method = vc_data["proof"]["verificationMethod"]
        public_key = None

        for method in did_document.get("verificationMethod", []):
            if method.get("id") == verification_method:
                public_key = method.get("publicKeyJwk")
                break

        if not public_key:
            logger.error("Public key not found in DID Document")
            return False

        logger.debug(f"Extracted public key: {json.dumps(public_key, indent=2)}")

        # Verify the JWS
        jws = vc_data["proof"]["jws"]
        vc_without_proof = vc_data.copy()
        vc_without_proof.pop("proof", None)
        vc_without_proof = json.dumps(vc_without_proof, separators=(",", ":"))

        verification_result = didkit.verifyJWS(jws, public_key, vc_without_proof)
        logger.debug(f"JWS verification result: {verification_result}")

        if verification_result:
            logger.info("JWS verification succeeded")
            return True
        else:
            logger.error("JWS verification failed")
            return False
    except Exception as e:
        logger.error(f"Failed to verify JWS: {e}")
        return False


def test_vc_lifecycle():
    """Test the full VC lifecycle: generate, issue, verify."""
    logger.info("Starting VC lifecycle test")

    # Step 1: Generate DID and key
    did, key = generate_did_and_key()

    # Step 2: Issue VC
    vc_data = issue_test_vc(did, key)
    if not vc_data:
        logger.error("Failed to issue VC")
        return False

    # Step 3: Verify VC without did_key
    logger.info("Testing VC verification without did_key")
    if not verify_vc(vc_data):
        logger.error("VC verification failed without did_key")
        logger.info("Debugging VC verification...")

        # Debug DID resolution
        debug_did_resolution(did)

        # Debug JWS verification
        debug_jws_verification(vc_data)

        return False

    # Step 4: Verify VC with did_key
    logger.info("Testing VC verification with did_key")
    if not verify_vc(vc_data, did_key=key):
        logger.error("VC verification failed with did_key")
        return False

    logger.info("VC lifecycle test passed")
    return True


def test_provided_vc():
    """Test the provided VC and DID key."""
    logger.info("Testing provided VC and DID key")

    # Provided VC and DID key
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

    # Test 2: Verify VC with did_key
    logger.info("Testing provided VC with did_key")
    if not verify_vc(vc_data, did_key=json.dumps(did_key)):
        logger.error("Provided VC verification failed with did_key")
        return False

    logger.info("Provided VC test passed")
    return True


if __name__ == "__main__":
    # Test 2: Provided VC test
    success = test_provided_vc()
    if success:
        logger.info("Provided VC test passed")
        sys.exit(0)
    else:
        logger.error("Provided VC test failed")
        sys.exit(1)
