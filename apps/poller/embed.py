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
Embeddable Poly widget for external applications.

This module provides a lightweight, embeddable poll widget that can be
integrated into external apps like Byers Brands LLC or Namechart.
"""

import json
import logging
from django.http import HttpRequest, JsonResponse
from django.shortcuts import get_object_or_404, render
from django.views import View

from apps.poller.models import Poll
from apps.core.models import VerifiableCredential
from django.utils import timezone

logger = logging.getLogger(__name__)


class EmbeddablePollWidget(View):
    """
    Render a poll widget that can be embedded in external apps.

    Usage:
    /embed/polls/ - List polls for embedding (filtered by app + user)
    /embed/polls/<poll_id>/ - Single poll widget

    Parameters:
    - embedding_app: The external app identifier (e.g., 'byers-brands-llc')
    - user_did: The user's DID for credential-based filtering
    - scope: Filter by scope value
    - theme: 'light' or 'dark'
    """

    def get(self, request: HttpRequest, poll_id: int = None) -> JsonResponse:
        embedding_app = request.GET.get("embedding_app", "")
        user_did = request.GET.get("user_did", "")
        theme = request.GET.get("theme", "light")

        if poll_id:
            return self._get_single_poll(request, poll_id, embedding_app, user_did, theme)
        return self._get_poll_list(request, embedding_app, user_did, theme)

    def _get_poll_list(self, request, embedding_app, user_did, theme):
        """Get list of polls for embedding."""
        polls = self._get_visible_polls(embedding_app, user_did)

        polls_data = []
        for poll in polls[:10]:  # Limit to 10 for widget
            polls_data.append({
                "id": poll.id,
                "title": poll.title,
                "description": poll.description[:200] if poll.description else "",
                "poll_type": poll.poll_type,
                "total_votes": poll.total_votes,
                "is_active_now": poll.is_active_now,
                "is_proposal": poll.is_proposal,
                "funding_progress": poll.funding_progress if poll.is_proposal else None,
                "options": [
                    {"id": opt.id, "text": opt.text, "votes": opt.votes}
                    for opt in poll.options.all()
                ],
            })

        return JsonResponse({
            "polls": polls_data,
            "theme": theme,
            "embedding_app": embedding_app,
        })

    def _get_single_poll(self, request, poll_id, embedding_app, user_did, theme):
        """Get a single poll for embedding."""
        poll = get_object_or_404(
            Poll.objects.prefetch_related("options"),
            id=poll_id,
            is_active=True,
        )

        # Check if user can view this poll
        if not self._can_user_view_poll(poll, user_did, embedding_app):
            return JsonResponse(
                {"error": "Poll not available for this user"},
                status=403,
            )

        return JsonResponse({
            "poll": {
                "id": poll.id,
                "title": poll.title,
                "description": poll.description,
                "poll_type": poll.poll_type,
                "created_by": poll.created_by.username if poll.created_by else "Unknown",
                "total_votes": poll.total_votes,
                "is_active_now": poll.is_active_now,
                "is_expired": poll.is_expired,
                "is_proposal": poll.is_proposal,
                "funding_goal": str(poll.funding_goal) if poll.funding_goal else None,
                "funding_current": str(poll.funding_current),
                "funding_progress": poll.funding_progress,
                "options": [
                    {
                        "id": opt.id,
                        "text": opt.text,
                        "votes": opt.votes,
                        "percentage": self._calculate_percentage(opt, poll),
                    }
                    for opt in poll.options.all()
                ],
            },
            "theme": theme,
            "user_did": user_did,
        })

    def _get_visible_polls(self, embedding_app, user_did):
        """Get polls visible to the user based on embedding app and credentials."""
        polls = Poll.objects.filter(
            is_active=True,
        ).select_related("created_by").prefetch_related("options")

        if embedding_app:
            polls = polls.filter(embedding_app=embedding_app)

        # Filter by timing
        now = timezone.now()
        polls = polls.exclude(starts_at__gt=now)

        # Filter by user credentials if user_did provided
        if user_did:
            from apps.core.models import DID
            did = DID.objects.filter(did_uri=user_did).first()
            if did:
                user = did.user
                user_scopes = self._get_user_scopes(user)
                polls = self._filter_by_scopes(polls, user_scopes)

        return polls.order_by("-created_at")[:10]

    def _get_user_scopes(self, user):
        """Get user's credential scopes."""
        scopes = []
        credentials = VerifiableCredential.objects.filter(
            user=user, is_active=True
        )
        for vc in credentials:
            cred_data = vc.credential or {}
            scope_data = cred_data.get("scope", {})
            if scope_data.get("value"):
                scopes.append(scope_data["value"])
        return scopes

    def _filter_by_scopes(self, polls, user_scopes):
        """Filter polls by user's credential scopes."""
        from django.db.models import Q

        if not user_scopes:
            return polls.filter(poll_type=Poll.PollType.PUBLIC)

        return polls.filter(
            Q(poll_type=Poll.PollType.PUBLIC) |
            Q(required_scope__value__in=user_scopes) |
            Q(required_scope__isnull=True)
        )

    def _can_user_view_poll(self, poll, user_did, embedding_app):
        """Check if user can view this poll."""
        # Check embedding app
        if embedding_app and poll.embedding_app != embedding_app:
            if poll.embedding_app:  # Poll has a specific app requirement
                return False

        # Check poll type visibility
        if poll.poll_type == Poll.PollType.PUBLIC:
            return True

        if not user_did:
            return poll.poll_type == Poll.PollType.PUBLIC

        # Check user credentials
        from apps.core.models import DID
        did = DID.objects.filter(did_uri=user_did).first()
        if not did:
            return poll.poll_type == Poll.PollType.PUBLIC

        user = did.user
        user_scopes = self._get_user_scopes(user)

        # Family-unit: only creator can view
        if poll.poll_type == Poll.PollType.FAMILY_UNIT:
            return poll.created_by_id == user.id

        # Family-scoped: check scope match
        if poll.poll_type == Poll.PollType.FAMILY_SCOPED:
            if poll.required_scope and poll.required_scope.value in user_scopes:
                return True

        # Check scope match for any poll
        if poll.required_scope and user_scopes:
            return poll.required_scope.value in user_scopes

        return True

    def _calculate_percentage(self, option, poll):
        """Calculate vote percentage for an option."""
        total = sum(opt.votes for opt in poll.options.all())
        if total == 0:
            return 0
        return round((option.votes / total) * 100, 1)


class EmbedPollView(View):
    """Simple embed endpoint that renders HTML for iframe embedding."""

    def get(self, request: HttpRequest, poll_id: int) -> JsonResponse:
        """Return minimal HTML for embedding."""
        embed_html = f'''
        <div id="poly-embed-{poll_id}" class="poly-widget">
            <div class="poly-loading">Loading poll...</div>
        </div>
        <script>
            (function() {{
                var container = document.getElementById('poly-embed-{poll_id}');
                fetch('/api/embed/polls/{poll_id}/?{request.GET.urlencode()}')
                    .then(r => r.json())
                    .then(data => {{
                        container.innerHTML = data.html;
                    }})
                    .catch(e => {{
                        container.innerHTML = '<div class="poly-error">Failed to load poll</div>';
                    }});
            }})();
        </script>
        '''
        return JsonResponse({"html": embed_html})


def embed_polls(request: HttpRequest) -> JsonResponse:
    """
    API endpoint for embedded polls.

    GET /api/embed/polls/
    GET /api/embed/polls/<poll_id>/

    Query parameters:
    - embedding_app: Filter by embedding app
    - user_did: Filter by user DID
    - scope: Filter by scope value
    - theme: light|dark
    """
    widget = EmbeddablePollWidget()
    return widget.get(request)
