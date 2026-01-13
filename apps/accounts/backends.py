"""
Custom authentication backends for the accounts app.
"""

import json

import didkit
from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend

from apps.accounts.utils.did_utils import verify_vc


class DIDAuthBackend(ModelBackend):
    """
    Custom authentication backend to support DID-based, VC-based, and OIDC authentication.
    """

    def authenticate(self, request, username=None, password=None, **kwargs):
        if username is not None:
            return super().authenticate(request, username, password, **kwargs)

        did = kwargs.get("did")
        vc = kwargs.get("vc")
        vc_proof = kwargs.get("vc_proof")

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
                # Verify the VC
                if not verify_vc(vc, {"proof": json.loads(vc_proof)}):
                    print("VC verification failed")
                    return None

                # Extract the DID from the VC
                vc_data = json.loads(vc)
                vc_did = vc_data.get("credentialSubject", {}).get("id")

                if not vc_did:
                    print("No DID found in VC")
                    return None

                # Fetch the user by DID
                user = User.objects.get(did=vc_did)
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


class OIDCAuthBackend:
    """
    Authentication backend for OIDC providers.

    This backend handles authentication via OIDC providers like Google and GitHub.
    It works in conjunction with social-auth-app-django.
    """

    def authenticate(self, request, **kwargs):
        """
        Authenticate a user using OIDC.

        This method is called by social-auth-app-django after successful
        OIDC authentication to find or create the user.

        Args:
            request: The request object
            **kwargs: Additional authentication parameters

        Returns:
            User: The authenticated user, or None if authentication fails
        """
        User = get_user_model()

        # Get the social user from the strategy
        social = kwargs.get("social")
        if not social:
            return None

        # Try to get an existing user by email first
        email = social.extra_data.get("email")
        if email:
            try:
                return User.objects.get(email=email)
            except User.DoesNotExist:
                pass

        # Try to get user by username (for providers that don't provide email)
        username = social.extra_data.get("username") or social.extra_data.get("login")
        if username:
            try:
                return User.objects.get(username=username)
            except User.DoesNotExist:
                pass

        # Create a new user if auto-provisioning is enabled
        if getattr(settings, "AUTO_PROVISION_OIDC_USERS", True):
            return self._create_oidc_user(social)

        return None

    def _create_oidc_user(self, social):
        """
        Create a new user from OIDC authentication data.

        Args:
            social: The social auth user object

        Returns:
            User: The newly created user
        """
        User = get_user_model()

        # Extract user data from the social auth response
        email = social.extra_data.get("email") or f"{social.uid}@oidc.example.com"
        username = (
            social.extra_data.get("username")
            or social.extra_data.get("login")
            or f"oidc_{social.uid[:20]}"
        )
        first_name = social.extra_data.get("first_name", "")
        last_name = social.extra_data.get("last_name", "")
        full_name = social.extra_data.get("name") or f"{first_name} {last_name}".strip()

        # Create the user
        user = User.objects.create_user(
            username=username, email=email, first_name=first_name, last_name=last_name
        )

        # Generate a DID for the user to enable federated identity
        user.did = generate_did(method="key")
        user.did_method = "key"
        key = json.loads(didkit.generateEd25519Key())
        user.did_key = json.dumps(key)

        # Issue an authentication VC for the user
        credential = {
            "@context": ["https://www.w3.org/2018/credentials/v1"],
            "type": ["VerifiableCredential", "AuthenticationCredential"],
            "issuer": user.did,
            "issuanceDate": "2023-01-01T00:00:00Z",
            "credentialSubject": {"id": user.did, "name": username, "email": email},
        }
        vc = issue_vc(credential, user.did, user.did_key)
        if vc:
            user.add_vc(json.loads(vc))

        user.save()
        return user

    def get_user(self, user_id):
        """
        Get a user by ID.

        Args:
            user_id: The user ID

        Returns:
            User: The user object or None if not found
        """
        User = get_user_model()
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None
