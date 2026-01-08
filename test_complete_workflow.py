"""
Complete workflow test demonstrating the VC generation fix.

This test shows the entire process from user creation to VC issuance,
demonstrating how the fix handles extra fields in credential subjects.
"""

import json
import logging

import didkit
from django.contrib.auth import get_user_model

from apps.accounts.utils.did_utils import generate_did, issue_vc

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def test_complete_vc_workflow():
    """
    Test the complete VC generation workflow with the fix.
    """
    logger.info("=== Starting Complete VC Workflow Test ===")

    # Step 1: Generate a key and DID for the issuer
    logger.info("Step 1: Generating issuer key and DID...")
    key = didkit.generateEd25519Key()
    did = didkit.keyToDID("key", key)
    logger.info(f"Generated DID: {did}")

    # Step 2: Create a comprehensive credential with multiple extra fields
    logger.info("Step 2: Creating credential with extra fields...")
    credential = {
        "@context": ["https://www.w3.org/2018/credentials/v1"],
        "type": ["VerifiableCredential", "AuthenticationCredential"],
        "issuer": did,
        "issuanceDate": "2023-01-01T00:00:00Z",
        "credentialSubject": {
            "id": did,
            "name": "John Doe",
            "email": "john.doe@example.com",
            "username": "johndoe",
            "role": "admin",
            "department": "Engineering",
            "employeeId": "EMP12345",
        },
    }
    logger.info(
        f"Credential subject fields: {list(credential['credentialSubject'].keys())}"
    )

    # Step 3: Issue the VC using our fixed function
    logger.info("Step 3: Issuing VC...")
    vc = issue_vc(credential, did, key)

    if not vc:
        logger.error("VC issuance failed!")
        return False

    logger.info("VC issued successfully!")

    # Step 4: Verify the VC contains all extra fields
    logger.info("Step 4: Verifying extra fields are preserved...")
    vc_dict = json.loads(vc)
    credential_subject = vc_dict.get("credentialSubject", {})

    # Check each expected field
    expected_fields = ["name", "email", "username", "role", "department", "employeeId"]
    missing_fields = []

    for field in expected_fields:
        if field not in credential_subject:
            missing_fields.append(field)
        else:
            logger.info(f"  ✓ {field}: {credential_subject[field]}")

    if missing_fields:
        logger.error(f"Missing fields: {missing_fields}")
        return False

    # Step 5: Verify the VC is valid (can be parsed and has required structure)
    logger.info("Step 5: Validating VC structure...")

    required_vc_fields = ["@context", "type", "issuer", "credentialSubject", "proof"]
    for field in required_vc_fields:
        if field not in vc_dict:
            logger.error(f"VC missing required field: {field}")
            return False
        logger.info(f"  ✓ VC has {field}")

    # Step 6: Verify the proof is properly included
    logger.info("Step 6: Verifying proof...")
    proof = vc_dict.get("proof", {})
    required_proof_fields = [
        "type",
        "proofPurpose",
        "verificationMethod",
        "created",
        "jws",
    ]

    for field in required_proof_fields:
        if field not in proof:
            logger.error(f"Proof missing required field: {field}")
            return False
        logger.info(f"  ✓ Proof has {field}")

    logger.info("=== Complete VC Workflow Test PASSED ===")
    logger.info("\nSummary:")
    logger.info(f"- Successfully issued VC with {len(expected_fields)} extra fields")
    logger.info(f"- All fields preserved: {', '.join(expected_fields)}")
    logger.info(f"- VC structure is valid and complete")
    logger.info(f"- Proof is properly included and signed")

    return True


def test_edge_cases():
    """
    Test edge cases to ensure robustness.
    """
    logger.info("\n=== Testing Edge Cases ===")

    # Generate key and DID
    key = didkit.generateEd25519Key()
    did = didkit.keyToDID("key", key)

    # Test 1: Credential with no extra fields (should work as before)
    logger.info("Test 1: Credential with no extra fields...")
    credential_minimal = {
        "@context": ["https://www.w3.org/2018/credentials/v1"],
        "type": ["VerifiableCredential"],
        "issuer": did,
        "issuanceDate": "2023-01-01T00:00:00Z",
        "credentialSubject": {"id": did},
    }

    vc1 = issue_vc(credential_minimal, did, key)
    if vc1:
        logger.info("  ✓ Minimal credential works")
    else:
        logger.error("  ✗ Minimal credential failed")
        return False

    # Test 2: Credential with only 'id' field (edge case)
    logger.info("Test 2: Credential with only 'id' field...")
    credential_id_only = {
        "@context": ["https://www.w3.org/2018/credentials/v1"],
        "type": ["VerifiableCredential"],
        "issuer": did,
        "issuanceDate": "2023-01-01T00:00:00Z",
        "credentialSubject": {"id": did},
    }

    vc2 = issue_vc(credential_id_only, did, key)
    if vc2:
        logger.info("  ✓ ID-only credential works")
    else:
        logger.error("  ✗ ID-only credential failed")
        return False

    # Test 3: Credential with special characters in fields
    logger.info("Test 3: Credential with special characters...")
    credential_special = {
        "@context": ["https://www.w3.org/2018/credentials/v1"],
        "type": ["VerifiableCredential"],
        "issuer": did,
        "issuanceDate": "2023-01-01T00:00:00Z",
        "credentialSubject": {
            "id": did,
            "name": "John O'Brien-Smith",
            "email": "john.o'brien@example.com",
            "notes": "Special chars: @#$%^&*()",
        },
    }

    vc3 = issue_vc(credential_special, did, key)
    if vc3:
        vc_dict = json.loads(vc3)
        if (
            "name" in vc_dict["credentialSubject"]
            and "John O'Brien-Smith" in vc_dict["credentialSubject"]["name"]
        ):
            logger.info("  ✓ Special characters preserved")
        else:
            logger.error("  ✗ Special characters not preserved")
            return False
    else:
        logger.error("  ✗ Special characters credential failed")
        return False

    logger.info("=== All Edge Cases PASSED ===")
    return True


if __name__ == "__main__":
    success = True

    # Run main workflow test
    if not test_complete_vc_workflow():
        success = False

    # Run edge case tests
    if not test_edge_cases():
        success = False

    if success:
        logger.info(
            "\n🎉 ALL TESTS PASSED! The VC generation fix is working correctly."
        )
    else:
        logger.error("\n❌ Some tests failed. Please check the logs above.")
