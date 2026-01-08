"""
Minimal test to isolate the VC generation issue.
"""

import json
import logging

import didkit

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


def test_minimal_vc():
    """
    Minimal test for VC generation.
    """
    # Generate a key
    key = didkit.generateEd25519Key()
    logger.debug(f"Generated key: {key}")

    # Parse the key to ensure it has the private component
    key_dict = json.loads(key)
    logger.debug(f"Key structure: {json.dumps(key_dict, indent=2)}")

    # Generate a DID
    did = didkit.keyToDID("key", key)
    logger.debug(f"Generated DID: {did}")

    # Create a minimal credential
    credential = {
        "@context": ["https://www.w3.org/2018/credentials/v1"],
        "type": ["VerifiableCredential"],
        "issuer": did,
        "issuanceDate": "2023-01-01T00:00:00Z",
        "credentialSubject": {
            "id": did,
        },
    }

    # Create options
    vm = didkit.keyToVerificationMethod("key", key)
    options = {
        "proofPurpose": "assertionMethod",
        "verificationMethod": vm,
    }

    logger.debug(f"Verification method: {vm}")
    logger.debug(f"Options: {json.dumps(options)}")

    # Try to issue the credential
    try:
        vc = didkit.issueCredential(
            json.dumps(credential),
            json.dumps(options),
            key,
        )
        logger.debug(f"VC issued successfully: {vc}")
        return True
    except Exception as e:
        logger.error(f"Failed to issue VC: {e}")
        return False


if __name__ == "__main__":
    test_minimal_vc()
