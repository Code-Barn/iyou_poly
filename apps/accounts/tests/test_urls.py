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

from django.test import TestCase
from django.urls import reverse


class URLResolutionTests(TestCase):

    def test_all_named_urls_resolve(self):
        urls = {
            "oidc_authentication_init": "/oidc/authenticate/",
            "oidc_authentication_callback": "/oidc/callback/",
            "oidc_logout": "/oidc/logout/",
            "login": "/login/",
            "logout": "/logout/",
            "poll_list": "/",
            "vc_management": "/credentials/",
            "generate_credential": "/credentials/generate/",
            "store_signed_credential": "/credentials/store-signed/",
            "delete_credential": "/credentials/delete/",
            "import_credential": "/credentials/import/",
        }
        for name, expected_path in urls.items():
            with self.subTest(url_name=name):
                resolved = reverse(name)
                self.assertEqual(resolved, expected_path)
