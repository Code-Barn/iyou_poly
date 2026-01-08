"""
Test with AuthenticationCredential type to see if that's causing the issue.
"""

import json
import logging

import didkit

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


def test_auth_vc():
    """
    Test VC generation with AuthenticationCredential type.
    """
    # Generate a key
    key = didkit.generateEd25519Key()
    logger.debug(f"Generated key: {key}")

    # Generate a DID
    did = didkit.keyToDID("key", key)
    logger.debug(f"Generated DID: {did}")

    # Create credential with AuthenticationCredential type but no extra fields
    credential = {
        "@context": ["https://www.w3.org/2018/credentials/v1"],
        "type": ["VerifiableCredential", "AuthenticationCredential"],
        "issuer": did,
        "issuanceDate": "2023-01-01T00:00:00Z",
        "credentialSubject": {
            "id": did,
        },
    }

    # Create options using the alternative approach
    vm = f"{did}#{did.split(':')[-1]}"
    options = {
        "proofPurpose": "assertionMethod",
        "verificationMethod": vm,
    }

    logger.debug(f"Verification method: {vm}")

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
    test_auth_vc()
