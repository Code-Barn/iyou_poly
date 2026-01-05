"""
Signals for the `poller` app.

This module defines signals for handling events related to federated poll synchronization,
such as creating, updating, and deleting polls and votes.
"""

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
        "geographical_scope": poll.geographical_scope.name,
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

    Args:
        sender: The model class sending the signal.
        instance: The instance of Vote being saved.
        created: Boolean indicating if the instance was created.
        **kwargs: Additional keyword arguments.
    """
    if created:
        # Update the federated data entry for the poll
        federated_data = FederatedData.objects.filter(
            data_type="poll",
            data_id=str(instance.poll.id),
        ).first()

        if federated_data:
            # Update the poll data with the new vote count
            poll_data = federated_data.data
            for option in poll_data["options"]:
                if option["text"] == instance.option.text:
                    option["votes"] += 1
                    # Update the vote count for the poll option
                    instance.option.votes = option["votes"]
                    instance.option.save()
                    break
            federated_data.data = poll_data
            federated_data.version += 1
            federated_data.save()
            # Update the vote count for the poll option after saving federated data
            instance.option.save()
            instance.option.save()
