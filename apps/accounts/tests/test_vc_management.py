"""
Tests for Verifiable Credential (VC) management functionality.

This module contains comprehensive tests for:
- VC generation with custom names and types
- VC import with validation
- VC naming and metadata management
- VC format migration
- User permissions and authentication
"""

import json
from unittest.mock import patch

from django.test import TestCase
from django.urls import reverse

from apps.accounts.models import User
from apps.accounts.tests.utils import (
    create_test_user,
    create_test_vc,
    create_vc_with_metadata,
    login_test_user,
)


class VCManagementTests(TestCase):
    """Comprehensive tests for VC management functionality."""

    def setUp(self):
        """Set up test data with improved isolation and consistency."""
        super().setUp()

        # Create a test user with consistent DID and key
        self.user = User.objects.create_user(
            username="testuser",
            password="testpass123",
            did="did:key:z6Mktestuser123",
            did_key=json.dumps(
                {
                    "kty": "OKP",
                    "crv": "Ed25519",
                    "x": "test_public_key",
                    "d": "test_private_key",
                }
            ),
        )
        self.client.login(username="testuser", password="testpass123")

        # Sample VC templates with consistent structure
        self.sample_vc = {
            "@context": ["https://www.w3.org/2018/credentials/v1"],
            "type": ["VerifiableCredential", "TestCredential"],
            "issuer": self.user.did,
            "issuanceDate": "2023-01-01T00:00:00Z",
            "credentialSubject": {
                "id": self.user.did,
                "name": self.user.username,
                "description": "Test credential",
            },
        }

        # Sample VC with ProfessionalCredential type for testing
        self.professional_vc = {
            "@context": ["https://www.w3.org/2018/credentials/v1"],
            "type": ["VerifiableCredential", "ProfessionalCredential"],
            "issuer": self.user.did,
            "issuanceDate": "2023-01-01T00:00:00Z",
            "credentialSubject": {
                "id": self.user.did,
                "name": self.user.username,
                "description": "Professional credential",
            },
        }

        self.auth_vc = {
            "@context": ["https://www.w3.org/2018/credentials/v1"],
            "type": ["VerifiableCredential", "AuthenticationCredential"],
            "issuer": self.user.did,
            "issuanceDate": "2023-01-01T00:00:00Z",
            "credentialSubject": {
                "id": self.user.did,
                "name": self.user.username,
            },
        }

        # Sample VC with proof for testing
        self.sample_vc_with_proof = self.sample_vc.copy()
        self.sample_vc_with_proof["proof"] = {
            "type": "Ed25519Signature2018",
            "proofPurpose": "assertionMethod",
            "verificationMethod": f"{self.user.did}#key-1",
            "created": "2023-01-01T00:00:00Z",
            "jws": "mock_jws_signature",
        }

    def test_vc_management_view_authenticated(self):
        """Test that authenticated users can access VC management page."""
        response = self.client.get(reverse("vc_management"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Verifiable Credentials")
        self.assertContains(response, "Other Credentials")

    def test_vc_management_view_unauthenticated(self):
        """Test that unauthenticated users are redirected to login with next parameter."""
        self.client.logout()
        response = self.client.get(reverse("vc_management"))
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, f"/login/?next={reverse('vc_management')}")

    @patch("apps.accounts.views.issue_vc")
    def test_generate_credential_view(self, mock_issue_vc):
        """Test that users can generate new credentials with custom names and types."""
        # Setup mock with the expected ProfessionalCredential type
        professional_vc_with_proof = self.professional_vc.copy()
        professional_vc_with_proof["proof"] = {
            "type": "Ed25519Signature2018",
            "proofPurpose": "assertionMethod",
            "verificationMethod": f"{self.user.did}#key-1",
            "created": "2023-01-01T00:00:00Z",
            "jws": "mock_jws_signature",
        }
        mock_issue_vc.return_value = json.dumps(professional_vc_with_proof)

        response = self.client.post(
            reverse("generate_credential"),
            {
                "credential_name": "Professional Certification",
                "credential_type": "ProfessionalCredential",
            },
        )

        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse("vc_management"))

        # Check that the VC was added to the user with correct metadata
        self.user.refresh_from_db()
        self.assertEqual(len(self.user.vcs), 1)
        self.assertEqual(self.user.vcs[0]["name"], "Professional Certification")
        self.assertEqual(
            self.user.vcs[0]["credential"]["type"],
            ["VerifiableCredential", "ProfessionalCredential"],
        )
        self.assertIn("added_date", self.user.vcs[0])

    @patch("apps.accounts.views.issue_vc")
    def test_generate_credential_with_empty_name(self, mock_issue_vc):
        """Test that credentials can be generated with empty names (uses type as name)."""
        # Setup mock
        mock_issue_vc.return_value = json.dumps(self.sample_vc_with_proof)

        response = self.client.post(
            reverse("generate_credential"),
            {
                "credential_name": "",
                "credential_type": "MembershipCredential",
            },
        )

        self.assertEqual(response.status_code, 302)
        self.user.refresh_from_db()
        self.assertEqual(len(self.user.vcs), 1)
        # Should use the credential type as the name when name is empty
        self.assertEqual(self.user.vcs[0]["name"], "MembershipCredential")

    def test_import_credential_view(self):
        """Test that users can import credentials with custom names."""
        response = self.client.post(
            reverse("import_credential"),
            {
                "vc_name": "Imported Professional Credential",
                "vc_json": json.dumps(self.sample_vc),
            },
        )

        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse("vc_management"))

        # Check that the VC was added to the user with correct metadata
        self.user.refresh_from_db()
        self.assertEqual(len(self.user.vcs), 1)
        self.assertEqual(self.user.vcs[0]["name"], "Imported Professional Credential")
        self.assertEqual(self.user.vcs[0]["credential"], self.sample_vc)
        self.assertIn("added_date", self.user.vcs[0])

    def test_import_credential_without_name(self):
        """Test that imported credentials without names get auto-generated names."""
        response = self.client.post(
            reverse("import_credential"),
            {
                "vc_name": "",
                "vc_json": json.dumps(self.sample_vc),
            },
        )

        self.assertEqual(response.status_code, 302)
        self.user.refresh_from_db()
        self.assertEqual(len(self.user.vcs), 1)
        # Should generate a name based on the credential type
        self.assertEqual(self.user.vcs[0]["name"], "TestCredential")

    def test_import_credential_invalid_json(self):
        """Test that invalid JSON is properly rejected."""
        response = self.client.post(
            reverse("import_credential"),
            {
                "vc_name": "Invalid Credential",
                "vc_json": "invalid json",
            },
        )

        self.assertEqual(response.status_code, 302)
        self.user.refresh_from_db()
        self.assertEqual(len(self.user.vcs), 0)

        # Follow the redirect to check for error message
        response = self.client.get(response.url)
        self.assertContains(response, "Invalid JSON format")

    def test_import_credential_missing_required_fields(self):
        """Test that credentials missing required fields are rejected."""
        # Test with missing @context
        invalid_vc = self.sample_vc.copy()
        del invalid_vc["@context"]

        response = self.client.post(
            reverse("import_credential"),
            {
                "vc_name": "Invalid Credential",
                "vc_json": json.dumps(invalid_vc),
            },
        )

        self.assertEqual(response.status_code, 302)
        self.user.refresh_from_db()
        self.assertEqual(len(self.user.vcs), 0)

        # Follow the redirect to check for error message
        response = self.client.get(response.url)
        self.assertContains(response, "Credential must have an @context field")

    def test_vc_format_migration(self):
        """Test that old format VCs are properly migrated to new format."""
        # Add a VC in old format (direct VC without metadata)
        self.user.vcs = [self.sample_vc]
        self.user.save()

        # Access the VC management page to trigger migration
        response = self.client.get(reverse("vc_management"))
        self.assertEqual(response.status_code, 200)

        # Check that the VC was migrated to new format
        self.user.refresh_from_db()
        self.assertEqual(len(self.user.vcs), 1)
        self.assertIn("credential", self.user.vcs[0])
        self.assertIn("name", self.user.vcs[0])
        self.assertIn("added_date", self.user.vcs[0])
        self.assertEqual(self.user.vcs[0]["credential"], self.sample_vc)
        # Should generate a name based on the credential type
        self.assertEqual(self.user.vcs[0]["name"], "TestCredential")

    def test_get_authentication_vc(self):
        """Test that authentication VC can be retrieved correctly."""
        # Add authentication VC in new format
        self.user.vcs = [{"credential": self.auth_vc, "name": "Auth VC"}]
        self.user.save()

        auth_vc = self.user.get_authentication_vc()
        self.assertEqual(auth_vc, self.auth_vc)

    def test_get_other_vcs(self):
        """Test that non-authentication VCs can be retrieved correctly."""
        # Add both authentication and regular VCs
        self.user.vcs = [
            {"credential": self.auth_vc, "name": "Auth VC"},
            {"credential": self.sample_vc, "name": "Test VC"},
        ]
        self.user.save()

        other_vcs = self.user.get_other_vcs()
        self.assertEqual(len(other_vcs), 1)
        self.assertEqual(other_vcs[0]["name"], "Test VC")
        self.assertEqual(other_vcs[0]["credential"], self.sample_vc)

    def test_update_vc_name(self):
        """Test that VC names can be updated correctly."""
        # Add a VC
        self.user.vcs = [{"credential": self.sample_vc, "name": "Original Name"}]
        self.user.save()

        # Update the name
        response = self.client.post(
            reverse("update_vc_name"),
            json.dumps(
                {
                    "vc_id": self.sample_vc["credentialSubject"]["id"],
                    "name": "Updated Name",
                }
            ),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"success": True})

        # Check that the name was updated
        self.user.refresh_from_db()
        self.assertEqual(self.user.vcs[0]["name"], "Updated Name")

    def test_update_vc_name_invalid(self):
        """Test that invalid VC name updates are rejected."""

    @patch("apps.accounts.views.messages")
    def test_delete_credential_view(self, mock_messages):
        """Test that users can delete credentials."""
        # Add a VC to delete
        self.user.vcs = [create_vc_with_metadata(self.sample_vc, "Test VC")]
        self.user.save()

        response = self.client.post(
            reverse("delete_credential"),
            json.dumps({"vc_id": self.sample_vc["credentialSubject"]["id"]}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"success": True})

        # Check that the VC was deleted
        self.user.refresh_from_db()
        self.assertEqual(len(self.user.vcs), 0)

    def test_delete_credential_not_found(self):
        """Test that deleting a non-existent credential returns error."""
        response = self.client.post(
            reverse("delete_credential"),
            json.dumps({"vc_id": "did:key:nonexistent"}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json(), {"success": False, "error": "VC not found"})

    def test_delete_credential_invalid_json(self):
        """Test that invalid JSON is rejected."""
        response = self.client.post(
            reverse("delete_credential"),
            "invalid json",
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.json(), {"success": False, "error": "Invalid JSON data"}
        )

    def test_delete_credential_unauthenticated(self):
        """Test that unauthenticated users cannot delete credentials."""
        self.client.logout()

        response = self.client.post(
            reverse("delete_credential"),
            json.dumps({"vc_id": "did:key:test"}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 403)
        self.assertEqual(
            response.json(), {"success": False, "error": "Authentication required"}
        )
        # Add a VC
        self.user.vcs = [{"credential": self.sample_vc, "name": "Original Name"}]
        self.user.save()

        # Try to update with empty name
        response = self.client.post(
            reverse("update_vc_name"),
            json.dumps(
                {
                    "vc_id": self.sample_vc["credentialSubject"]["id"],
                    "name": "",
                }
            ),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 403)
        self.assertEqual(
            response.json(), {"success": False, "error": "Authentication required"}
        )

        # Check that the name was not updated
        self.user.refresh_from_db()
        self.assertEqual(self.user.vcs[0]["name"], "Original Name")

    @patch("apps.accounts.views.generate_did")
    @patch("apps.accounts.views.issue_vc")
    def test_generate_did_and_vc_view(self, mock_issue_vc, mock_generate_did):
        """Test that DID and VC generation works correctly."""
        # Setup mocks
        mock_generate_did.return_value = "did:key:z6Mkgenerated123"
        mock_issue_vc.return_value = json.dumps(self.auth_vc)

        # Create a user without DID
        user_without_did = create_test_user(
            username="newuser",
            password="newpass123",
            did=None,
            did_key=None,
        )
        login_test_user(self.client, "newuser", "newpass123")

        response = self.client.get(reverse("generate_did_and_vc"))

        self.assertEqual(response.status_code, 200)
        user_without_did.refresh_from_db()
        self.assertIsNotNone(user_without_did.did)
        self.assertIsNotNone(user_without_did.get_authentication_vc())

    def test_vc_management_template_context(self):
        """Test that the VC management template receives correct context."""
        # Add some VCs
        self.user.vcs = [
            {"credential": self.auth_vc, "name": "Auth VC"},
            {"credential": self.sample_vc, "name": "Test VC"},
        ]
        self.user.save()

        response = self.client.get(reverse("vc_management"))

        self.assertEqual(response.status_code, 200)
        self.assertIn("auth_vc", response.context)
        self.assertIn("vcs", response.context)
        self.assertEqual(response.context["auth_vc"], self.auth_vc)
        self.assertEqual(len(response.context["vcs"]), 1)
        self.assertEqual(response.context["vcs"][0]["name"], "Test VC")


class VCModelMethodTests(TestCase):
    """Tests for User model VC-related methods."""

    def test_delete_vc_from_list(self):
        """Test that VCs can be properly removed from the user's VC list."""
        # Add multiple VCs
        vc1 = create_test_vc(self.user, "Type1")
        vc2 = create_test_vc(self.user, "Type2")
        vc2["credentialSubject"]["id"] = "did:key:different_id"

        self.user.vcs = [
            create_vc_with_metadata(vc1, "VC1"),
            create_vc_with_metadata(vc2, "VC2"),
        ]
        self.user.save()

        # Remove one VC
        vcs = self.user.vcs.copy()
        vcs.pop(0)  # Remove first VC
        self.user.vcs = vcs
        self.user.save()

        self.user.refresh_from_db()
        self.assertEqual(len(self.user.vcs), 1)
        self.assertEqual(self.user.vcs[0]["name"], "VC2")

    def setUp(self):
        """Set up test data for model method tests."""
        self.user = create_test_user(username="modeltestuser")
        self.sample_vc = create_test_vc(self.user, "TestCredential")

    def test_add_vc_with_name(self):
        """Test adding a VC with a custom name."""
        self.user.add_vc(self.sample_vc, "Custom Name")

        self.assertEqual(len(self.user.vcs), 1)
        self.assertEqual(self.user.vcs[0]["name"], "Custom Name")
        self.assertEqual(self.user.vcs[0]["credential"], self.sample_vc)
        self.assertIn("added_date", self.user.vcs[0])

    def test_add_vc_without_name(self):
        """Test adding a VC without a custom name (auto-generates name)."""
        self.user.add_vc(self.sample_vc)

        self.assertEqual(len(self.user.vcs), 1)
        self.assertEqual(self.user.vcs[0]["name"], "TestCredential")
        self.assertEqual(self.user.vcs[0]["credential"], self.sample_vc)

    def test_add_vc_existing_id(self):
        """Test adding a VC with an existing credentialSubject.id updates the VC."""
        # Add VC first time
        self.user.add_vc(self.sample_vc, "Original Name")

        # Modify the VC and add again
        updated_vc = self.sample_vc.copy()
        updated_vc["updated"] = True

        self.user.add_vc(updated_vc, "Updated Name")

        # Should have only one VC (updated)
        self.assertEqual(len(self.user.vcs), 1)
        self.assertEqual(self.user.vcs[0]["name"], "Updated Name")
        self.assertTrue(self.user.vcs[0]["credential"]["updated"])

    def test_get_vcs_by_type(self):
        """Test filtering VCs by type."""
        # Add VCs of different types
        vc1 = create_test_vc(self.user, "Type1")
        vc2 = create_test_vc(self.user, "Type2")
        vc2["credentialSubject"]["id"] = "did:key:different_id"

        self.user.vcs = [
            create_vc_with_metadata(vc1, "VC1"),
            create_vc_with_metadata(vc2, "VC2"),
        ]
        self.user.save()

        # Get VCs by type
        type1_vcs = self.user.get_vcs_by_type("Type1")
        type2_vcs = self.user.get_vcs_by_type("Type2")
        all_vcs = self.user.get_vcs_by_type("VerifiableCredential")

        self.assertEqual(len(type1_vcs), 1)
        self.assertEqual(len(type2_vcs), 1)
        self.assertEqual(len(all_vcs), 2)

    def test_ensure_vcs_migrated(self):
        """Test that ensure_vcs_migrated properly migrates old format VCs."""
        # Add VCs in old format
        self.user.vcs = [self.sample_vc]
        self.user.save()

        # Call ensure_vcs_migrated
        self.user.ensure_vcs_migrated()

        # Check that VCs were migrated
        self.user.refresh_from_db()
        self.assertEqual(len(self.user.vcs), 1)
        self.assertIn("credential", self.user.vcs[0])
        self.assertIn("name", self.user.vcs[0])
        self.assertIn("added_date", self.user.vcs[0])
        self.assertEqual(self.user.vcs[0]["credential"], self.sample_vc)
