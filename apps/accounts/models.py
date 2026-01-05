import json

from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """
    Custom User model with support for Decentralized Identifiers (DIDs).
    """

    did = models.CharField(
        max_length=255,
        unique=True,
        null=True,
        blank=True,
        help_text="Decentralized Identifier (DID) for the user.",
    )
    vcs = models.JSONField(
        default=list,
        help_text="List of verifiable credentials associated with the user.",
        verbose_name="Verifiable Credentials",
    )
    did_method = models.CharField(
        max_length=50,
        default="key",
        help_text="The DID method used for this user's DID (e.g., 'key', 'web').",
    )
    did_key = models.TextField(
        blank=True,
        help_text="The private key associated with this user's DID (in JWK format).",
    )

    def __str__(self):
        return self.username

    def add_vc(self, vc: dict) -> None:
        """
        Add a verifiable credential to the user's list of VCs.

        Args:
            vc: The verifiable credential to add (as a dictionary).
        """
        vcs = self.vcs.copy()
        vcs.append(vc)
        self.vcs = vcs
        self.save()

    def get_vcs_by_type(self, vc_type: str) -> list:
        """
        Get all VCs of a specific type for this user.

        Args:
            vc_type: The type of VC to filter by (e.g., "VerifiableCredential").

        Returns:
            List of VCs matching the type.
        """
        return [vc for vc in self.vcs if vc.get("type") == vc_type]

    def get_authentication_vc(self) -> dict:
        """
        Get the authentication VC for this user.

        Returns:
            The authentication VC, or None if not found.
        """
        auth_vcs = self.get_vcs_by_type("AuthenticationCredential")
        return auth_vcs[0] if auth_vcs else None


class FederatedIdentity(models.Model):
    """
    Model to store federated identities linked to a user.
    """

    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="federated_identities"
    )
    provider = models.CharField(
        max_length=50,
        help_text="Name of the identity provider (e.g., 'google', 'adfs').",
    )
    external_id = models.CharField(
        max_length=255, help_text="Unique identifier from the external provider."
    )
    is_active = models.BooleanField(
        default=True, help_text="Whether this federated identity is active."
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("provider", "external_id")

    def __str__(self):
        return f"{self.provider}:{self.external_id}"
