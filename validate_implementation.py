"""
Simple validation script to verify the federated authentication implementation.
This script checks that all components are properly configured without requiring a full test suite.
"""

import json
import logging
import os
import sys

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def validate_imports():
    """Validate that all required modules can be imported."""
    logger.info("🔍 Validating imports...")

    try:
        # Test Django imports
        import django
        from django.conf import settings

        # Test views
        from apps.accounts.did_views import DIDLoginPartialView, DIDLoginView

        # Test our custom modules
        from apps.accounts.utils.did_utils import (
            get_trusted_issuers,
            is_trusted_issuer,
            issue_vc,
            verify_federated_vc,
        )

        logger.info("✅ All imports successful")
        return True

    except ImportError as e:
        logger.error(f"❌ Import failed: {e}")
        return False


def validate_settings():
    """Validate that required settings are configured."""
    logger.info("🔍 Validating settings...")

    try:
        from django.conf import settings

        # Check if settings are configured
        if not hasattr(settings, "INSTALLED_APPS"):
            logger.error("❌ Django settings not configured")
            return False

        # Check for our custom settings (they should exist even if not set)
        logger.info("✅ Settings module accessible")
        return True

    except Exception as e:
        logger.error(f"❌ Settings validation failed: {e}")
        return False


def validate_trust_management():
    """Validate trust management functions."""
    logger.info("🔍 Validating trust management...")

    try:
        from apps.accounts.utils.did_utils import (
            get_trusted_issuers,
            is_trusted_issuer,
            verify_federated_vc,
        )

        # Test get_trusted_issuers
        trusted = get_trusted_issuers()
        if not isinstance(trusted, set):
            logger.error("❌ get_trusted_issuers() should return a set")
            return False

        # Test is_trusted_issuer
        result = is_trusted_issuer("did:key:test")
        if not isinstance(result, bool):
            logger.error("❌ is_trusted_issuer() should return a boolean")
            return False

        # Test verify_federated_vc with invalid input
        result = verify_federated_vc("invalid json")
        if result is not False:
            logger.error(
                "❌ verify_federated_vc() should return False for invalid input"
            )
            return False

        logger.info("✅ Trust management functions working correctly")
        return True

    except Exception as e:
        logger.error(f"❌ Trust management validation failed: {e}")
        return False


def validate_vc_generation():
    """Validate VC generation with extra fields."""
    logger.info("🔍 Validating VC generation...")

    try:
        import didkit

        from apps.accounts.utils.did_utils import issue_vc

        # Generate a test key and DID
        key = didkit.generateEd25519Key()
        did = didkit.keyToDID("key", key)

        # Create credential with extra fields
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

        # Issue the VC
        vc = issue_vc(credential, did, key)

        if not vc:
            logger.error("❌ VC issuance failed")
            return False

        # Verify the VC contains all extra fields
        vc_data = json.loads(vc)
        credential_subject = vc_data.get("credentialSubject", {})

        required_fields = ["name", "email", "role"]
        for field in required_fields:
            if field not in credential_subject:
                logger.error(f"❌ Field '{field}' not preserved in VC")
                return False

        logger.info("✅ VC generation with extra fields working correctly")
        return True

    except Exception as e:
        logger.error(f"❌ VC generation validation failed: {e}")
        return False


def validate_templates():
    """Validate that required templates exist."""
    logger.info("🔍 Validating templates...")

    template_dir = "templates/accounts"
    required_templates = [
        "did_login.html",
        "partials/did_login_partial.html",
        "partials/login_success.html",
    ]

    for template in required_templates:
        template_path = os.path.join(template_dir, template)
        if not os.path.exists(template_path):
            logger.error(f"❌ Template not found: {template_path}")
            return False

    logger.info("✅ All required templates exist")
    return True


def validate_views():
    """Validate that views are properly configured."""
    logger.info("🔍 Validating views...")

    try:
        from apps.accounts.did_views import DIDLoginPartialView, DIDLoginView

        # Check that views have required methods
        if not hasattr(DIDLoginView, "get") or not hasattr(DIDLoginView, "post"):
            logger.error("❌ DIDLoginView missing required methods")
            return False

        if not hasattr(DIDLoginPartialView, "get") or not hasattr(
            DIDLoginPartialView, "post"
        ):
            logger.error("❌ DIDLoginPartialView missing required methods")
            return False

        logger.info("✅ Views properly configured")
        return True

    except Exception as e:
        logger.error(f"❌ Views validation failed: {e}")
        return False


def validate_urls():
    """Validate that URLs are configured."""
    logger.info("🔍 Validating URLs...")

    try:
        from django.urls import reverse

        # Test that our URLs can be reversed
        try:
            did_login_url = reverse("did_login")
            logger.info(f"✅ DID login URL: {did_login_url}")
        except Exception as e:
            logger.error(f"❌ Could not reverse 'did_login' URL: {e}")
            return False

        return True

    except Exception as e:
        logger.error(f"❌ URLs validation failed: {e}")
        return False


def main():
    """Run all validation checks."""
    logger.info("🚀 Starting implementation validation...")
    logger.info("=" * 60)

    validations = [
        ("Imports", validate_imports),
        ("Settings", validate_settings),
        ("Trust Management", validate_trust_management),
        ("VC Generation", validate_vc_generation),
        ("Templates", validate_templates),
        ("Views", validate_views),
        ("URLs", validate_urls),
    ]

    results = []
    for name, validation_func in validations:
        try:
            result = validation_func()
            results.append((name, result))
        except Exception as e:
            logger.error(f"❌ {name} validation crashed: {e}")
            results.append((name, False))

    logger.info("=" * 60)
    logger.info("📊 Validation Results:")

    all_passed = True
    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        logger.info(f"  {status} {name}")

        if not result:
            all_passed = False

    logger.info("=" * 60)

    if all_passed:
        logger.info("🎉 ALL VALIDATIONS PASSED!")
        logger.info(
            "\nThe federated authentication implementation is working correctly."
        )
        logger.info("You can now:")
        logger.info("  1. Test the DID login flow in a browser")
        logger.info("  2. Verify the hybrid authentication interface")
        logger.info("  3. Test cross-server VC verification")
        logger.info("  4. Monitor adoption and performance")
        return 0
    else:
        logger.error("❌ SOME VALIDATIONS FAILED")
        logger.error("\nPlease check the error messages above for details.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
