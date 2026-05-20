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
Core models for the Poly project.

This module defines the foundational models for decentralized identity and federated data.
These models serve as the backbone for the entire project, enabling decentralized
identity management and federated database functionality.
"""

import datetime
import uuid

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

    A federated node is an instance of the Poly application that participates in the federated network.
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
    instances of the Poly application.
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


class SyncMessageType(models.TextChoices):
    ANNOUNCE = "announce", _("Announce")
    REQUEST = "request", _("Request")
    RESPONSE = "response", _("Response")
    VOTE = "vote", _("Vote")
    CREDENTIAL = "credential", _("Credential")
    POLL = "poll", _("Poll")
    MERKLE_UPDATE = "merkle_update", _("Merkle Update")
    PING = "ping", _("Ping")
    PONG = "pong", _("Pong")


class SyncMessage(models.Model):
    """
    Model representing a gossip protocol message for federated data synchronization.

    Messages are signed by the sending node and propagated to peers.
    """

    message_id = models.UUIDField(
        default=uuid.uuid4,
        unique=True,
        help_text=_("Unique identifier for this message."),
    )
    message_type = models.CharField(
        max_length=20,
        choices=SyncMessageType.choices,
        help_text=_("The type of sync message."),
    )
    sender_node = models.ForeignKey(
        FederatedNode,
        on_delete=models.CASCADE,
        related_name="sent_messages",
        help_text=_("The node that sent this message."),
    )
    sender_endpoint = models.URLField(
        max_length=500,
        blank=True,
        help_text=_("The endpoint URL of the sending node."),
    )
    timestamp = models.DateTimeField(
        default=datetime.datetime.utcnow,
        help_text=_("When the message was created."),
    )
    signature = models.TextField(
        blank=True,
        help_text=_("Signature of the message by the sender node."),
    )
    payload = models.JSONField(
        help_text=_("The message payload containing data and metadata."),
    )
    previous_hash = models.CharField(
        max_length=128,
        blank=True,
        help_text=_("Hash of the previous message for chain integrity."),
    )
    proof_of_work = models.PositiveIntegerField(
        default=0,
        help_text=_("Proof of work nonce for message validation."),
    )
    is_processed = models.BooleanField(
        default=False,
        help_text=_("Whether this message has been processed."),
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _("Sync Message")
        verbose_name_plural = _("Sync Messages")
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["message_type"]),
            models.Index(fields=["sender_node", "timestamp"]),
            models.Index(fields=["is_processed"]),
        ]

    def __str__(self):
        return f"{self.message_type}:{self.message_id} from {self.sender_node.name}"


class ScopeType(models.Model):
    """
    Registry of available scope types. Allows dynamic addition of new scope types
    without code changes. This is the backbone of the flexible scope system.
    """

    name = models.CharField(
        max_length=50,
        unique=True,
        help_text=_(
            "The scope type identifier (e.g., 'geographic', 'organization', 'company', 'family')."
        ),
    )
    display_name = models.CharField(
        max_length=100,
        help_text=_(
            "Human-readable name (e.g., 'Geographic', 'Organization', 'Company')."
        ),
    )
    description = models.TextField(
        blank=True,
        help_text=_("Description of this scope type and its intended use."),
    )

    parent_type = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="child_types",
        help_text=_(
            "The scope type that authorizes this one. Null for root/self-authorizing types."
        ),
    )
    hierarchy_depth = models.PositiveIntegerField(
        default=1,
        help_text=_("Maximum depth of hierarchy for this type (1 = no sub-scopes)."),
    )

    is_self_authorizing = models.BooleanField(
        default=False,
        help_text=_(
            "Whether issuers can self-authorize (no parent required). True for organizations, families."
        ),
    )
    requires_proof = models.BooleanField(
        default=True,
        help_text=_("Whether holders must provide proof of scope membership."),
    )

    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _("Scope Type")
        verbose_name_plural = _("Scope Types")
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} ({self.display_name})"


class Scope(models.Model):
    """
    A specific scope instance within a scope type.
    Example: scope_type='geographic', value='DeKalb County, IN'
    """

    scope_type = models.ForeignKey(
        ScopeType,
        on_delete=models.PROTECT,
        related_name="scopes",
        help_text=_("The type of this scope."),
    )
    value = models.CharField(
        max_length=255,
        help_text=_(
            "The specific scope value (e.g., 'DeKalb County, IN', 'Acme Corp')."
        ),
    )

    parent_scope = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="child_scopes",
        help_text=_(
            "Parent scope in hierarchy (e.g., DeKalb County's parent is Indiana)."
        ),
    )

    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _("Scope")
        verbose_name_plural = _("Scopes")
        unique_together = ("scope_type", "value")
        ordering = ["scope_type", "value"]

    def __str__(self):
        return f"{self.scope_type.name}:{self.value}"


class CredentialType(models.Model):
    """
    Defines credential types and their issuance rules.
    """

    name = models.CharField(
        max_length=100,
        unique=True,
        help_text=_(
            "Unique name for this credential type (e.g., 'voting_authorization')."
        ),
    )
    display_name = models.CharField(
        max_length=150,
        help_text=_("Human-readable name (e.g., 'Voting Authorization')."),
    )
    description = models.TextField(blank=True)

    scope_type = models.ForeignKey(
        ScopeType,
        on_delete=models.PROTECT,
        related_name="credential_types",
        help_text=_("The scope type this credential is valid for."),
    )

    parent_credential_type = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="child_credential_types",
        help_text=_(
            "Credential type required to issue this credential (e.g., StateAuthorization issues CountyAuthorization)."
        ),
    )

    max_issuers_per_scope = models.PositiveIntegerField(
        default=5,
        help_text=_("Maximum number of issuers allowed per scope."),
    )
    requires_approval = models.BooleanField(
        default=True,
        help_text=_("Whether issuance requires multi-signer approval."),
    )
    min_approvals = models.PositiveIntegerField(
        default=1,
        help_text=_("Minimum approvals required for issuance."),
    )

    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _("Credential Type")
        verbose_name_plural = _("Credential Types")
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} (scope: {self.scope_type.name})"


class CredentialIssuance(models.Model):
    """
    Records all credential issuances for audit and sync.
    """

    credential = models.JSONField(
        help_text=_("The full Verifiable Credential as a JSON object."),
    )
    holder_did = models.CharField(
        max_length=255,
        help_text=_("The DID of the credential holder."),
    )
    issuer_did = models.CharField(
        max_length=255,
        help_text=_("The DID of the credential issuer."),
    )
    credential_type = models.ForeignKey(
        CredentialType,
        on_delete=models.PROTECT,
        related_name="issuances",
        help_text=_("The type of credential issued."),
    )
    scope = models.ForeignKey(
        Scope,
        on_delete=models.PROTECT,
        related_name="credential_issuances",
        help_text=_("The scope this credential is valid for."),
    )

    ipfs_cid = models.CharField(
        max_length=255,
        blank=True,
        help_text=_("IPFS Content Identifier where credential is stored."),
    )
    blockchain_tx = models.CharField(
        max_length=255,
        blank=True,
        help_text=_("Blockchain transaction hash where credential hash is anchored."),
    )

    STATUS_CHOICES = [
        ("active", _("Active")),
        ("revoked", _("Revoked")),
        ("expired", _("Expired")),
    ]
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="active",
        help_text=_("Current status of the credential."),
    )

    issued_at = models.DateTimeField(auto_now_add=True)
    revoked_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = _("Credential Issuance")
        verbose_name_plural = _("Credential Issuances")
        unique_together = ("holder_did", "credential_type", "scope")
        ordering = ["-issued_at"]

    def __str__(self):
        return f"{self.credential_type.name} issued to {self.holder_did}"


class IssuerAuthorization(models.Model):
    """
    Tracks which issuers are authorized to issue credentials for a scope.
    """

    issuer_did = models.CharField(
        max_length=255,
        help_text=_("The DID of the authorized issuer."),
    )
    credential_type = models.ForeignKey(
        CredentialType,
        on_delete=models.PROTECT,
        related_name="authorizations",
        help_text=_("The credential type this issuer is authorized to issue."),
    )
    scope = models.ForeignKey(
        Scope,
        on_delete=models.PROTECT,
        related_name="issuer_authorizations",
        help_text=_("The scope this issuer is authorized to issue for."),
    )

    authorized_by = models.CharField(
        max_length=255,
        help_text=_("The DID that authorized this issuer."),
    )
    authorization_credential = models.JSONField(
        blank=True,
        help_text=_("The credential proving authorization."),
    )

    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _("Issuer Authorization")
        verbose_name_plural = _("Issuer Authorizations")
        unique_together = ("issuer_did", "credential_type", "scope")
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.issuer_did} authorized for {self.credential_type.name} in {self.scope}"


class IssuerMetrics(models.Model):
    """
    Tracks trust metrics for each issuer within a specific scope.

    Metrics are collected over time to calculate trust scores.
    """

    issuer_did = models.CharField(
        max_length=255,
        help_text=_("The DID of the issuer."),
    )
    scope = models.ForeignKey(
        Scope,
        on_delete=models.CASCADE,
        related_name="issuer_metrics",
        help_text=_("The scope these metrics apply to."),
    )
    total_credentials_issued = models.PositiveIntegerField(
        default=0,
        help_text=_("Total number of credentials issued."),
    )
    unique_holders = models.PositiveIntegerField(
        default=0,
        help_text=_("Number of unique credential holders."),
    )
    credentials_this_month = models.PositiveIntegerField(
        default=0,
        help_text=_("Credentials issued in the current month."),
    )
    credentials_revoked = models.PositiveIntegerField(
        default=0,
        help_text=_("Number of credentials revoked."),
    )
    verifications_attempted = models.PositiveIntegerField(
        default=0,
        help_text=_("Number of verification attempts."),
    )
    verifications_successful = models.PositiveIntegerField(
        default=0,
        help_text=_("Number of successful verifications."),
    )
    scope_violations = models.PositiveIntegerField(
        default=0,
        help_text=_("Number of out-of-scope issuances."),
    )
    first_issuance = models.DateTimeField(
        null=True,
        blank=True,
        help_text=_("When the first credential was issued."),
    )
    last_updated = models.DateTimeField(
        auto_now=True,
        help_text=_("Last time metrics were updated."),
    )

    class Meta:
        verbose_name = _("Issuer Metrics")
        verbose_name_plural = _("Issuer Metrics")
        unique_together = ("issuer_did", "scope")
        ordering = ["-last_updated"]

    def __str__(self):
        return f"Metrics for {self.issuer_did} in {self.scope}"

    @property
    def revocation_rate(self) -> float:
        """Calculate revocation rate as a percentage."""
        if self.total_credentials_issued == 0:
            return 0.0
        return (self.credentials_revoked / self.total_credentials_issued) * 100

    @property
    def verification_success_rate(self) -> float:
        """Calculate verification success rate as a decimal."""
        if self.verifications_attempted == 0:
            return 1.0
        return self.verifications_successful / self.verifications_attempted


class IssuerEndorsement(models.Model):
    """
    Allows issuers to endorse each other within a scope.

    Endorsements contribute to trust scores.
    """

    endorser_did = models.CharField(
        max_length=255,
        help_text=_("The DID of the issuer giving the endorsement."),
    )
    endorsed_issuer_did = models.CharField(
        max_length=255,
        help_text=_("The DID of the issuer being endorsed."),
    )
    scope = models.ForeignKey(
        Scope,
        on_delete=models.CASCADE,
        related_name="endorsements",
        help_text=_("The scope of the endorsement."),
    )
    is_positive = models.BooleanField(
        default=True,
        help_text=_("Whether this is a positive endorsement."),
    )
    comment = models.TextField(
        blank=True,
        help_text=_("Optional comment about the endorsement."),
    )
    is_active = models.BooleanField(
        default=True,
        help_text=_("Whether this endorsement is active."),
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Issuer Endorsement")
        verbose_name_plural = _("Issuer Endorsements")
        unique_together = ("endorser_did", "endorsed_issuer_did", "scope")
        ordering = ["-created_at"]

    def __str__(self):
        direction = "endorsed" if self.is_positive else "warned about"
        return f"{self.endorser_did} {direction} {self.endorsed_issuer_did} in {self.scope}"
