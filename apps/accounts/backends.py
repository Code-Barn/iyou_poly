"""
Custom authentication backends for the accounts app.
"""

from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend


class DIDAuthBackend(ModelBackend):
    """
    Custom authentication backend to support DID-based authentication.
    """

    def authenticate(self, request, username=None, password=None, **kwargs):
        if username is not None:
            return super().authenticate(request, username, password, **kwargs)
        did = kwargs.get("did")
        """
        Authenticate a user using their DID.

        Args:
            request: The request object.
            did (str): The Decentralized Identifier (DID) of the user.

        Returns:
            User: The authenticated user, or None if authentication fails.
        """
        User = get_user_model()
        try:
            user = User.objects.get(did=did)
            return user
        except User.DoesNotExist:
            return None
