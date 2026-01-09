"""
Test script to simulate the registration and VC generation process.
"""

import json
import logging

import didkit

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


def test_did_vc_generation():
    """
    Test the DID and VC generation process.
    """
    # Generate a DID
    key = didkit.generateEd25519Key()
    did = didkit.keyToDID("key", key)
    logger.debug(f"Generated DID: {did}")
    logger.debug(f"Key: {key}")
    logger.debug(f"Key type: {type(key)}")

    # Parse the key to see its structure
    try:
        key_dict = json.loads(key)
        logger.debug(f"Key structure: {json.dumps(key_dict, indent=2)}")

        # Check if the key has the required 'd' parameter
        if "d" not in key_dict:
            logger.error("Key is missing the 'd' (private key) parameter!")
        else:
            logger.debug(f"Private key 'd' length: {len(key_dict['d'])}")

        # Check base64url encoding
        import base64
        import re

        # Check if the values are proper base64url
        x_value = key_dict.get("x", "")
        d_value = key_dict.get("d", "")

        logger.debug(f"x value: {x_value}")
        logger.debug(f"d value: {d_value}")

        # Check for invalid base64url characters
        base64url_pattern = r"^[A-Za-z0-9_-]+$"
        if not re.match(base64url_pattern, x_value):
            logger.error(f"x value contains invalid base64url characters: {x_value}")
        if not re.match(base64url_pattern, d_value):
            logger.error(f"d value contains invalid base64url characters: {d_value}")

        # Check for padding characters
        if "=" in x_value:
            logger.error(f"x value contains padding (=): {x_value}")
        if "=" in d_value:
            logger.error(f"d value contains padding (=): {d_value}")

    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse key: {e}")

    # Derive the verification method from the key
    vm = didkit.keyToVerificationMethod("key", key)
    logger.debug(f"Verification method: {vm}")

    # Define the credential
    credential = {
        "@context": ["https://www.w3.org/2018/credentials/v1"],
        "type": ["VerifiableCredential", "AuthenticationCredential"],
        "issuer": did,
        "issuanceDate": "2023-01-01T00:00:00Z",
        "credentialSubject": {
            "id": did,
        },
    }
    logger.debug(f"Credential: {credential}")

    # Store the name parameter to re-add it after issuing the VC
    name = "testuser"

    # Define the options
    options = {
        "proofPurpose": "assertionMethod",
        "verificationMethod": vm,
    }
    logger.debug(f"Options: {options}")

    # Issue the credential
    # Try using the key directly without JSON serialization
    vc = didkit.issueCredential(
        json.dumps(credential),
        json.dumps(options),
        key,
    )
    logger.debug(f"VC: {vc}")

    if vc:
        logger.debug("VC issued successfully")

        # Re-add the name parameter to the VC
        vc_dict = json.loads(vc)
        vc_dict["credentialSubject"]["name"] = name
        vc = json.dumps(vc_dict)

        return True
    else:
        logger.error("VC issuance failed")
        return False


if __name__ == "__main__":
    test_did_vc_generation()
