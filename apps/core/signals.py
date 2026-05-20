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
Signals for the `core` app.

This module defines signals for handling events related to federated data synchronization,
such as creating, updating, and deleting federated data.
"""

from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from apps.core.models import DataSyncLog, FederatedData, FederatedNode


@receiver(post_save, sender=FederatedData)
def sync_federated_data_on_save(sender, instance, created, **kwargs):
    """
    Signal receiver to synchronize federated data when it is saved.

    Args:
        sender: The model class sending the signal.
        instance: The instance of FederatedData being saved.
        created: Boolean indicating if the instance was created.
        **kwargs: Additional keyword arguments.
    """
    # Disconnect the signal to prevent infinite loops
    post_save.disconnect(sync_federated_data_on_save, sender=FederatedData)

    try:
        if created:
            # New data was created, sync to all active nodes
            sync_new_data(instance)
        else:
            # Existing data was updated, sync the changes
            sync_updated_data(instance, created)
    finally:
        # Reconnect the signal
        post_save.connect(sync_federated_data_on_save, sender=FederatedData)


@receiver(post_delete, sender=FederatedData)
def sync_federated_data_on_delete(sender, instance, **kwargs):
    """
    Signal receiver to synchronize federated data when it is deleted.

    Args:
        sender: The model class sending the signal.
        instance: The instance of FederatedData being deleted.
        **kwargs: Additional keyword arguments.
    """
    sync_deleted_data(instance)


def sync_new_data(data):
    """
    Synchronize new federated data to all active nodes.

    Args:
        data: The FederatedData instance to synchronize.
    """
    active_nodes = FederatedNode.objects.filter(is_active=True).exclude(id=data.node.id)
    for node in active_nodes:
        sync_data_to_node(data, node)


def sync_updated_data(data, created=False):
    """
    Synchronize updated federated data to all active nodes.

    Args:
        data: The FederatedData instance to synchronize.
        created: Boolean indicating if the instance was created.
    """
    # Skip synchronization if the data was just created
    if created:
        return

    # Disconnect the signal to prevent infinite loops
    post_save.disconnect(sync_federated_data_on_save, sender=FederatedData)

    try:
        # Increment the version before syncing
        data.version += 1
        data.save(update_fields=["version"])

        active_nodes = FederatedNode.objects.filter(is_active=True).exclude(
            id=data.node.id
        )
        for node in active_nodes:
            sync_data_to_node(data, node)
    finally:
        # Reconnect the signal
        post_save.connect(sync_federated_data_on_save, sender=FederatedData)


def sync_deleted_data(data):
    """
    Synchronize the deletion of federated data to all active nodes.

    Args:
        data: The FederatedData instance being deleted.
    """
    active_nodes = FederatedNode.objects.filter(is_active=True).exclude(id=data.node.id)
    for node in active_nodes:
        log_sync_event(
            data, node, "success", f"Data deleted: {data.data_type}:{data.data_id}"
        )


def sync_data_to_node(data, node):
    """
    Synchronize data to a specific federated node.

    Args:
        data: The FederatedData instance to synchronize.
        node: The FederatedNode instance to synchronize to.
    """
    # Placeholder for actual synchronization logic
    # In a real implementation, this would involve making an API call to the node's endpoint
    try:
        # Simulate synchronization
        log_sync_event(
            data, node, "success", f"Data synchronized: {data.data_type}:{data.data_id}"
        )
    except Exception as e:
        log_sync_event(data, node, "failed", f"Error synchronizing data: {str(e)}")


def log_sync_event(data, node, status, details):
    """
    Log a synchronization event.

    Args:
        data: The FederatedData instance being synchronized.
        node: The FederatedNode instance being synchronized to.
        status: The status of the synchronization event.
        details: Additional details about the event.
    """
    DataSyncLog.objects.create(
        source_node=data.node,
        target_node=node,
        data_type=data.data_type,
        data_id=data.data_id,
        version=data.version,
        status=status,
        details=details,
    )
