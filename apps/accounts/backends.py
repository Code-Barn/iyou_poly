"""
Legacy OIDC backend — kept for test compatibility.

This module is superseded by apps.accounts.utils.auth_pkce which implements
the full canonical PKCE flow. MyOIDCAuthenticationBackend here is retained
only so that existing test_auth.py imports continue to resolve. It does NOT
participate in AUTHENTICATION_BACKENDS (that points to auth_pkce.PKCEAuthenticationBackend).
"""

import logging

from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend

logger = logging.getLogger(__name__)
User = get_user_model()


class MyOIDCAuthenticationBackend(ModelBackend):
    """OIDC backend that maps the 'sub' claim (DID) directly as the Django username.

    Inherits from ModelBackend instead of OIDCAuthenticationBackend to avoid
    OIDC_RP_CLIENT_SECRET enforcement (Rule 2). This class is retained for
    test compatibility only — production auth uses auth_pkce.PKCEAuthenticationBackend.
    """

    def authenticate(self, request, **kwargs):
        claims = kwargs.get("claims")
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
        elif getattr(self, "create_users", True):
            return self.create_user(claims)
        return None

    def create_user(self, claims):
        user = User.objects.create_user(username=claims.get("sub"))
        user.is_active = True
        user.set_unusable_password()
        user.save()
        logger.info("Created sovereign user: %s", user.username)
        return self._evaluate_admin_elevation(user)

    def filter_users_by_claims(self, claims):
        did = claims.get("sub")
        if not did:
            logger.error("No 'sub' claim found in OIDC token")
            return User.objects.none()
        user, created = User.objects.get_or_create(username=did)
        if created:
            user.set_unusable_password()
            user.is_active = True
            user.save()
            logger.info("Auto-created sovereign user via OIDC: %s", user.username)
        else:
            logger.info("Mapped to existing user: %s", user.username)
        self._evaluate_admin_elevation(user)
        return User.objects.filter(id=user.id)

    def verify_claims(self, claims):
        return "sub" in claims

    def get_username(self, claims):
        return claims.get("sub")

    def _evaluate_admin_elevation(self, user):
        if not user or user.is_anonymous:
            return user
        from django.conf import settings

        target_admin_did = getattr(settings, "ADMIN_DID", None)
        if not target_admin_did or user.username != target_admin_did:
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

    def update_user(self, user, claims):
        return user

    def get_user(self, user_id):
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None
