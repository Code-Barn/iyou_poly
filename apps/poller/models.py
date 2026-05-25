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
from django.core.exceptions import ValidationError
from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.core.models import FederatedData, Scope, ScopeType

User = get_user_model()


class PollType(models.TextChoices):
    """Types of polls with different visibility and authorization rules."""

    PUBLIC = "public", _("Public")
    FAMILY_SCOPED = "family_scoped", _("Family-Scoped")
    FAMILY_UNIT = "family_unit", _("Family-Unit")
    ORGANIZATION = "organization", _("Organization")


class TemporalPollType(models.TextChoices):
    """Temporal behaviour classification for poll scheduling."""

    TIMED = "timed", _("Timed")
    SCHEDULED = "scheduled", _("Scheduled")
    ONGOING = "ongoing", _("Ongoing")


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

    temporal_type = models.CharField(
        max_length=20,
        choices=TemporalPollType.choices,
        default=TemporalPollType.TIMED,
        help_text=_("Temporal schedule classification: timed, scheduled, or ongoing."),
    )

    is_mutable = models.BooleanField(
        default=False,
        help_text=_("Allow a DID to overwrite their previous vote checkpoint."),
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
    required_credential_type = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text=_("The identity credential required to vote in this poll (e.g., 'municipal_voter')."),
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
    # Write-in ballot governance
    allow_write_ins = models.BooleanField(
        default=False,
        help_text=_("Allow voters to submit write-in ballot options."),
    )
    write_in_display_limit = models.PositiveIntegerField(
        default=5,
        help_text=_("Max write-in options shown in the leaderboard."),
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def clean(self):
        from django.utils import timezone as tz

        if self.temporal_type in (TemporalPollType.TIMED, TemporalPollType.SCHEDULED):
            if self.ends_at is None:
                raise ValidationError(
                    {"ends_at": "TIMED and SCHEDULED polls must have an end time."}
                )

        if self.temporal_type == TemporalPollType.SCHEDULED:
            if self.starts_at is None:
                raise ValidationError(
                    {"starts_at": "SCHEDULED polls must have a start time."}
                )

    class Meta:
        verbose_name = _("Poll")
        verbose_name_plural = _("Polls")

    def __str__(self):
        return self.title

    @property
    def is_expired(self):
        """Check if the poll has ended."""
        if self.temporal_type == TemporalPollType.ONGOING:
            return False
        from django.utils import timezone

        if self.ends_at:
            return timezone.now() > self.ends_at
        return False

    @property
    def is_active_now(self):
        """Check if poll is currently active (within start/end times)."""
        if self.temporal_type == TemporalPollType.ONGOING:
            return self.is_active
        from django.utils import timezone

        now = timezone.now()
        if self.starts_at and now < self.starts_at:
            return False
        if self.ends_at and now > self.ends_at:
            return False
        return self.is_active

    @property
    def total_votes(self):
        """Get total vote count using timestamp-derived aggregation.

        Uses the latest ``Vote.id`` (monotonically increasing) per
        ``(poll, voter_did)`` as the canonical active checkpoint,
        making the tally resilient to out-of-order arrival.
        """
        latest_ids = Vote.objects.filter(poll=self).values("voter_did").annotate(
            latest_id=models.Max("id"),
        ).values("latest_id")
        return Vote.objects.filter(id__in=latest_ids).count()

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

    Note: ``votes`` is a **deprecated** denormalized counter.  Federated
    out-of-order arrivals make it unreliable.  Use the
    ``dynamic_vote_count`` property (timestamp-derived aggregation via
    ``Max(id)`` per voter) for canonical tallies.
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
        help_text=_("DEPRECATED — use dynamic_vote_count instead."),
    )

    # Write-in ballot governance
    is_write_in = models.BooleanField(
        default=False,
        help_text=_("Whether this is a crowd-sourced write-in option."),
    )
    nominated_by = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text=_("DID of the voter who first proposed this write-in."),
    )

    @property
    def dynamic_vote_count(self):
        """Accurate tally computed via timestamp-derived aggregation.

        Only the record with the highest ``Vote.id`` (latest insert) per
        ``(poll, voter_did)`` is counted.  Immune to out-of-order
        federation arrivals.
        """
        latest_ids = Vote.objects.filter(poll=self.poll).values("voter_did").annotate(
            latest_id=models.Max("id"),
        ).values("latest_id")
        return Vote.objects.filter(id__in=latest_ids, option=self).count()

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Poll Option")
        verbose_name_plural = _("Poll Options")

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

    credential_data = models.JSONField(
        blank=True,
        null=True,
        help_text=_("Stores the un-blinded verification credential proof package passed during ingestion."),
    )

    # Mutable checkpoint support (ONGOING / is_mutable polls)
    is_current = models.BooleanField(
        default=True,
        help_text=_(
            "Whether this vote is the voter's active checkpoint. "
            "When a DID re-votes on a mutable poll the previous record "
            "is flipped to False and a new record is ingested."
        ),
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _("Vote")
        verbose_name_plural = _("Votes")

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
