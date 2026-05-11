"""
Custom authentication backends for the accounts app.
"""

import json

import didkit
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend


class DIDAuthBackend(ModelBackend):
    """
    Custom authentication backend to support DID-based, VC-based, and OIDC authentication.
    """

    def authenticate(self, request, username=None, password=None, **kwargs):
        if username is not None:
            return super().authenticate(request, username, password, **kwargs)

        did = kwargs.get("did")
        vc = kwargs.get("vc")

        """
        Authenticate a user using their DID and Verifiable Credential (VC).

        Args:
            request: The request object.
            did (str): The Decentralized Identifier (DID) of the user.
            vc (str): The Verifiable Credential (VC) as a JSON string.
            vc_proof (str): The proof for the VC as a JSON string.

        Returns:
            User: The authenticated user, or None if authentication fails.
        """
        User = get_user_model()

        # Authenticate using DID only (fallback)
        if did and not vc:
            try:
                user = User.objects.get(did=did)
                return user
            except User.DoesNotExist:
                return None

        # Authenticate using VC
        if vc:
            try:
                import logging

                logger = logging.getLogger(__name__)
                logger.debug(f"VC for authentication: {vc}")

                # Get the user and their DID key
                vc_data = json.loads(vc)
                vc_did = vc_data.get("credentialSubject", {}).get("id")
                if not vc_did:
                    logger.debug("No DID found in VC")
                    return None

                try:
                    user = User.objects.get(did=vc_did)
                    did_key = user.did_key
                    logger.debug(f"User DID key: {did_key}")
                except User.DoesNotExist:
                    logger.debug(f"User with DID {vc_did} not found")
                    return None

                # Verify the VC using verify_federated_vc with the user's did_key
                from apps.accounts.utils.did_utils import verify_federated_vc

                if not verify_federated_vc(vc, did_key=did_key):
                    logger.debug("VC verification failed")
                    return None

                # Return the user if VC verification succeeds
                return user
            except User.DoesNotExist:
                print(f"User with DID {vc_did} not found")
                return None
            except json.JSONDecodeError as e:
                print(f"Invalid JSON in VC or proof: {e}")
                return None
            except Exception as e:
                print(f"VC authentication failed: {e}")
                return None

        return None


from mozilla_django_oidc.auth import OIDCAuthenticationBackend

class OIDCAuthBackend(OIDCAuthenticationBackend):
    """
    Authentication backend for OIDC providers.
    Maps the 'sub' claim (DID) to the username and user's DID field.
    """

    def create_user(self, claims):
        user = super().create_user(claims)
        user.did = claims.get("sub")
        # Ensure we have a DID key if not already present
        if not user.did_key:
             import didkit
             user.did_key = didkit.generateEd25519Key()
             user.did_method = "key"
        user.save()
        return user

    def update_user(self, user, claims):
        user.did = claims.get("sub")
        user.save()
        return user

    def get_user(self, user_id):
        User = get_user_model()
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None
