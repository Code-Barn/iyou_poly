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

This module defines signals for federated data lifecycle audit logging.
Network dispatch is handled by the Nostr protocol layer (see apps.poller.nostr).
"""

from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from apps.core.models import DataSyncLog, FederatedData, FederatedNode


@receiver(post_save, sender=FederatedData)
def log_federated_data_on_save(sender, instance, created, **kwargs):
    """Audit-log local FederatedData changes."""
    post_save.disconnect(log_federated_data_on_save, sender=FederatedData)
    try:
        if created:
            log_sync_event(
                instance, "local", "created",
                f"FederatedData created: {instance.data_type}:{instance.data_id}",
            )
        else:
            log_sync_event(
                instance, "local", "updated",
                f"FederatedData updated: {instance.data_type}:{instance.data_id} (v{instance.version})",
            )
    finally:
        post_save.connect(log_federated_data_on_save, sender=FederatedData)


@receiver(post_delete, sender=FederatedData)
def log_federated_data_on_delete(sender, instance, **kwargs):
    """Audit-log local FederatedData deletions."""
    log_sync_event(
        instance, "local", "deleted",
        f"FederatedData deleted: {instance.data_type}:{instance.data_id}",
    )


def log_sync_event(data, node_name, status, details):
    """Create an audit log entry for a sync event."""
    node, _ = FederatedNode.objects.get_or_create(
        name=str(node_name),
        defaults={"endpoint": "", "public_key": "", "is_active": True},
    )
    DataSyncLog.objects.create(
        source_node=node,
        target_node=node,
        data_type=data.data_type if hasattr(data, "data_type") else "unknown",
        data_id=data.data_id if hasattr(data, "data_id") else str(getattr(data, "id", "")),
        version=getattr(data, "version", 0),
        status=status,
        details=details,
    )
