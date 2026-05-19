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
Admin configuration for the `core` app.

This module registers the core models with the Django admin interface,
allowing administrators to manage decentralized identity and federated data.
"""

from django.contrib import admin

from apps.core.models import (
    DID,
    DataSyncLog,
    DIDDocument,
    DIDMethod,
    FederatedData,
    FederatedNode,
    VerifiableCredential,
)


@admin.register(DIDMethod)
class DIDMethodAdmin(admin.ModelAdmin):
    """
    Admin interface for the DIDMethod model.
    """

    list_display = ("name", "is_active", "created_at", "updated_at")
    list_filter = ("is_active",)
    search_fields = ("name", "description")
    ordering = ("name",)


@admin.register(DID)
class DIDAdmin(admin.ModelAdmin):
    """
    Admin interface for the DID model.
    """

    list_display = (
        "did_uri",
        "user",
        "method",
        "is_primary",
        "is_active",
        "created_at",
    )
    list_filter = ("method", "is_primary", "is_active")
    search_fields = ("did_uri", "identifier", "user__username")
    raw_id_fields = ("user",)
    ordering = ("-created_at",)


@admin.register(DIDDocument)
class DIDDocumentAdmin(admin.ModelAdmin):
    """
    Admin interface for the DIDDocument model.
    """

    list_display = ("did", "created_at", "updated_at")
    search_fields = ("did__did_uri",)
    raw_id_fields = ("did",)


@admin.register(VerifiableCredential)
class VerifiableCredentialAdmin(admin.ModelAdmin):
    """
    Admin interface for the VerifiableCredential model.
    """

    list_display = ("user", "issuer", "is_active", "created_at", "updated_at")
    list_filter = ("is_active",)
    search_fields = ("user__username", "issuer")
    raw_id_fields = ("user",)


@admin.register(FederatedNode)
class FederatedNodeAdmin(admin.ModelAdmin):
    """
    Admin interface for the FederatedNode model.
    """

    list_display = ("name", "endpoint", "is_active", "created_at", "updated_at")
    list_filter = ("is_active",)
    search_fields = ("name", "endpoint")
    ordering = ("name",)


@admin.register(FederatedData)
class FederatedDataAdmin(admin.ModelAdmin):
    """
    Admin interface for the FederatedData model.
    """

    list_display = (
        "node",
        "data_type",
        "data_id",
        "version",
        "is_active",
        "created_at",
    )
    list_filter = ("data_type", "is_active", "node")
    search_fields = ("data_type", "data_id", "node__name")
    raw_id_fields = ("node",)
    ordering = ("-created_at",)


@admin.register(DataSyncLog)
class DataSyncLogAdmin(admin.ModelAdmin):
    """
    Admin interface for the DataSyncLog model.
    """

    list_display = (
        "source_node",
        "target_node",
        "data_type",
        "data_id",
        "version",
        "status",
        "created_at",
    )
    list_filter = ("status", "data_type", "source_node", "target_node")
    search_fields = ("data_type", "data_id", "details")
    raw_id_fields = ("source_node", "target_node")
    ordering = ("-created_at",)
    readonly_fields = ("created_at",)
