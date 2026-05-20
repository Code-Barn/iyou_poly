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
Admin configuration for the `poller` app.

This module registers the poller models with the Django admin interface,
allowing administrators to manage polls, poll options, votes, and geographical scopes.
"""

from django.contrib import admin

from apps.poller.models import Poll, PollOption, Vote


@admin.register(Poll)
class PollAdmin(admin.ModelAdmin):
    """
    Admin interface for the Poll model.
    """

    list_display = (
        "title",
        "created_by",
        "required_scope_type",
        "required_scope",
        "is_active",
        "created_at",
    )
    list_filter = ("is_active", "created_by")
    search_fields = ("title", "description", "created_by__username")
    ordering = ("-created_at",)


@admin.register(PollOption)
class PollOptionAdmin(admin.ModelAdmin):
    """
    Admin interface for the PollOption model.
    """

    list_display = ("poll", "text", "votes", "created_at", "updated_at")
    list_filter = ("poll",)
    search_fields = ("text", "poll__title")
    autocomplete_fields = ("poll",)
    ordering = ("poll", "text")


@admin.register(Vote)
class VoteAdmin(admin.ModelAdmin):
    """
    Admin interface for the Vote model.
    """

    list_display = ("poll", "option", "voter_did", "is_verified", "created_at")
    list_filter = ("poll", "is_verified")
    search_fields = ("poll__title", "option__text", "voter_did")
    raw_id_fields = ("poll", "option", "user")
    ordering = ("-created_at",)
