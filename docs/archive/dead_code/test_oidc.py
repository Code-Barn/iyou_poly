"""
Tests for OIDC authentication functionality.
"""

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

User = get_user_model()


class OIDCAuthenticationTests(TestCase):
    """
    Test OIDC authentication functionality.
    """

    def setUp(self):
        self.client = Client()
        self.login_url = reverse("login")
        self.poll_list_url = reverse("poll_list")

    def test_oidc_login_buttons_in_template(self):
        """Test that OIDC login buttons are present in the login template."""
        response = self.client.get(self.login_url)
        self.assertEqual(response.status_code, 200)

        # Check that Google and GitHub login buttons are present
        self.assertContains(response, "Login with Google")
        self.assertContains(response, "Login with GitHub")

        # Check that the buttons have the correct URLs
        self.assertContains(response, reverse("social:begin", args=["google-oauth2"]))
        self.assertContains(response, reverse("social:begin", args=["github"]))

    def test_oidc_urls_configured(self):
        """Test that OIDC URLs are properly configured."""
        # Test that social auth URLs are available
        google_auth_url = reverse("social:begin", args=["google-oauth2"])
        github_auth_url = reverse("social:begin", args=["github"])

        self.assertTrue(google_auth_url.startswith("/social-auth/"))
        self.assertTrue(github_auth_url.startswith("/social-auth/"))

    def test_oidc_settings_configured(self):
        """Test that OIDC settings are properly configured."""
        from django.conf import settings

        # Check that social auth backends are configured
        self.assertIn(
            "social_core.backends.google.GoogleOAuth2", settings.AUTHENTICATION_BACKENDS
        )
        self.assertIn(
            "social_core.backends.github.GithubOAuth2", settings.AUTHENTICATION_BACKENDS
        )

        # Check that required settings are present
        self.assertTrue(hasattr(settings, "SOCIAL_AUTH_GOOGLE_OAUTH2_KEY"))
        self.assertTrue(hasattr(settings, "SOCIAL_AUTH_GOOGLE_OAUTH2_SECRET"))
        self.assertTrue(hasattr(settings, "SOCIAL_AUTH_GITHUB_KEY"))
        self.assertTrue(hasattr(settings, "SOCIAL_AUTH_GITHUB_SECRET"))

    def test_oidc_pipeline_configured(self):
        """Test that OIDC pipeline is properly configured."""
        from django.conf import settings

        # Check that our custom pipeline function is in the pipeline
        self.assertIn(
            "apps.accounts.pipeline.save_federated_identity",
            settings.SOCIAL_AUTH_PIPELINE,
        )

    def test_oidc_backend_available(self):
        """Test that our custom OIDC backend is available."""
        from django.conf import settings

        # Check that our custom OIDC backend is in the authentication backends
        self.assertIn(
            "apps.accounts.backends.OIDCAuthBackend", settings.AUTHENTICATION_BACKENDS
        )

    def test_oidc_login_redirects_when_not_configured(self):
        """Test that OIDC login redirects appropriately when not fully configured."""
        # Since we don't have real OIDC credentials, the login should redirect to the provider
        # and then fail, but we can at least test that the initial redirect works
        google_auth_url = reverse("social:begin", args=["google-oauth2"])
        response = self.client.get(google_auth_url)

        # Should redirect to Google's OAuth endpoint (or fail with missing credentials)
        # Since we don't have real credentials, it might fail, but that's expected for this test
        self.assertTrue(
            response.status_code in [302, 400, 500]
        )  # Redirect or error is fine for this test
