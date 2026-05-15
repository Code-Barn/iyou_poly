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
