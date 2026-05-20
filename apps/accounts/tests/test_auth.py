# Copyright (C) 2026 David Byers dba Byers Brands
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

from django.test import TestCase
from django.urls import reverse

from apps.accounts.models import User


class OIDCLoginRedirectTests(TestCase):

    def test_login_url_redirects_to_oidc(self):
        response = self.client.get(reverse("login"))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("oidc_authentication_init"), response.url)

    def test_logout_url_redirects_to_oidc(self):
        response = self.client.get(reverse("logout"))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("oidc_logout"), response.url)

    def test_protected_view_redirects_unauthenticated(self):
        response = self.client.get(reverse("vc_management"))
        self.assertEqual(response.status_code, 302)
        self.assertIn("/login/", response.url)

    def test_no_password_login(self):
        User.objects.create_user(username="someuser", password="somepass")
        logged_in = self.client.login(username="someuser", password="somepass")
        self.assertFalse(logged_in)


class OIDCAuthBackendTests(TestCase):

    def test_backend_filter_users_by_claims_creates_new(self):
        from apps.accounts.backends import MyOIDCAuthenticationBackend

        backend = MyOIDCAuthenticationBackend()
        claims = {"sub": "oidc-user-123"}
        queryset = backend.filter_users_by_claims(claims)
        user = queryset.first()
        self.assertIsNotNone(user)
        self.assertEqual(user.username, "oidc-user-123")

    def test_backend_filter_users_by_claims_finds_existing(self):
        User.objects.create_user(username="existing-oidc-user")
        from apps.accounts.backends import MyOIDCAuthenticationBackend

        backend = MyOIDCAuthenticationBackend()
        claims = {"sub": "existing-oidc-user"}
        queryset = backend.filter_users_by_claims(claims)
        user = queryset.first()
        self.assertIsNotNone(user)
        self.assertEqual(user.username, "existing-oidc-user")
