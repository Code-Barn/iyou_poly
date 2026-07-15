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

"""
Session-backed PKCE mechanics for OIDC authentication.

Bypasses mozilla-django-oidc configuration requirements by implementing
PKCE code challenge/verification directly, with safe defaults for all
configuration variables.
"""

import base64
import hashlib
import logging
import secrets
import time
from urllib.parse import urlencode

import environ
import jwt
import requests
from django.conf import settings
from django.contrib import auth
from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.utils.crypto import get_random_string
from django.views.generic import View
from mozilla_django_oidc.views import OIDCAuthenticationCallbackView

logger = logging.getLogger(__name__)
User = get_user_model()
env = environ.Env()


class PKCEOIDCAuthenticationRequestView(View):
    """OIDC authentication request with session-backed PKCE code verifier.

    Generates a code_verifier via secrets.token_urlsafe(64), derives the
    code_challenge as Base64URL(SHA256(utf-8(verifier))) with trailing '='
    stripped, and stores the verifier in request.session['pkce_code_verifier']
    for retrieval during the callback exchange.
    """

    http_method_names = ["get"]

    def get(self, request):
        state = get_random_string(32)

        code_verifier = secrets.token_urlsafe(64)
        code_challenge = (
            base64.urlsafe_b64encode(
                hashlib.sha256(code_verifier.encode("utf-8")).digest()
            )
            .rstrip(b"=")
            .decode("ascii")
        )

        request.session["pkce_code_verifier"] = code_verifier

        nonce = get_random_string(32)

        params = {
            "response_type": "code",
            "scope": getattr(settings, "OIDC_RP_SCOPES", "openid email"),
            "client_id": getattr(settings, "OIDC_RP_CLIENT_ID", ""),
            "redirect_uri": request.build_absolute_uri(
                reverse("oidc_authentication_callback")
            ),
            "state": state,
            "code_challenge": code_challenge,
            "code_challenge_method": "S256",
            "nonce": nonce,
        }

        if "oidc_states" not in request.session or not isinstance(
            request.session["oidc_states"], dict
        ):
            request.session["oidc_states"] = {}

        request.session["oidc_states"][state] = {
            "code_verifier": code_verifier,
            "nonce": nonce,
            "added_on": time.time(),
        }

        redirect_url = "{url}?{query}".format(
            url=settings.OIDC_OP_AUTHORIZATION_ENDPOINT,
            query=urlencode(params),
        )
        return HttpResponseRedirect(redirect_url)


class PKCEOIDCAuthenticationCallbackView(OIDCAuthenticationCallbackView):
    """OIDC callback that performs back-channel token exchange with PKCE verifier.

    Inherits standardised OIDC lifecycle from mozilla-django-oidc and injects
    the PKCE code_verifier into backend kwargs via get_backend_kwargs().
    """

    def get_backend_kwargs(self, request):
        kwargs = {
            "request": request,
        }
        code_verifier = request.session.pop("pkce_code_verifier", None)
        if code_verifier:
            kwargs["code_verifier"] = code_verifier
        return kwargs

    def get(self, request):
        if request.GET.get("error"):
            if (
                "state" in request.GET
                and "oidc_states" in request.session
                and request.GET["state"] in request.session["oidc_states"]
            ):
                del request.session["oidc_states"][request.GET["state"]]
                request.session.save()

            if request.user.is_authenticated:
                auth.logout(request)
            return self.login_failure()

        if "code" not in request.GET or "state" not in request.GET:
            return self.login_failure()

        if "oidc_states" not in request.session:
            return self.login_failure()

        state = request.GET["state"]
        if state not in request.session["oidc_states"]:
            return self.login_failure()

        nonce = request.session["oidc_states"][state]["nonce"]
        del request.session["oidc_states"][state]
        request.session.save()

        request.session = request.session.__class__(request.session.session_key)

        kwargs = self.get_backend_kwargs(request)
        kwargs["nonce"] = nonce

        self.user = auth.authenticate(**kwargs)
        if self.user and self.user.is_active:
            return self.login_success()

        return self.login_failure()


class PKCEAuthenticationBackend(ModelBackend):
    """OIDC backend that avoids library initialization constraints.

    Configuration variables default to an empty string safely unless an
    explicit key override is discovered in settings or the environment.
    """

    def __init__(self, *args, **kwargs):
        self.OIDC_OP_TOKEN_ENDPOINT = getattr(settings, "OIDC_OP_TOKEN_ENDPOINT", "")
        self.OIDC_OP_USER_ENDPOINT = getattr(settings, "OIDC_OP_USER_ENDPOINT", "")
        self.OIDC_OP_JWKS_ENDPOINT = getattr(settings, "OIDC_OP_JWKS_ENDPOINT", None)
        self.OIDC_RP_CLIENT_ID = getattr(settings, "OIDC_RP_CLIENT_ID", "")
        self.OIDC_RP_CLIENT_SECRET = getattr(settings, "OIDC_RP_CLIENT_SECRET", "")
        self.OIDC_RP_SIGN_ALGO = getattr(settings, "OIDC_RP_SIGN_ALGO", "RS256")
        self.OIDC_RP_IDP_SIGN_KEY = getattr(settings, "OIDC_RP_IDP_SIGN_KEY", None)
        self.UserModel = get_user_model()

    def authenticate(self, request, **kwargs):
        claims = kwargs.get("claims")

        if not claims and request is not None:
            claims = request.session.get("oidc_claims")

        code_verifier = kwargs.get("code_verifier")
        if not claims and code_verifier and request is not None:
            claims = self._exchange_code_for_claims(request, code_verifier)

        if not claims:
            id_token_str = kwargs.get("token")
            if id_token_str and request is not None:
                nonce = request.session.get("oidc_pending_nonce", "")
                try:
                    claims = self._decode_id_token(id_token_str, nonce)
                except Exception as e:
                    logger.error(f"Token decode fallback failed: {e}")
                    return None

        if not claims:
            return None

        if not self.verify_claims(claims):
            logger.warning("Claims verification failed — missing 'sub'")
            return None

        users = self.filter_users_by_claims(claims)
        if len(users) == 1:
            return self.update_user(users[0], claims)
        elif len(users) > 1:
            logger.warning("Multiple users returned for claims")
            return None
        elif getattr(settings, "OIDC_CREATE_USER", True):
            return self.create_user(claims)
        return None

    def _exchange_code_for_claims(self, request, code_verifier):
        code = request.GET.get("code")
        if not code:
            logger.error("No authorization code in request")
            return None

        state = request.GET.get("state", "")
        nonce = ""
        if "oidc_states" in request.session and state in request.session["oidc_states"]:
            nonce = request.session["oidc_states"][state].get("nonce", "")

        redirect_uri = request.build_absolute_uri(
            reverse("oidc_authentication_callback")
        )

        token_payload = {
            "client_id": getattr(settings, "OIDC_RP_CLIENT_ID", ""),
            "client_secret": getattr(settings, "OIDC_RP_CLIENT_SECRET", ""),
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": redirect_uri,
        }
        if code_verifier:
            token_payload["code_verifier"] = code_verifier

        try:
            token_response = requests.post(
                settings.OIDC_OP_TOKEN_ENDPOINT,
                data=token_payload,
                verify=getattr(settings, "OIDC_VERIFY_SSL", True),
                timeout=getattr(settings, "OIDC_TIMEOUT", None),
            )
            token_response.raise_for_status()
            token_info = token_response.json()
        except Exception as e:
            logger.error(f"OIDC token exchange failed: {e}")
            return None

        id_token_str = token_info.get("id_token")
        if not id_token_str:
            logger.error("No id_token in token response")
            return None

        try:
            claims = self._decode_id_token(id_token_str, nonce)
        except Exception as e:
            logger.error(f"ID token verification failed: {e}")
            return None

        request.session["oidc_claims"] = claims
        request.session.save()
        return claims

    def _decode_id_token(self, id_token_str, nonce):
        unverified_header = jwt.get_unverified_header(id_token_str)
        alg = unverified_header.get("alg", "RS256")

        idp_sign_key = getattr(settings, "OIDC_RP_IDP_SIGN_KEY", None)
        jwks_endpoint = getattr(settings, "OIDC_OP_JWKS_ENDPOINT", None)

        if idp_sign_key:
            key = idp_sign_key
        elif jwks_endpoint:
            key = self._retrieve_jwks_key(id_token_str, jwks_endpoint)
        else:
            key = getattr(settings, "OIDC_RP_CLIENT_SECRET", "")

        options = {"verify_aud": False}
        if alg == "none":
            options["verify_signature"] = False

        payload = jwt.decode(id_token_str, key, algorithms=[alg], options=options)

        if getattr(settings, "OIDC_USE_NONCE", True) and nonce and nonce != payload.get("nonce"):
            raise ValueError("Nonce verification failed")

        return payload

    def _retrieve_jwks_key(self, token, jwks_endpoint):
        response = requests.get(
            jwks_endpoint,
            verify=getattr(settings, "OIDC_VERIFY_SSL", True),
            timeout=getattr(settings, "OIDC_TIMEOUT", None),
        )
        response.raise_for_status()
        jwks = response.json()

        jws = jwt.get_unverified_header(token)
        verify_kid = getattr(settings, "OIDC_VERIFY_KID", True)

        for jwk in jwks.get("keys", []):
            if verify_kid and jwk.get("kid") != jws.get("kid"):
                continue
            if "alg" in jwk and jwk["alg"] != jws.get("alg"):
                continue
            return jwt.PyJWK(jwk)

        raise ValueError("No matching JWK found")

    def filter_users_by_claims(self, claims):
        did = claims.get("sub")
        if not did:
            logger.error("No 'sub' claim found in OIDC token")
            return self.UserModel.objects.none()
        user, created = self.UserModel.objects.get_or_create(username=did)
        if created:
            user.set_unusable_password()
            user.is_active = True
            user.save()
            logger.info(f"Auto-created sovereign user via PKCE: {user.username}")
        else:
            logger.info(f"Mapped to existing user: {user.username}")
        self._evaluate_admin_elevation(user)
        return self.UserModel.objects.filter(id=user.id)

    def create_user(self, claims):
        user = self.UserModel.objects.create_user(username=claims.get("sub"))
        user.is_active = True
        user.set_unusable_password()
        user.save()
        logger.info(f"Created sovereign user: {user.username}")
        return self._evaluate_admin_elevation(user)

    def verify_claims(self, claims):
        return "sub" in claims

    def update_user(self, user, claims):
        return user

    def get_user(self, user_id):
        try:
            return self.UserModel.objects.get(pk=user_id)
        except self.UserModel.DoesNotExist:
            return None

    def _evaluate_admin_elevation(self, user):
        if not user or user.is_anonymous:
            return user
        master_admin_did = env.str("ADMIN_DID", default="")
        if master_admin_did and user.username == master_admin_did:
            dirty = False
            if not user.is_staff:
                user.is_staff = True
                dirty = True
            if not user.is_superuser:
                user.is_superuser = True
                dirty = True
            if dirty:
                user.save()
                logger.info(f"Admin elevation granted: {user.username}")
        return user
