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
    Custom authentication backend to support DID-based and VC-based authentication.
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
        if vc and vc_proof:
            try:
                # Parse VC proof
                proof = json.loads(vc_proof)

                # Verify the VC
                if not verify_vc(vc, {"proof": proof}):
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
