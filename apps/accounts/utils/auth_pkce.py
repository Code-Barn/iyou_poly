"""
Session-backed PKCE mechanics for OIDC authentication.

Eliminates OIDC_RP_CLIENT_SECRET by replacing it with ephemeral,
per-request code verifiers per RFC 7636. The verifier lives in the
encrypted session cookie for the duration of the OAuth flow and is
consumed exactly once on callback.

Drop-in for mozilla_django_oidc 5.x — no library settings required
beyond the standard OIDC_RP_CLIENT_ID / endpoint URLs.

Requirements (settings.py):
    SESSION_ENGINE = "django.contrib.sessions.backends.signed_cookies"
    OIDC_RP_CLIENT_ID = "<your-app-client-id>"
    OIDC_RP_SCOPES = "openid profile email"
    OIDC_OP_AUTHORIZATION_ENDPOINT = "https://iyou.me/openid/authorize/"
    OIDC_OP_TOKEN_ENDPOINT        = "https://iyou.me/openid/token/"
    OIDC_OP_USER_ENDPOINT         = "https://iyou.me/openid/userinfo/"
    OIDC_AUTHENTICATION_CALLBACK_URL = "oidc_authentication_callback"
    LOGIN_REDIRECT_URL            = "/"
    LOGIN_REDIRECT_URL_FAILURE    = "/"
    ADMIN_DID = env.str("ADMIN_DID", default="")
"""

from __future__ import annotations

import hashlib
import logging
import secrets
from base64 import urlsafe_b64encode
from urllib.parse import urlencode

import requests
from django.contrib.auth import get_user_model
from django.contrib.auth.backends import BaseBackend
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.utils.crypto import get_random_string
from mozilla_django_oidc.utils import (
    absolutify,
    add_state_and_verifier_and_nonce_to_session,
)
from mozilla_django_oidc.views import (
    OIDCAuthenticationCallbackView,
    OIDCAuthenticationRequestView,
)

logger = logging.getLogger(__name__)

# Session key constants
SESSION_KEY_CODE_VERIFIER = "pkce_code_verifier"
SESSION_KEY_OIDC_LOGIN_NEXT = "oidc_login_next"


def _generate_code_verifier(length: int = 64) -> str:
    """Return a cryptographically secure, URL-safe random string."""
    if not (43 <= length <= 128):
        raise ValueError(
            f"code_verifier length must be between 43 and 128, got {length}"
        )
    return secrets.token_urlsafe(length)


def _compute_code_challenge(verifier: str) -> str:
    """BASE64URL(SHA256(verifier)) — RFC 7636 section 4.1, S256 method."""
    hash_bytes = hashlib.sha256(verifier.encode("utf-8")).digest()
    challenge = urlsafe_b64encode(hash_bytes).decode("utf-8")
    return challenge.rstrip("=")


def _evaluate_sovereign_admin_posture(user):
    """AUTH_FLOW_SPECIFICATION.md section 6.2 — Canonical admin elevation.

    Elevation only — no demotion. Idempotent: safe to call on every auth ingress.
    """
    from django.conf import settings

    target_admin_did = getattr(settings, "ADMIN_DID", None)
    if not target_admin_did:
        return user

    if user.username != target_admin_did:
        return user

    dirty = False
    if not user.is_staff:
        user.is_staff = True
        dirty = True
    if not user.is_superuser:
        user.is_superuser = True
        dirty = True
    if user.has_usable_password():
        user.set_unusable_password()
        dirty = True

    if dirty:
        user.save(update_fields=["is_staff", "is_superuser", "password"])
        logger.info("Admin elevation granted: %s", user.username)

    return user


# ---------------------------------------------------------------------------
# Authorization Request — RP -> iyou_idp
# ---------------------------------------------------------------------------

class PKCEOIDCAuthenticationRequestView(OIDCAuthenticationRequestView):
    """Generate a PKCE code_verifier, compute its S256 code_challenge,
    and redirect the user-agent to iyou_idp with both injected into the
    authorization request parameters.

    The verifier is persisted in request.session['pkce_code_verifier']
    so it survives the round-trip through the OP without server-side state.
    """

    http_method_names = ["get"]

    def get(self, request):
        try:
            state = get_random_string(
                self.get_settings("OIDC_STATE_SIZE", 32)
            )
            redirect_field_name = self.get_settings(
                "OIDC_REDIRECT_FIELD_NAME", "next"
            )
            reverse_url = self.get_settings(
                "OIDC_AUTHENTICATION_CALLBACK_URL",
                "oidc_authentication_callback",
            )

            code_verifier = _generate_code_verifier(
                self.get_settings("OIDC_PKCE_CODE_VERIFIER_SIZE", 64)
            )
            code_challenge = _compute_code_challenge(code_verifier)

            request.session[SESSION_KEY_CODE_VERIFIER] = code_verifier

            params = {
                "response_type": "code",
                "scope": self.get_settings("OIDC_RP_SCOPES", "openid profile email"),
                "client_id": self.OIDC_RP_CLIENT_ID,
                "redirect_uri": absolutify(request, reverse(reverse_url)),
                "state": state,
                "code_challenge": code_challenge,
                "code_challenge_method": "S256",
            }

            params.update(self.get_extra_params(request))

            if self.get_settings("OIDC_USE_NONCE", True):
                nonce = get_random_string(
                    self.get_settings("OIDC_NONCE_SIZE", 32)
                )
                params["nonce"] = nonce

            add_state_and_verifier_and_nonce_to_session(
                request, state, params, code_verifier=None
            )

            next_url = request.GET.get(redirect_field_name, "/")
            request.session[SESSION_KEY_OIDC_LOGIN_NEXT] = next_url
            request.session.save()

            query = urlencode(params)
            redirect_url = f"{self.OIDC_OP_AUTH_ENDPOINT}?{query}"
            return HttpResponseRedirect(redirect_url)

        except Exception:
            logger.exception("PKCE auth request failed")
            return HttpResponseRedirect(
                self.get_settings("LOGIN_REDIRECT_URL_FAILURE", "/")
            )


# ---------------------------------------------------------------------------
# Authorization Callback — iyou_idp -> RP
# ---------------------------------------------------------------------------

class PKCEOIDCAuthenticationCallbackView(OIDCAuthenticationCallbackView):
    """Handle the authorization code callback from iyou_idp.

    Rule 3: Override get_backend_kwargs(), NOT get().
    The parent get() calls this hook internally and passes the returned
    dict as keyword arguments to auth.authenticate().
    """

    def get_backend_kwargs(self, request):
        kwargs = super().get_backend_kwargs(request)

        code_verifier = request.session.pop(SESSION_KEY_CODE_VERIFIER, None)

        if code_verifier is None:
            logger.warning(
                "No pkce_code_verifier in session — possible replay, "
                "cookie rotation failure, or direct callback access"
            )

        kwargs.update({"code_verifier": code_verifier})
        return kwargs


# ---------------------------------------------------------------------------
# Authentication Backend — PKCE-only, no client_secret required
# ---------------------------------------------------------------------------

class PKCEAuthenticationBackend(BaseBackend):
    """Authenticate via iyou_idp using an authorization code + PKCE
    code_verifier.

    Inherits from django.contrib.auth.Backend to avoid OIDCAuthenticationBackend's
    __init__ which enforces OIDC_RP_CLIENT_SECRET presence (Rule 2).

    User lookup filters strictly on username=claims.get('sub') (Rule 4).
    """

    def authenticate(self, request, code_verifier=None, nonce=None, **kwargs):
        if not request:
            return None

        code = request.GET.get("code")
        state = request.GET.get("state")

        if not (code and state):
            return None

        token_payload = {
            "client_id": self._get_setting("OIDC_RP_CLIENT_ID"),
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": absolutify(
                request,
                reverse(
                    self._get_setting(
                        "OIDC_AUTHENTICATION_CALLBACK_URL",
                        "oidc_authentication_callback",
                    )
                ),
            ),
        }

        if code_verifier is not None:
            token_payload["code_verifier"] = code_verifier

        try:
            token_info = self._do_token_request(token_payload)
        except requests.ConnectionError:
            logger.error("Connection refused by token endpoint")
            return None
        except requests.Timeout:
            logger.error("Token endpoint timed out")
            return None
        except requests.RequestException as exc:
            logger.error("Token exchange failed: %s", exc)
            return None

        if "error" in token_info:
            logger.warning(
                "Token error [%s]: %s",
                token_info.get("error"),
                token_info.get("error_description", "(no description)"),
            )
            return None

        try:
            user_info = self._do_userinfo_request(token_info)
        except requests.ConnectionError:
            logger.error("Connection refused by userinfo endpoint")
            return None
        except requests.Timeout:
            logger.error("UserInfo endpoint timed out")
            return None
        except requests.RequestException as exc:
            logger.error("UserInfo request failed: %s", exc)
            return None

        return self._get_or_create_user(user_info)

    def get_user(self, user_id):
        User = get_user_model()
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None

    # ------------------------------------------------------------------
    # Back-channel HTTP helpers
    # ------------------------------------------------------------------

    def _do_token_request(self, payload: dict) -> dict:
        """POST to the OP's token endpoint."""
        response = requests.post(
            self._get_setting("OIDC_OP_TOKEN_ENDPOINT"),
            data=payload,
            verify=self._get_setting("OIDC_VERIFY_SSL", True),
            timeout=self._get_setting("OIDC_TIMEOUT", 10),
        )
        response.raise_for_status()
        return response.json()

    def _do_userinfo_request(self, token_info: dict) -> dict:
        """GET the user profile from the OP's userinfo endpoint."""
        access_token = token_info.get("access_token")
        if not access_token:
            raise ValueError("Token response missing access_token")

        response = requests.get(
            self._get_setting("OIDC_OP_USER_ENDPOINT"),
            headers={"Authorization": f"Bearer {access_token}"},
            verify=self._get_setting("OIDC_VERIFY_SSL", True),
            timeout=self._get_setting("OIDC_TIMEOUT", 10),
        )
        response.raise_for_status()
        return response.json()

    # ------------------------------------------------------------------
    # User provisioning — DID-only lookup, no email fallback
    # ------------------------------------------------------------------

    def _get_or_create_user(self, user_info: dict):
        """Rule 4: username = sub. section 6.2: Sovereign Admin Posture."""
        User = get_user_model()

        sub = user_info.get("sub")
        if not sub:
            logger.warning("OIDC userinfo missing 'sub' claim")
            return None

        username = sub

        try:
            user, created = User.objects.get_or_create(
                username=username,
                defaults={
                    "email": user_info.get("email", ""),
                    "first_name": user_info.get("given_name", ""),
                    "last_name": user_info.get("family_name", ""),
                },
            )
        except Exception:
            logger.exception("User provisioning failed for %s", username)
            return None

        _evaluate_sovereign_admin_posture(user)

        return user

    # ------------------------------------------------------------------
    # Settings helper
    # ------------------------------------------------------------------

    @staticmethod
    def _get_setting(key: str, default=None):
        from django.conf import settings as _s

        return getattr(_s, key, default)
