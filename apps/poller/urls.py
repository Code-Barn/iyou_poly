"""
URL configuration for the `poller` app.

This module defines the URL routes for the API endpoints provided by the `poller` app,
including endpoints for managing polls and votes.
"""

from django.urls import path

from apps.poller.views import (
    poll_api,
    poll_detail_api,
    vote_api,
    vote_detail_api,
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
    # Vote API
    path(
        "api/polls/<int:poll_id>/votes/",
        vote_api,
        name="vote_api",
    ),
    path(
        "api/polls/<int:poll_id>/votes/detail/",
        vote_detail_api,
        name="vote_detail_api",
    ),
]
