"""
Test the fixed issue_vc function with name field.
"""

import json
import logging

from apps.accounts.utils.did_utils import issue_vc

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


def test_fixed_vc():
    """
    Test the fixed VC generation with name field.
    """
    import didkit

    # Generate a key
    key = didkit.generateEd25519Key()
    logger.debug(f"Generated key: {key}")

    # Generate a DID
    did = didkit.keyToDID("key", key)
    logger.debug(f"Generated DID: {did}")

    # Create credential with name field (this should now work)
    credential = {
        "@context": ["https://www.w3.org/2018/credentials/v1"],
        "type": ["VerifiableCredential", "AuthenticationCredential"],
        "issuer": did,
        "issuanceDate": "2023-01-01T00:00:00Z",
        "credentialSubject": {
            "id": did,
            "name": "testuser",
            "email": "test@example.com",
            "role": "user",
        },
    }

    logger.debug(f"Credential: {credential}")

    # Try to issue the credential using our fixed function
    try:
        vc = issue_vc(credential, did, key)
        logger.debug(f"VC issued successfully: {vc}")

        # Parse the VC to verify it contains all extra fields
        vc_dict = json.loads(vc)
        credential_subject = vc_dict.get("credentialSubject", {})
        if (
            "name" in credential_subject
            and "email" in credential_subject
            and "role" in credential_subject
        ):
            logger.debug(f"All extra fields preserved:")
            logger.debug(f"  Name: {credential_subject['name']}")
            logger.debug(f"  Email: {credential_subject['email']}")
            logger.debug(f"  Role: {credential_subject['role']}")
            return True
        else:
            logger.error("Not all extra fields were preserved in the VC")
            logger.error(f"Credential subject: {credential_subject}")
            return False
    except Exception as e:
        logger.error(f"Failed to issue VC: {e}")
        return False


if __name__ == "__main__":
    test_fixed_vc()
