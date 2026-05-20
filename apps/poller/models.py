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
Models for the `poller` app.

This module defines the models for decentralized polling functionality,
including polls, poll options, votes, and geographical scopes.
"""

from django.contrib.auth import get_user_model
from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.core.models import FederatedData, Scope, ScopeType, CredentialType

User = get_user_model()


class PollType(models.TextChoices):
    """Types of polls with different visibility and authorization rules."""

    PUBLIC = "public", _("Public")
    FAMILY_SCOPED = "family_scoped", _("Family-Scoped")
    FAMILY_UNIT = "family_unit", _("Family-Unit")
    ORGANIZATION = "organization", _("Organization")


class Poll(models.Model):
    """
    Model representing a poll.

    A poll consists of a question and multiple options for users to vote on.
    Supports scope-based voting requirements for decentralized authorization.
    """

    poll_type = models.CharField(
        max_length=20,
        choices=PollType.choices,
        default=PollType.PUBLIC,
        help_text=_("Type of poll determining visibility and authorization rules."),
    )

    # Family/organization hierarchy
    parent_poll = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="child_polls",
        help_text=_("Parent poll for hierarchical family/organization polls."),
    )
    embedding_app = models.CharField(
        max_length=100,
        blank=True,
        help_text=_("Embedding application identifier (e.g., 'byers-brands-llc', 'namechart')."),
    )

    title = models.CharField(
        max_length=255,
        help_text=_("Title of the poll."),
    )
    description = models.TextField(
        blank=True,
        help_text=_("Description of the poll."),
    )
    created_by = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name="polls_created",
        help_text=_("The user who created this poll."),
    )

    # Scope-based voting requirements (replaces geographical_scope)
    required_scope_type = models.ForeignKey(
        ScopeType,
        on_delete=models.PROTECT,
        related_name="polls_requiring_scope",
        help_text=_("The scope type required to vote in this poll."),
        null=True,
        blank=True,
    )
    required_scope = models.ForeignKey(
        Scope,
        on_delete=models.PROTECT,
        related_name="polls_requiring_scope",
        help_text=_("The specific scope value required to vote."),
        null=True,
        blank=True,
    )
    required_credential_type = models.ForeignKey(
        CredentialType,
        on_delete=models.PROTECT,
        related_name="polls_requiring_credential",
        help_text=_("The credential type required to vote in this poll."),
        null=True,
        blank=True,
    )

    # Trust requirements
    min_issuer_trust_score = models.FloatField(
        default=0.0,
        help_text=_("Minimum trust score for credential issuers (0.0 - 1.0)."),
    )
    require_multiple_issuers = models.BooleanField(
        default=False,
        help_text=_("Require credentials from multiple issuers."),
    )

    # Vote power and rules
    vote_power_rule = models.CharField(
        max_length=50,
        default="1:1",
        help_text=_("The rule defining voting power calculation (e.g., '1:1', 'investor_share')."),
    )
    vote_power_ratio = models.FloatField(
        default=1.0,
        help_text=_("The multiplier for voting power if using a custom rule."),
    )

    # Timing for scheduled polls
    starts_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text=_("When the poll starts. Null for immediate activation."),
    )
    ends_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text=_("When the poll ends. Null for no end time."),
    )

    # Proposal mode for funding/decision workflows
    is_proposal = models.BooleanField(
        default=False,
        help_text=_("Whether this is a proposal requiring funding."),
    )
    funding_goal = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        help_text=_("Funding goal for proposal."),
    )
    funding_current = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        help_text=_("Current funding amount."),
    )
    funding_deadline = models.DateTimeField(
        null=True,
        blank=True,
        help_text=_("Deadline for funding before proposal expires."),
    )

    # Decentralized storage
    ipfs_cid = models.CharField(
        max_length=255,
        blank=True,
        help_text=_("IPFS Content Identifier for poll data."),
    )
    blockchain_anchor = models.CharField(
        max_length=255,
        blank=True,
        help_text=_("Blockchain transaction hash anchoring this poll."),
    )
    votes_merkle_root = models.CharField(
        max_length=255,
        blank=True,
        help_text=_("Merkle root of all votes for verification."),
    )
    vote_count_anchor = models.CharField(
        max_length=255,
        blank=True,
        help_text=_("Blockchain anchor for vote count."),
    )

    is_active = models.BooleanField(
        default=True,
        help_text=_("Whether this poll is active and available for voting."),
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Poll")
        verbose_name_plural = _("Polls")

    def __str__(self):
        return self.title

    @property
    def is_expired(self):
        """Check if the poll has ended."""
        from django.utils import timezone

        if self.ends_at:
            return timezone.now() > self.ends_at
        return False

    @property
    def is_active_now(self):
        """Check if poll is currently active (within start/end times)."""
        from django.utils import timezone

        now = timezone.now()
        if self.starts_at and now < self.starts_at:
            return False
        if self.ends_at and now > self.ends_at:
            return False
        return self.is_active

    @property
    def total_votes(self):
        """Get total vote count."""
        return sum(option.votes for option in self.options.all())

    @property
    def funding_progress(self):
        """Get funding progress percentage."""
        if not self.funding_goal or self.funding_goal == 0:
            return 0
        return min(100, (self.funding_current / self.funding_goal) * 100)


class PollOption(models.Model):
    """
    Model representing an option in a poll.

    Each poll can have multiple options for users to choose from.
    """

    poll = models.ForeignKey(
        Poll,
        on_delete=models.CASCADE,
        related_name="options",
        help_text=_("The poll to which this option belongs."),
    )
    text = models.CharField(
        max_length=255,
        help_text=_("Text of the poll option."),
    )
    votes = models.PositiveIntegerField(
        default=0,
        help_text=_("Number of votes this option has received."),
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Poll Option")
        verbose_name_plural = _("Poll Options")
        unique_together = ("poll", "text")

    def __str__(self):
        return f"{self.poll.title}: {self.text}"


class Vote(models.Model):
    """
    Model representing a vote cast by a user in a poll.

    This model records which option a user voted for, with cryptographic
    verification for decentralized trust.
    """

    poll = models.ForeignKey(
        Poll,
        on_delete=models.CASCADE,
        related_name="votes",
        help_text=_("The poll in which this vote was cast."),
    )
    option = models.ForeignKey(
        PollOption,
        on_delete=models.CASCADE,
        related_name="vote_options",
        help_text=_("The option that was voted for."),
    )
    user = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name="votes_cast",
        help_text=_("The user who cast this vote."),
        null=True,
        blank=True,
    )

    # DID-based voting (can vote without local user account)
    voter_did = models.CharField(
        max_length=255,
        blank=True,
        help_text=_("The DID of the voter."),
    )

    # Cryptographic verification
    signature = models.TextField(
        null=True,
        blank=True,
        help_text=_("Cryptographic signature from voter's DID key."),
    )
    merkle_root = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        help_text=_("Merkle root of vote batch for cryptographic verification."),
    )
    credential_cid = models.CharField(
        max_length=255,
        blank=True,
        help_text=_("IPFS CID of voter's voting credential."),
    )
    credential_proof = models.JSONField(
        default=dict,
        blank=True,
        help_text=_("Zero-knowledge proof of credential possession."),
    )

    # Vote weight (always 1 for this app)
    weight = models.PositiveIntegerField(
        default=1,
        help_text=_("Weight of this vote. Always 1 for equal voting."),
    )

    # Decentralized storage
    ipfs_cid = models.CharField(
        max_length=255,
        blank=True,
        help_text=_("IPFS Content Identifier for this vote."),
    )
    blockchain_tx = models.CharField(
        max_length=255,
        blank=True,
        help_text=_("Blockchain transaction hash for this vote."),
    )

    # Verification status
    is_verified = models.BooleanField(
        default=False,
        help_text=_("Whether this vote has been cryptographically verified."),
    )
    verification_details = models.JSONField(
        default=dict,
        blank=True,
        help_text=_("Details about vote verification."),
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _("Vote")
        verbose_name_plural = _("Votes")
        unique_together = ("poll", "voter_did")

    def __str__(self):
        identity = self.user.username if self.user else self.voter_did
        return f"{identity} cast vote for '{self.option.text}' in [{self.poll.title}]"


class FederatedPoll(FederatedData):
    """
    Model representing a poll that is synchronized across federated nodes.

    This model extends the `FederatedData` model to store poll data that needs to be
    synchronized across multiple instances of the Poly application.
    """

    class Meta:
        verbose_name = _("Federated Poll")
        verbose_name_plural = _("Federated Polls")
        proxy = True

    def save(self, *args, **kwargs):
        """
        Override the save method to ensure the data is correctly formatted.
        """
        if not self.data_type:
            self.data_type = "poll"
        super().save(*args, **kwargs)
