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
Signals for the `poller` app.

This module defines signals for federated poll synchronization via Nostr protocol.
On local model changes, events are broadcast as Nostr events (kind:30023 for polls,
kind:1111 for votes) to configured relays.
"""

from django.db import models
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from apps.core.models import FederatedData, FederatedNode
from apps.poller.models import Poll, PollOption, Vote

from . import nostr


@receiver(post_save, sender=PollOption)
def sync_poll_option_on_save(sender, instance, created, **kwargs):
    """Re-broadcast poll when its options change."""
    if created:
        return
    sync_poll(instance.poll)


@receiver(post_save, sender=Poll)
def sync_poll_on_save(sender, instance, created, **kwargs):
    """Broadcast poll definition as kind:30023 Nostr event."""
    sync_poll(instance, created)


def sync_poll(poll, created=False):
    """Persist poll to local FederatedData and broadcast via Nostr."""
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

    node, _ = FederatedNode.objects.get_or_create(
        name="local",
        defaults={
            "endpoint": "",
            "public_key": "local",
            "is_active": True,
        },
    )

    try:
        federated_data, created_flag = FederatedData.objects.get_or_create(
            node=node,
            data_type="poll",
            data_id=str(poll.id),
            defaults={
                "data": poll_data,
                "version": 1,
                "is_active": poll.is_active,
            },
        )
        if not created_flag:
            federated_data.data = poll_data
            federated_data.version += 1
            federated_data.is_active = poll.is_active
            federated_data.save()
    except Exception as e:
        print(f"Error synchronizing poll: {e}")
        return

    nostr.publish_poll(poll)


@receiver(post_delete, sender=Poll)
def sync_poll_on_delete(sender, instance, **kwargs):
    """Mark poll inactive in local ledger and broadcast tombstone via Nostr."""
    FederatedData.objects.filter(
        data_type="poll",
        data_id=str(instance.id),
    ).update(is_active=False)

    instance.is_active = False
    nostr.publish_poll(instance)


@receiver(post_save, sender=Vote)
def sync_vote_on_save(sender, instance, created, **kwargs):
    """Broadcast vote as kind:1111 Nostr event."""
    if created:
        federated_data = FederatedData.objects.filter(
            data_type="poll",
            data_id=str(instance.poll.id),
        ).first()

        if federated_data:
            poll_data = federated_data.data
            for opt in poll_data["options"]:
                if opt["text"] == instance.option.text:
                    opt["votes"] = Vote.objects.filter(
                        option=instance.option, is_current=True
                    ).count()
                    break
            federated_data.data = poll_data
            federated_data.version = models.F("version") + 1
            federated_data.save(update_fields=["data", "version"])

        nostr.publish_vote(instance, instance.poll_id)
