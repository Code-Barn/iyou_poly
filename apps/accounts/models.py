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
    )

    def __str__(self):
        return self.username


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
