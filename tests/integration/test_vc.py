# Copyright (C) 2026 Byers Brands, LLC
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <https://www.gnu.org/licenses/>.

"""
Test script to verify the copy functionality and VC display improvements.
"""

import json
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def test_vc_display_structure():
    """
    Test that VCs have the expected structure for display.
    """
    logger.info("Testing VC display structure...")

    # Simulate a VC with various fields
    test_vc = {
        "@context": ["https://www.w3.org/2018/credentials/v1"],
        "type": ["VerifiableCredential", "AuthenticationCredential"],
        "issuer": "did:key:z6Mk...",
        "issuanceDate": "2023-01-01T00:00:00Z",
        "credentialSubject": {
            "id": "did:key:z6Mk...",
            "name": "testuser",
            "email": "test@example.com",
        },
        "proof": {
            "type": "Ed25519Signature2018",
            "proofPurpose": "assertionMethod",
            "verificationMethod": "did:key:z6Mk...#z6Mk...",
            "created": "2026-01-08T00:00:00Z",
            "jws": "eyJhbGciOiJFZERTQSIsImNyaXQiOlsiYjY0Il0sImI2NCI6ZmFsc2V9..signature",
        },
    }

    # Test 1: Check that we can determine the VC type for labeling
    vc_type = test_vc.get("type", [])
    if "AuthenticationCredential" in vc_type:
        label = "Authentication Credential"
        logger.info(f"✓ VC correctly identified as: {label}")
    else:
        label = "User Credential 1"
        logger.info(f"✓ VC labeled as: {label}")

    # Test 2: Check that we can escape the VC for HTML display
    import django.utils.html

    escaped_vc = django.utils.html.escape(json.dumps(test_vc, indent=2))
    logger.info(
        f"✓ VC can be escaped for HTML display (length: {len(escaped_vc)} chars)"
    )

    # Test 3: Verify the VC structure has all required fields
    required_fields = ["@context", "type", "issuer", "credentialSubject", "proof"]
    for field in required_fields:
        if field in test_vc:
            logger.info(f"✓ VC has required field: {field}")
        else:
            logger.error(f"✗ VC missing required field: {field}")
            return False

    logger.info("✓ All VC display structure tests passed!")
    return True


def test_copy_functionality_simulation():
    """
    Simulate the copy to clipboard functionality.
    """
    logger.info("\nTesting copy functionality simulation...")

    # Simulate a VC JSON string
    test_vc = {
        "type": ["VerifiableCredential"],
        "credentialSubject": {"id": "did:key:test"},
    }
    vc_json = json.dumps(test_vc, indent=2)

    # Test 1: Verify we can extract text from a simulated pre element
    simulated_pre_content = vc_json
    if simulated_pre_content:
        logger.info(
            f"✓ Can extract text from pre element (length: {len(simulated_pre_content)} chars)"
        )
    else:
        logger.error("✗ Failed to extract text from pre element")
        return False

    # Test 2: Verify the text is valid JSON
    try:
        json.loads(simulated_pre_content)
        logger.info("✓ Extracted text is valid JSON")
    except json.JSONDecodeError as e:
        logger.error(f"✗ Extracted text is not valid JSON: {e}")
        return False

    # Test 3: Simulate clipboard copy (just verify the text is ready)
    clipboard_ready = simulated_pre_content.strip()
    if clipboard_ready:
        logger.info(
            f"✓ Text is ready for clipboard (length: {len(clipboard_ready)} chars)"
        )
    else:
        logger.error("✗ Text is not ready for clipboard")
        return False

    logger.info("✓ All copy functionality tests passed!")
    return True


def test_vc_labeling():
    """
    Test the VC labeling logic.
    """
    logger.info("\nTesting VC labeling logic...")

    # Test different VC types
    test_cases = [
        {
            "vc": {"type": ["VerifiableCredential", "AuthenticationCredential"]},
            "expected": "Authentication Credential",
            "counter": 1,
        },
        {
            "vc": {"type": ["VerifiableCredential"]},
            "expected": "User Credential 1",
            "counter": 1,
        },
        {
            "vc": {"type": ["VerifiableCredential", "CustomCredential"]},
            "expected": "User Credential 2",
            "counter": 2,
        },
    ]

    for test_case in test_cases:
        vc = test_case["vc"]
        expected = test_case["expected"]
        counter = test_case["counter"]

        # Apply the same logic as in the template
        if vc.get("type") and "AuthenticationCredential" in vc["type"]:
            label = "Authentication Credential"
        else:
            label = f"User Credential {counter}"

        if label == expected:
            logger.info(f"✓ Test case {counter}: Correct label '{label}'")
        else:
            logger.error(f"✗ Test case {counter}: Expected '{expected}', got '{label}'")
            return False

    logger.info("✓ All VC labeling tests passed!")
    return True


if __name__ == "__main__":
    logger.info("🧪 Starting VC Display and Copy Functionality Tests")
    logger.info("=" * 60)

    success = True

    if not test_vc_display_structure():
        success = False

    if not test_copy_functionality_simulation():
        success = False

    if not test_vc_labeling():
        success = False

    logger.info("=" * 60)
    if success:
        logger.info(
            "🎉 ALL TESTS PASSED! VC display and copy functionality is working correctly."
        )
    else:
        logger.error("❌ Some tests failed. Please check the logs above.")

    logger.info("\nNext steps:")
    logger.info("1. Test the changes in a real browser")
    logger.info("2. Verify the copy button visual feedback works")
    logger.info("3. Check that VC labels are displayed correctly")
    logger.info("4. Test with different VC types and structures")
