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
URL configuration for the `poller` app.

This module defines the URL routes for the API endpoints and template views provided by the `poller` app,
including endpoints for managing polls and votes, as well as server-side rendered views.
"""

from django.urls import path
from rest_framework.routers import DefaultRouter

from apps.poller.embed import EmbeddablePollWidget
from apps.poller.views import (
    CastVoteAPIView,
    CheckVotingEligibilityAPIView,
    CreatePollView,
    PollViewSet,
    VoteViewSet,
    get_votes,
    poll_api,
    poll_detail,
    poll_detail_api,
    poll_list,
    vote_api,
)

router = DefaultRouter()
router.register(r"api/polls", PollViewSet, basename="poll")
router.register(r"api/votes", VoteViewSet, basename="vote")

urlpatterns = router.urls + [
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
    path(
        "api/polls/<int:poll_id>/history/",
        get_votes,
        name="poll_history_api",
    ),
    # DRF voting endpoints
    path(
        "api/polls/<int:poll_id>/cast/",
        CastVoteAPIView.as_view(),
        name="cast_vote_api",
    ),
    path(
        "api/polls/<int:poll_id>/eligibility/",
        CheckVotingEligibilityAPIView.as_view(),
        name="check_eligibility_api",
    ),
    # Embeddable Poly API
    path(
        "api/embed/polls/",
        EmbeddablePollWidget.as_view(),
        name="embed_polls",
    ),
    path(
        "api/embed/polls/<int:poll_id>/",
        EmbeddablePollWidget.as_view(),
        name="embed_poll_detail",
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
