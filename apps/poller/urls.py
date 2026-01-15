"""
URL configuration for the `poller` app.

This module defines the URL routes for the API endpoints and template views provided by the `poller` app,
including endpoints for managing polls and votes, as well as server-side rendered views.
"""

from django.urls import path

from apps.poller.views import (
    CreatePollView,
    poll_api,
    poll_detail,
    poll_detail_api,
    poll_list,
    vote_api,
)

urlpatterns = [
    # Poll API
    path(
        "api/polls/",
        poll_api,
        name="poll_api",
    ),
    path(
        "api/polls/<int:poll_id>/",
        poll_detail_api,
        name="poll_detail_api",
    ),
    # Vote API - Primary voting endpoint
    path(
        "api/polls/<int:poll_id>/vote/",
        vote_api,
        name="vote_api",
    ),
    # Template Views
    path(
        "",
        poll_list,
        name="poll_list",
    ),
    path(
        "<int:poll_id>/",
        poll_detail,
        name="poll_detail",
    ),
    path(
        "create/",
        CreatePollView.as_view(),
        name="poll_create",
    ),
]
