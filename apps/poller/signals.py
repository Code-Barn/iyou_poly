# Copyright (C) 2026 Byers Brands, LLC
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
Signals for the `poller` app.

This module defines signals for handling events related to federated poll synchronization,
such as creating, updating, and deleting polls and votes.
"""

from django.db import models
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from apps.core.models import FederatedData, FederatedNode
from apps.poller.models import Poll, PollOption, Vote


@receiver(post_save, sender=PollOption)
def sync_poll_option_on_save(sender, instance, created, **kwargs):
    """
    Signal receiver to synchronize a poll when its options are changed.

    Args:
        sender: The model class sending the signal.
        instance: The instance of PollOption being saved.
        created: Boolean indicating if the instance was created.
        **kwargs: Additional keyword arguments.
    """
    # Skip synchronization if the PollOption is being created
    if created:
        return
    sync_poll(instance.poll)


@receiver(post_save, sender=Poll)
def sync_poll_on_save(sender, instance, created, **kwargs):
    """
    Signal receiver to synchronize a poll when it is saved.

    Args:
        sender: The model class sending the signal.
        instance: The instance of Poll being saved.
        created: Boolean indicating if the instance was created.
        **kwargs: Additional keyword arguments.
    """
    sync_poll(instance, created)


def sync_poll(poll, created=False):
    """
    Synchronize a poll to the federated database.

    Args:
        poll: The Poll instance to synchronize.
        created: Boolean indicating if the poll was just created.
    """
    # Convert the poll to a federated data entry
    # Evaluate the options queryset to ensure it is not empty
    options = list(poll.options.all())
    poll_data = {
        "title": poll.title,
        "description": poll.description,
        "created_by": poll.created_by.username,
        "required_scope_type": poll.required_scope_type.name
        if poll.required_scope_type
        else None,
        "required_scope": poll.required_scope.value if poll.required_scope else None,
        "required_credential_type": poll.required_credential_type.name
        if poll.required_credential_type
        else None,
        "is_active": poll.is_active,
        "options": [{"text": option.text, "votes": option.votes} for option in options],
    }

    # Get or create the local federated node
    node, _ = FederatedNode.objects.get_or_create(
        name="local",
        defaults={
            "endpoint": "https://local.example.com",
            "public_key": "public-key-local",
            "is_active": True,
        },
    )

    try:
        # Check if a federated data entry already exists for this poll
        federated_data, created = FederatedData.objects.get_or_create(
            node=node,
            data_type="poll",
            data_id=str(poll.id),
            defaults={
                "data": poll_data,
                "version": 1,
                "is_active": poll.is_active,
            },
        )

        if not created:
            # Update the existing federated data entry
            federated_data.data = poll_data
            # Only increment version if the poll was not just created
            federated_data.version += 1
            federated_data.is_active = poll.is_active
            federated_data.save()
    except Exception as e:
        # Log the error and continue without synchronization
        print(f"Error synchronizing poll: {e}")
        return


@receiver(post_delete, sender=Poll)
def sync_poll_on_delete(sender, instance, **kwargs):
    """
    Signal receiver to synchronize a poll when it is deleted.

    Args:
        sender: The model class sending the signal.
        instance: The instance of Poll being deleted.
        **kwargs: Additional keyword arguments.
    """
    # Mark the federated data entry as inactive
    FederatedData.objects.filter(
        data_type="poll",
        data_id=str(instance.id),
    ).update(is_active=False)


@receiver(post_save, sender=Vote)
def sync_vote_on_save(sender, instance, created, **kwargs):
    """
    Signal receiver to synchronize a vote when it is saved.

    Always increments the PollOption.votes counter on vote creation,
    and optionally syncs to federated data if a FederatedData entry exists.

    Args:
        sender: The model class sending the signal.
        instance: The instance of Vote being saved.
        created: Boolean indicating if the instance was created.
        **kwargs: Additional keyword arguments.
    """
    if created:
        option = instance.option
        option.votes = models.F("votes") + 1
        option.save(update_fields=["votes"])

        federated_data = FederatedData.objects.filter(
            data_type="poll",
            data_id=str(instance.poll.id),
        ).first()

        if federated_data:
            poll_data = federated_data.data
            for opt in poll_data["options"]:
                if opt["text"] == option.text:
                    opt["votes"] = option.votes
                    break
            federated_data.data = poll_data
            federated_data.version = models.F("version") + 1
            federated_data.save(update_fields=["data", "version"])
