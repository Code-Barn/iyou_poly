import json

from django.test import TestCase, override_settings
from django.urls import reverse

from apps.accounts.models import User
from apps.accounts.tests.utils import (
    create_test_user,
    create_test_vc,
    create_vc_with_metadata,
)

_no_session_refresh = override_settings(
    MIDDLEWARE=[
        "debug_toolbar.middleware.DebugToolbarMiddleware",
        "django.middleware.security.SecurityMiddleware",
        "django.contrib.sessions.middleware.SessionMiddleware",
        "django.middleware.common.CommonMiddleware",
        "django.middleware.csrf.CsrfViewMiddleware",
        "django.contrib.auth.middleware.AuthenticationMiddleware",
        "django.contrib.messages.middleware.MessageMiddleware",
        "django.middleware.clickjacking.XFrameOptionsMiddleware",
    ]
)


@_no_session_refresh
class VCManagementViewTests(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser", password="testpass123"
        )
        self.client.force_login(self.user)

        self.sample_vc = {
            "@context": ["https://www.w3.org/2018/credentials/v1"],
            "type": ["VerifiableCredential", "TestCredential"],
            "issuer": self.user.username,
            "issuanceDate": "2023-01-01T00:00:00Z",
            "credentialSubject": {
                "id": self.user.username,
                "name": self.user.username,
                "description": "Test credential",
            },
        }

        self.auth_vc = {
            "@context": ["https://www.w3.org/2018/credentials/v1"],
            "type": ["VerifiableCredential", "AuthenticationCredential"],
            "issuer": self.user.username,
            "issuanceDate": "2023-01-01T00:00:00Z",
            "credentialSubject": {
                "id": self.user.username,
                "name": self.user.username,
            },
        }

    def test_vc_management_view_authenticated(self):
        response = self.client.get(reverse("vc_management"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Verifiable Credentials")

    def test_vc_management_view_unauthenticated(self):
        self.client.logout()
        response = self.client.get(reverse("vc_management"))
        self.assertEqual(response.status_code, 302)
        self.assertIn("/login/", response.url)

    def test_generate_credential_view_returns_unsigned_json(self):
        response = self.client.post(
            reverse("generate_credential"),
            {
                "credential_name": "Professional Certification",
                "credential_type": "ProfessionalCredential",
                "scope_value": "",
            },
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("unsigned_credential", data)
        self.assertEqual(data["credential_name"], "Professional Certification")
        self.assertEqual(data["credential_type"], "ProfessionalCredential")

    def test_generate_credential_without_name_uses_type(self):
        response = self.client.post(
            reverse("generate_credential"),
            {
                "credential_name": "",
                "credential_type": "MembershipCredential",
                "scope_value": "",
            },
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["credential_name"], "MembershipCredential")

    def test_import_credential_view(self):
        response = self.client.post(
            reverse("import_credential"),
            {
                "vc_name": "Imported Professional Credential",
                "vc_json": json.dumps(self.sample_vc),
            },
        )
        self.assertRedirects(response, reverse("vc_management"))
        self.user.refresh_from_db()
        self.assertEqual(len(self.user.vcs), 1)
        self.assertEqual(self.user.vcs[0]["name"], "Imported Professional Credential")

    def test_import_credential_without_name(self):
        response = self.client.post(
            reverse("import_credential"),
            {
                "vc_name": "",
                "vc_json": json.dumps(self.sample_vc),
            },
        )
        self.assertRedirects(response, reverse("vc_management"))
        self.user.refresh_from_db()
        self.assertEqual(len(self.user.vcs), 1)
        self.assertEqual(self.user.vcs[0]["name"], "TestCredential")

    def test_import_credential_invalid_json(self):
        response = self.client.post(
            reverse("import_credential"),
            {
                "vc_name": "Invalid Credential",
                "vc_json": "invalid json",
            },
        )
        self.assertRedirects(response, reverse("import_credential"))
        self.user.refresh_from_db()
        self.assertEqual(len(self.user.vcs), 0)

    def test_import_credential_missing_required_fields(self):
        invalid_vc = self.sample_vc.copy()
        del invalid_vc["@context"]
        response = self.client.post(
            reverse("import_credential"),
            {
                "vc_name": "Invalid Credential",
                "vc_json": json.dumps(invalid_vc),
            },
        )
        self.assertRedirects(response, reverse("import_credential"))
        self.user.refresh_from_db()
        self.assertEqual(len(self.user.vcs), 0)

    def test_vc_format_migration(self):
        self.user.vcs = [self.sample_vc]
        self.user.save()
        response = self.client.get(reverse("vc_management"))
        self.assertEqual(response.status_code, 200)
        self.user.refresh_from_db()
        self.assertEqual(len(self.user.vcs), 1)
        self.assertIn("credential", self.user.vcs[0])
        self.assertIn("name", self.user.vcs[0])
        self.assertIn("added_date", self.user.vcs[0])

    def test_store_signed_credential(self):
        response = self.client.post(
            reverse("store_signed_credential"),
            json.dumps({
                "signed_credential": self.sample_vc,
                "credential_name": "Signed Test VC",
            }),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"success": True})
        self.user.refresh_from_db()
        self.assertEqual(len(self.user.vcs), 1)
        self.assertEqual(self.user.vcs[0]["name"], "Signed Test VC")

    def test_store_signed_credential_unauthenticated(self):
        self.client.logout()
        response = self.client.post(
            reverse("store_signed_credential"),
            json.dumps({"signed_credential": self.sample_vc}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 403)

    def test_vc_management_template_context(self):
        self.user.vcs = [
            {"credential": self.auth_vc, "name": "Auth VC"},
            {"credential": self.sample_vc, "name": "Test VC"},
        ]
        self.user.save()
        response = self.client.get(reverse("vc_management"))
        self.assertEqual(response.status_code, 200)
        self.assertIn("auth_vc", response.context)
        self.assertIn("vcs", response.context)
        self.assertEqual(len(response.context["vcs"]), 1)

    def test_get_authentication_vc(self):
        self.user.vcs = [{"credential": self.auth_vc, "name": "Auth VC"}]
        self.user.save()
        auth_vc = self.user.get_authentication_vc()
        self.assertEqual(auth_vc, self.auth_vc)

    def test_get_other_vcs(self):
        self.user.vcs = [
            {"credential": self.auth_vc, "name": "Auth VC"},
            {"credential": self.sample_vc, "name": "Test VC"},
        ]
        self.user.save()
        other_vcs = self.user.get_other_vcs()
        self.assertEqual(len(other_vcs), 1)
        self.assertEqual(other_vcs[0]["name"], "Test VC")


@_no_session_refresh
class VCManagementDeleteTests(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser", password="testpass123"
        )
        self.client.force_login(self.user)
        self.sample_vc = {
            "@context": ["https://www.w3.org/2018/credentials/v1"],
            "type": ["VerifiableCredential", "TestCredential"],
            "issuer": self.user.username,
            "issuanceDate": "2023-01-01T00:00:00Z",
            "credentialSubject": {
                "id": self.user.username,
                "name": self.user.username,
            },
        }

    def test_delete_credential_view(self):
        self.user.vcs = [create_vc_with_metadata(self.sample_vc, "Test VC")]
        self.user.save()
        response = self.client.post(
            reverse("delete_credential"),
            json.dumps({"vc_id": self.sample_vc["credentialSubject"]["id"]}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"success": True})
        self.user.refresh_from_db()
        self.assertEqual(len(self.user.vcs), 0)

    def test_delete_credential_not_found(self):
        response = self.client.post(
            reverse("delete_credential"),
            json.dumps({"vc_id": "nonexistent"}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 404)

    def test_delete_credential_invalid_json(self):
        response = self.client.post(
            reverse("delete_credential"),
            "invalid json",
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)

    def test_delete_credential_unauthenticated(self):
        self.client.logout()
        response = self.client.post(
            reverse("delete_credential"),
            json.dumps({"vc_id": "test"}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 403)


class VCModelMethodTests(TestCase):

    def setUp(self):
        self.user = create_test_user(username="modeltestuser")
        self.sample_vc = create_test_vc(self.user, "TestCredential")

    def test_add_vc_with_name(self):
        self.user.add_vc(self.sample_vc, "Custom Name")
        self.assertEqual(len(self.user.vcs), 1)
        self.assertEqual(self.user.vcs[0]["name"], "Custom Name")

    def test_add_vc_without_name(self):
        self.user.add_vc(self.sample_vc)
        self.assertEqual(len(self.user.vcs), 1)
        self.assertEqual(self.user.vcs[0]["name"], "TestCredential")

    def test_add_vc_existing_id(self):
        self.user.add_vc(self.sample_vc, "Original Name")
        updated_vc = self.sample_vc.copy()
        updated_vc["updated"] = True
        self.user.add_vc(updated_vc, "Updated Name")
        self.assertEqual(len(self.user.vcs), 1)
        self.assertEqual(self.user.vcs[0]["name"], "Updated Name")
        self.assertTrue(self.user.vcs[0]["credential"]["updated"])

    def test_get_vcs_by_type(self):
        vc1 = create_test_vc(self.user, "Type1")
        vc2 = create_test_vc(self.user, "Type2")
        vc2["credentialSubject"]["id"] = "different_id"
        self.user.vcs = [
            create_vc_with_metadata(vc1, "VC1"),
            create_vc_with_metadata(vc2, "VC2"),
        ]
        self.user.save()
        self.assertEqual(len(self.user.get_vcs_by_type("Type1")), 1)
        self.assertEqual(len(self.user.get_vcs_by_type("Type2")), 1)
        self.assertEqual(len(self.user.get_vcs_by_type("VerifiableCredential")), 2)

    def test_ensure_vcs_migrated(self):
        self.user.vcs = [self.sample_vc]
        self.user.save()
        self.user.ensure_vcs_migrated()
        self.user.refresh_from_db()
        self.assertEqual(len(self.user.vcs), 1)
        self.assertIn("credential", self.user.vcs[0])
        self.assertIn("name", self.user.vcs[0])
        self.assertIn("added_date", self.user.vcs[0])
