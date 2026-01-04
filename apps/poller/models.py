"""
Models for the `poller` app.

This module defines the models for decentralized polling functionality,
including polls, poll options, votes, and geographical scopes.
"""

from django.contrib.auth import get_user_model
from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.core.models import FederatedData

User = get_user_model()


class GeographicalScope(models.Model):
    """
    Model representing a geographical scope for polls.

    This model defines the geographical reach of a poll (e.g., local, state, national, global).
    """

    name = models.CharField(
        max_length=50,
        unique=True,
        help_text=_(
            "Name of the geographical scope (e.g., 'local', 'state', 'national', 'global')."
        ),
    )
    description = models.TextField(
        blank=True,
        help_text=_("Description of the geographical scope and its use cases."),
    )
    is_active = models.BooleanField(
        default=True,
        help_text=_("Whether this geographical scope is active and available for use."),
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Geographical Scope")
        verbose_name_plural = _("Geographical Scopes")

    def __str__(self):
        return self.name


class Poll(models.Model):
    """
    Model representing a poll.

    A poll consists of a question and multiple options for users to vote on.
    """

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
    geographical_scope = models.ForeignKey(
        GeographicalScope,
        on_delete=models.PROTECT,
        help_text=_("The geographical scope of this poll."),
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

    This model records which option a user voted for in a poll.
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
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _("Vote")
        verbose_name_plural = _("Votes")
        unique_together = ("poll", "user")

    def __str__(self):
        return f"{self.user.username} voted for {self.option.text} in {self.poll.title}"


class FederatedPoll(FederatedData):
    """
    Model representing a poll that is synchronized across federated nodes.

    This model extends the `FederatedData` model to store poll data that needs to be
    synchronized across multiple instances of the Polly application.
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
