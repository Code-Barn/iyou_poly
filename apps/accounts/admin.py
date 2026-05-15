"""
Admin configuration for the `accounts` app.

This module registers the User and FederatedIdentity models with the Django admin interface,
allowing administrators to manage users and their federated identities.
"""

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from apps.accounts.models import FederatedIdentity, User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """
    Admin interface for the custom User model.
    """

    list_display = (
        "username",
        "email",
        "first_name",
        "last_name",
        "is_active",
        "is_staff",
        "did",
    )
    list_filter = ("is_active", "is_staff", "is_superuser")
    search_fields = ("username", "email", "first_name", "last_name", "did")
    ordering = ("username",)
    fieldsets = (
        (None, {"fields": ("username", "password")}),
        ("Personal Info", {"fields": ("first_name", "last_name", "email", "did")}),
        (
            "Permissions",
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                ),
            },
        ),
        ("Important dates", {"fields": ("last_login", "date_joined")}),
    )
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("username", "password1", "password2"),
            },
        ),
    )


@admin.register(FederatedIdentity)
class FederatedIdentityAdmin(admin.ModelAdmin):
    """
    Admin interface for the FederatedIdentity model.
    """

    list_display = ("user", "provider", "external_id", "is_active", "created_at")
    list_filter = ("provider", "is_active")
    search_fields = ("user__username", "external_id", "provider")
    raw_id_fields = ("user",)
    ordering = ("-created_at",)
