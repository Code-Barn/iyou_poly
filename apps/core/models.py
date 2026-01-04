"""
Core models for the Polly project.

This module defines the foundational models for decentralized identity and federated data.
These models serve as the backbone for the entire project, enabling decentralized
identity management and federated database functionality.
"""

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import models
from django.utils.translation import gettext_lazy as _

User = get_user_model()


class DIDMethod(models.Model):
    """
    Model representing a Decentralized Identifier (DID) method.

    DID methods define the protocol and rules for creating, resolving, and managing DIDs.
    Examples include `did:key`, `did:web`, and `did:ion`.
    """

    name = models.CharField(
        max_length=50,
        unique=True,
        help_text=_("Name of the DID method (e.g., 'key', 'web', 'ion')."),
    )
    description = models.TextField(
        blank=True, help_text=_("Description of the DID method and its use cases.")
    )
    is_active = models.BooleanField(
        default=True,
        help_text=_("Whether this DID method is active and available for use."),
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("DID Method")
        verbose_name_plural = _("DID Methods")

    def __str__(self):
        return f"did:{self.name}"


class DID(models.Model):
    """
    Model representing a Decentralized Identifier (DID).

    A DID is a globally unique identifier that enables verifiable, decentralized identity.
    This model stores DIDs and their associated metadata.
    """

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="dids",
        help_text=_("The user associated with this DID."),
    )
    method = models.ForeignKey(
        DIDMethod,
        on_delete=models.PROTECT,
        help_text=_("The DID method used to create this DID."),
    )
    identifier = models.CharField(
        max_length=255,
        help_text=_(
            "The unique identifier for this DID (e.g., 'example123456789' for 'did:key:example123456789')."
        ),
    )
    did_uri = models.CharField(
        max_length=255,
        unique=True,
        help_text=_("The full DID URI (e.g., 'did:key:example123456789')."),
    )
    is_primary = models.BooleanField(
        default=False, help_text=_("Whether this is the primary DID for the user.")
    )
    is_active = models.BooleanField(
        default=True, help_text=_("Whether this DID is active and available for use.")
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("DID")
        verbose_name_plural = _("DIDs")
        unique_together = ("method", "identifier")

    def __str__(self):
        return self.did_uri

    def save(self, *args, **kwargs):
        """
        Override the save method to ensure the `did_uri` is correctly formatted.
        """
        self.did_uri = f"did:{self.method.name}:{self.identifier}"
        super().save(*args, **kwargs)

    def clean(self):
        """
        Validate the DID before saving.
        """
        if not self.identifier:
            raise ValidationError(_("The identifier cannot be empty."))
        if not self.method:
            raise ValidationError(_("The DID method cannot be empty."))


class DIDDocument(models.Model):
    """
    Model representing a DID Document.

    A DID Document contains public keys, authentication protocols, and service endpoints
    associated with a DID. This model stores the DID Document as a JSON field.
    """

    did = models.OneToOneField(
        DID,
        on_delete=models.CASCADE,
        related_name="document",
        help_text=_("The DID associated with this DID Document."),
    )
    document = models.JSONField(help_text=_("The DID Document as a JSON object."))
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("DID Document")
        verbose_name_plural = _("DID Documents")

    def __str__(self):
        return f"DID Document for {self.did}"


class VerifiableCredential(models.Model):
    """
    Model representing a Verifiable Credential (VC).

    A Verifiable Credential is a tamper-evident credential that has authorship that can be cryptographically verified.
    This model stores VCs issued to users.
    """

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="verifiable_credentials",
        help_text=_("The user to whom this VC is issued."),
    )
    credential = models.JSONField(
        help_text=_("The Verifiable Credential as a JSON object.")
    )
    issuer = models.CharField(
        max_length=255, help_text=_("The DID of the issuer of this VC.")
    )
    is_active = models.BooleanField(
        default=True, help_text=_("Whether this VC is active and valid.")
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Verifiable Credential")
        verbose_name_plural = _("Verifiable Credentials")

    def __str__(self):
        return f"VC for {self.user} issued by {self.issuer}"


class FederatedNode(models.Model):
    """
    Model representing a federated node in the network.

    A federated node is an instance of the Polly application that participates in the federated network.
    This model stores metadata about each node.
    """

    name = models.CharField(
        max_length=100, unique=True, help_text=_("Name of the federated node.")
    )
    endpoint = models.URLField(
        unique=True, help_text=_("The endpoint URL of the federated node.")
    )
    public_key = models.TextField(
        help_text=_("The public key of the federated node for secure communication.")
    )
    is_active = models.BooleanField(
        default=True,
        help_text=_(
            "Whether this node is active and participating in the federated network."
        ),
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Federated Node")
        verbose_name_plural = _("Federated Nodes")

    def __str__(self):
        return self.name


class FederatedData(models.Model):
    """
    Model representing data that is synchronized across federated nodes.

    This model stores data that needs to be shared and synchronized across multiple
    instances of the Polly application.
    """

    node = models.ForeignKey(
        FederatedNode,
        on_delete=models.CASCADE,
        related_name="federated_data",
        help_text=_("The federated node that owns this data."),
    )
    data_type = models.CharField(
        max_length=50, help_text=_("The type of data (e.g., 'poll', 'user_profile').")
    )
    data_id = models.CharField(
        max_length=255,
        help_text=_("The unique identifier for this data within its type."),
    )
    data = models.JSONField(help_text=_("The data as a JSON object."))
    version = models.PositiveIntegerField(
        default=1, help_text=_("The version of this data for conflict resolution.")
    )
    is_active = models.BooleanField(
        default=True, help_text=_("Whether this data is active and synchronized.")
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Federated Data")
        verbose_name_plural = _("Federated Data")
        unique_together = ("node", "data_type", "data_id")

    def __str__(self):
        return f"{self.data_type}:{self.data_id} (Node: {self.node.name})"


class DataSyncLog(models.Model):
    """
    Model representing a log of data synchronization events between federated nodes.

    This model tracks synchronization events for debugging and conflict resolution.
    """

    source_node = models.ForeignKey(
        FederatedNode,
        on_delete=models.CASCADE,
        related_name="sync_logs_sent",
        help_text=_("The node that sent the data."),
    )
    target_node = models.ForeignKey(
        FederatedNode,
        on_delete=models.CASCADE,
        related_name="sync_logs_received",
        help_text=_("The node that received the data."),
    )
    data_type = models.CharField(
        max_length=50, help_text=_("The type of data that was synchronized.")
    )
    data_id = models.CharField(
        max_length=255, help_text=_("The unique identifier for the synchronized data.")
    )
    version = models.PositiveIntegerField(
        help_text=_("The version of the data that was synchronized.")
    )
    status = models.CharField(
        max_length=20,
        choices=[
            ("success", "Success"),
            ("failed", "Failed"),
            ("conflict", "Conflict"),
        ],
        help_text=_("The status of the synchronization event."),
    )
    details = models.TextField(
        blank=True, help_text=_("Additional details about the synchronization event.")
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _("Data Sync Log")
        verbose_name_plural = _("Data Sync Logs")
        ordering = ["-created_at"]

    def __str__(self):
        return f"Sync {self.status}: {self.data_type}:{self.data_id} from {self.source_node} to {self.target_node}"
