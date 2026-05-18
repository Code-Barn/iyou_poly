"""
Views for the `poller` app.

This module defines the views for managing polls and votes, including
creating polls, casting votes, and viewing poll results.
"""

import datetime
import json
import logging
from typing import Any, Dict

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.decorators import method_decorator
from django.views import View

from apps.poller.models import Poll, PollOption, Vote

logger = logging.getLogger(__name__)
User = get_user_model()


def poll_api(request: HttpRequest) -> JsonResponse:
    """
    API endpoint for managing polls.

    Args:
        request: The HTTP request object.

    Returns:
        JsonResponse: A JSON response containing poll data or error message.
    """
    if request.method == "GET":
        # Get all active polls
        polls = Poll.objects.filter(is_active=True).prefetch_related("options", "votes")
        data = []
        for poll in polls:
            poll_data = {
                "id": poll.id,
                "title": poll.title,
                "description": poll.description,
                "created_by": poll.created_by.username,
                "created_at": poll.created_at.isoformat(),
                "options": [
                    {
                        "id": option.id,
                        "text": option.text,
                        "votes": option.votes,
                    }
                    for option in poll.options.all()
                ],
                "total_votes": poll.votes.count(),
            }
            data.append(poll_data)
        return JsonResponse({"status": "success", "data": data})

    elif request.method == "POST":
        # Create a new poll
        try:
            data = json.loads(request.body)
            title = data.get("title")
            description = data.get("description", "")
            options = data.get("options", [])

            if not title or not options:
                return JsonResponse(
                    {"status": "error", "message": "Title and options are required."},
                    status=400,
                )

            if len(options) < 2:
                return JsonResponse(
                    {
                        "status": "error",
                        "message": "At least two options are required.",
                    },
                    status=400,
                )

            # Check for duplicate options
            option_texts = [option.strip() for option in options]
            if len(option_texts) != len(set(option_texts)):
                return JsonResponse(
                    {
                        "status": "error",
                        "message": "Duplicate options are not allowed.",
                    },
                    status=400,
                )

            # Create the poll
            poll = Poll.objects.create(
                title=title,
                description=description,
                created_by=request.user,
            )

            # Create the options
            for option_text in option_texts:
                PollOption.objects.create(poll=poll, text=option_text.strip())

            return JsonResponse(
                {
                    "status": "success",
                    "message": "Poll created successfully.",
                    "data": {
                        "id": poll.id,
                        "title": poll.title,
                        "description": poll.description,
                    },
                }
            )
        except json.JSONDecodeError:
            return JsonResponse(
                {"status": "error", "message": "Invalid JSON data."}, status=400
            )
        except Exception as e:
            logger.error(f"Error creating poll: {e}")
            return JsonResponse({"status": "error", "message": str(e)}, status=500)

    return JsonResponse(
        {"status": "error", "message": "Method not allowed."}, status=405
    )


def poll_detail_api(request: HttpRequest, poll_id: int) -> JsonResponse:
    """
    API endpoint for retrieving a specific poll.

    Args:
        request: The HTTP request object.
        poll_id: The ID of the poll.

    Returns:
        JsonResponse: A JSON response containing poll data or error message.
    """
    if request.method == "GET":
        try:
            poll = get_object_or_404(Poll, id=poll_id, is_active=True)
            poll_data = {
                "id": poll.id,
                "title": poll.title,
                "description": poll.description,
                "created_by": poll.created_by.username,
                "created_at": poll.created_at.isoformat(),
                "options": [
                    {
                        "id": option.id,
                        "text": option.text,
                        "votes": option.votes,
                    }
                    for option in poll.options.all()
                ],
                "total_votes": poll.votes.count(),
            }
            return JsonResponse({"status": "success", "data": poll_data})
        except Exception as e:
            logger.error(f"Error retrieving poll: {e}")
            return JsonResponse({"status": "error", "message": str(e)}, status=500)

    return JsonResponse(
        {"status": "error", "message": "Method not allowed."}, status=405
    )


def vote_api(request: HttpRequest, poll_id: int) -> HttpResponse:
    """
    API endpoint for casting a vote in a poll.

    Args:
        request: The HTTP request object.
        poll_id: The ID of the poll.

    Returns:
        HttpResponse: A response containing the updated vote form or error message.
    """
    logger.debug(f"Vote API called for poll_id: {poll_id}")
    logger.debug(f"Request method: {request.method}")
    logger.debug(f"Request headers: {dict(request.headers)}")
    logger.debug(f"User authenticated: {request.user.is_authenticated}")
    logger.debug(f"User: {request.user}")
    logger.debug(f"Content-Type: {request.content_type}")
    logger.debug(f"Request body: {request.body}")
    logger.debug(f"HX-Request: {request.headers.get('HX-Request')}")
    logger.debug(f"Full POST data: {request.POST}")

    # Get option_id from POST data
    option_id = request.POST.get("option_id")
    logger.debug(f"Extracted option_id: {option_id}")

    # If we don't have an option_id, return an error
    if not option_id:
        logger.error(
            f"Option ID is required but not provided. Request data: {request.POST}"
        )
        if request.headers.get("HX-Request") == "true":
            return render(
                request,
                "poller/partials/vote_error.html",
                {"error_message": "Option ID is required.", "poll_id": poll_id},
                status=400,
            )
        return JsonResponse(
            {"status": "error", "message": "Option ID is required."},
            status=400,
        )

    # Call cast_vote to process the vote
    logger.debug(f"Calling cast_vote with option_id: {option_id}")
    response = cast_vote(request, poll_id, {"option_id": option_id})
    logger.debug(f"cast_vote response status: {response.status_code}")

    # If the vote was successful and this is an HTMX request, return the updated form
    if response.status_code == 200:
        # For HTMX requests, return the updated form
        if request.headers.get("HX-Request") == "true":
            logger.debug("Preparing to render updated form for HTMX request")
            try:
                # Get the poll with all options and votes
                poll = Poll.objects.prefetch_related("options", "votes").get(
                    id=poll_id, is_active=True
                )
                logger.debug(f"Retrieved poll with ID: {poll.id}, Title: {poll.title}")

                # Get the user's vote - this should match the vote we just created
                user_vote = None
                if request.user.is_authenticated:
                    try:
                        user_vote = Vote.objects.get(poll=poll, user=request.user)
                        logger.debug(
                            f"Found user vote: {user_vote.id} for option: {user_vote.option.text}"
                        )
                    except Vote.DoesNotExist:
                        logger.debug("No existing vote found for user")
                        pass
                else:
                    logger.debug("User is not authenticated")

                # Return the updated combined form and results
                logger.debug(
                    f"Rendering combined template with user_vote: {user_vote is not None}"
                )
                rendered = render(
                    request,
                    "poller/partials/vote_combined.html",
                    {"poll": poll, "user_vote": user_vote},
                )
                logger.debug(
                    f"Rendered template content length: {len(rendered.content)}"
                )
                return rendered
            except Exception as e:
                logger.error(f"Error rendering poll detail: {e}")
                return render(
                    request,
                    "poller/partials/vote_error.html",
                    {
                        "error_message": f"Error updating poll: {str(e)}",
                        "poll_id": poll_id,
                    },
                    status=500,
                )
        else:
            # For non-HTML requests, return the JSON response
            return response

    return response


def cast_vote(request: HttpRequest, poll_id: int, data: Dict[str, Any]) -> JsonResponse:
    """
    Cast a vote in a poll.

    Args:
        request: The HTTP request object.
        poll_id: The ID of the poll.
        data: The request data (form or JSON).

    Returns:
        JsonResponse: A JSON response confirming the vote.
    """
    try:
        # Check if user is authenticated
        if not request.user.is_authenticated:
            return JsonResponse(
                {"status": "error", "message": "You must be logged in to vote."},
                status=401,
            )

        user = request.user

        # Get option_id from data
        option_id = data.get("option_id")
        if not option_id:
            return JsonResponse(
                {"status": "error", "message": "Option ID is required."},
                status=400,
            )

        # Convert option_id to integer
        try:
            option_id = int(option_id)
        except (ValueError, TypeError):
            return JsonResponse(
                {"status": "error", "message": "Invalid option ID."},
                status=400,
            )

        # Get poll and option
        try:
            poll = Poll.objects.select_related(
                "required_scope_type", "required_scope", "required_credential_type"
            ).get(id=poll_id, is_active=True)
            option = PollOption.objects.get(id=option_id, poll=poll)
        except Poll.DoesNotExist:
            return JsonResponse(
                {"status": "error", "message": "Poll not found or inactive."},
                status=404,
            )
        except PollOption.DoesNotExist:
            return JsonResponse(
                {"status": "error", "message": "Option not found."},
                status=404,
            )

        # Check if user has already voted
        if Vote.objects.filter(poll=poll, user=user).exists():
            return JsonResponse(
                {"status": "error", "message": "You have already voted in this poll."},
                status=400,
            )

        # Check scope/credential requirements
        if (
            poll.required_scope_type
            or poll.required_scope
            or poll.required_credential_type
        ):
            from apps.core.models import CredentialIssuance

            # Get user's DIDs
            dids = user.dids.filter(is_primary=True)

            # username is the DID from OIDC
            all_did_uris = [did.did_uri for did in dids]
            if user.username not in all_did_uris:
                all_did_uris.append(user.username)

            if not all_did_uris:
                return JsonResponse(
                    {
                        "status": "error",
                        "message": "You need a DID to vote in scoped polls. Please create a DID first.",
                        "requires_credential": True,
                    },
                    status=403,
                )

            # Check if user has valid credentials for this poll
            # First check CredentialIssuance table
            user_credentials = CredentialIssuance.objects.filter(
                holder_did__in=all_did_uris, status="active"
            ).select_related("scope", "credential_type", "scope__scope_type")

            # Also check user's stored VCs as backup
            user_vcs = user.get_other_vcs() or []
            vc_scopes = []
            for vc in user_vcs:
                vc_credential = vc.get("credential", {})
                vc_type = vc_credential.get("type", [])
                vc_subject = vc_credential.get("credentialSubject", {})
                vc_description = vc_subject.get("description", "")

                # Extract credential type from VC
                for t in vc_type:
                    if t != "VerifiableCredential":
                        vc_scopes.append(
                            {
                                "type": t,
                                "description": vc_description,
                                "scope_value": vc.get(
                                    "name", ""
                                ),  # Use the VC name user gave
                            }
                        )
                        break

            # Filter credentials based on poll requirements
            valid_credential = None

            # Check CredentialIssuance credentials
            for cred in user_credentials:
                # Check scope type requirement
                if poll.required_scope_type:
                    if cred.scope and cred.scope.scope_type != poll.required_scope_type:
                        continue

                # Check specific scope requirement
                if poll.required_scope:
                    if not cred.scope or cred.scope != poll.required_scope:
                        continue

                # Check credential type requirement
                if poll.required_credential_type:
                    if cred.credential_type != poll.required_credential_type:
                        continue

                # User has a valid credential
                valid_credential = cred
                break

            # If no valid credential from CredentialIssuance, check stored VCs
            if not valid_credential and user_vcs:
                for vc_scope in vc_scopes:
                    # Check credential type requirement
                    if poll.required_credential_type:
                        if poll.required_credential_type.name != vc_scope["type"]:
                            continue

                    # User has a valid VC (we'll allow it since it's in their profile)
                    valid_credential = True
                    break

            if not valid_credential:
                scope_info = ""
                if poll.required_scope:
                    scope_info = f" for {poll.required_scope.value} ({poll.required_scope.scope_type.display_name})"
                elif poll.required_scope_type:
                    scope_info = f" for any {poll.required_scope_type.display_name}"

                cred_info = ""
                if poll.required_credential_type:
                    cred_info = f" with a {poll.required_credential_type.display_name} credential"

                return JsonResponse(
                    {
                        "status": "error",
                        "message": f"This poll requires a credential{scope_info}. You don't have the required credential.{cred_info}",
                        "requires_credential": True,
                        "required_scope": poll.required_scope.value
                        if poll.required_scope
                        else None,
                        "required_scope_type": poll.required_scope_type.display_name
                        if poll.required_scope_type
                        else None,
                        "required_credential_type": poll.required_credential_type.display_name
                        if poll.required_credential_type
                        else None,
                    },
                    status=403,
                )

        # Create the vote with cryptographic signature for audit trail
        voter_did = user.username  # username IS the DID from OIDC

        # Prepare data to hash for audit trail
        import hashlib
        sign_data = {
            "poll_id": poll.id,
            "option_id": option.id,
            "voter_did": voter_did,
            "timestamp": datetime.datetime.now().isoformat()
        }
        signature = hashlib.sha256(json.dumps(sign_data, sort_keys=True).encode()).hexdigest()

        Vote.objects.create(
            poll=poll,
            option=option,
            user=user,
            voter_did=voter_did,
            signature=signature,
            is_verified=True
        )

        # Counter increment handled by post_save signal on Vote

        # For HTMX requests, we'll handle the response in vote_api
        # For non-HTML requests, return a simple success response
        return JsonResponse(
            {
                "status": "success",
                "message": "Vote cast successfully.",
                "data": {
                    "poll_id": poll.id,
                    "option_id": option.id,
                    "user": user.username,
                },
            }
        )
    except Poll.DoesNotExist:
        return JsonResponse(
            {"status": "error", "message": "Poll not found or inactive."}, status=404
        )
    except PollOption.DoesNotExist as e:
        logger.error(f"PollOption.DoesNotExist: {e}")
        return JsonResponse(
            {"status": "error", "message": "Option not found."}, status=404
        )
    except Exception as e:
        logger.error(f"Error casting vote: {e}")
        return JsonResponse({"status": "error", "message": str(e)}, status=500)


def get_polls(request: HttpRequest) -> JsonResponse:
    """
    Get a list of all active polls.

    Args:
        request: The HTTP request object.

    Returns:
        JsonResponse: A JSON response containing a list of polls.
    """
    polls = Poll.objects.filter(is_active=True).prefetch_related("options", "votes")
    data = []
    for poll in polls:
        poll_data = {
            "id": poll.id,
            "title": poll.title,
            "description": poll.description,
            "created_by": poll.created_by.username,
            "created_at": poll.created_at.isoformat(),
            "options": [
                {
                    "id": option.id,
                    "text": option.text,
                    "votes": option.votes,
                }
                for option in poll.options.all()
            ],
            "total_votes": poll.votes.count(),
        }
        data.append(poll_data)
    return JsonResponse({"status": "success", "data": data})


@login_required
def create_poll(request: HttpRequest) -> HttpResponse:
    """
    Create a new poll.

    Args:
        request: The HTTP request object.

    Returns:
        HttpResponse: A response redirecting to the poll detail page or showing errors.
    """
    if request.method == "POST":
        title = request.POST.get("title")
        description = request.POST.get("description", "")
        options = request.POST.getlist("options")

        # Validate input
        if not title or not options:
            messages.error(request, "Title and options are required.")
            return redirect("poll_create")

        if len(options) < 2:
            messages.error(request, "At least two options are required.")
            return redirect("poll_create")

        # Check for duplicate options
        option_texts = [option.strip() for option in options]
        if len(option_texts) != len(set(option_texts)):
            messages.warning(request, "Duplicate options have been removed.")
            option_texts = list(set(option_texts))

        try:
            with transaction.atomic():
                # Create the poll
                poll = Poll.objects.create(
                    title=title,
                    description=description,
                    created_by=request.user,
                )

                # Create the options
                for option_text in option_texts:
                    if option_text.strip():  # Skip empty options
                        PollOption.objects.create(poll=poll, text=option_text.strip())

                messages.success(request, "Poll created successfully!")
                return redirect("poll_detail", poll_id=poll.id)
        except Exception as e:
            logger.error(f"Error creating poll: {e}")
            messages.error(request, f"Error creating poll: {str(e)}")
            return redirect("poll_create")

    return render(request, "poller/poll_create.html")


def get_poll_detail(request: HttpRequest, poll_id: int) -> HttpResponse:
    """
    Get the details of a specific poll.

    Args:
        request: The HTTP request object.
        poll_id: The ID of the poll.

    Returns:
        HttpResponse: A response containing the poll detail page.
    """
    poll = get_object_or_404(Poll, id=poll_id, is_active=True)
    user_vote = None

    if request.user.is_authenticated:
        try:
            user_vote = Vote.objects.get(poll=poll, user=request.user)
        except Vote.DoesNotExist:
            pass

    return render(
        request,
        "poller/poll_detail.html",
        {
            "poll": poll,
            "user_vote": user_vote,
        },
    )


@login_required
def update_poll(request: HttpRequest, poll_id: int) -> HttpResponse:
    """
    Update an existing poll.

    Args:
        request: The HTTP request object.
        poll_id: The ID of the poll.

    Returns:
        HttpResponse: A response redirecting to the poll detail page or showing errors.
    """
    poll = get_object_or_404(Poll, id=poll_id, created_by=request.user)

    if request.method == "POST":
        title = request.POST.get("title")
        description = request.POST.get("description", "")
        options = request.POST.getlist("options")

        # Validate input
        if not title or not options:
            messages.error(request, "Title and options are required.")
            return redirect("poll_update", poll_id=poll.id)

        if len(options) < 2:
            messages.error(request, "At least two options are required.")
            return redirect("poll_update", poll_id=poll.id)

        # Check for duplicate options
        option_texts = [option.strip() for option in options]
        if len(option_texts) != len(set(option_texts)):
            messages.warning(request, "Duplicate options have been removed.")
            option_texts = list(set(option_texts))

        try:
            with transaction.atomic():
                # Update the poll
                poll.title = title
                poll.description = description
                poll.save()

                # Delete existing options
                poll.options.all().delete()

                # Create new options
                for option_text in option_texts:
                    if option_text.strip():  # Skip empty options
                        PollOption.objects.create(poll=poll, text=option_text.strip())

                messages.success(request, "Poll updated successfully!")
                return redirect("poll_detail", poll_id=poll.id)
        except Exception as e:
            logger.error(f"Error updating poll: {e}")
            messages.error(request, f"Error updating poll: {str(e)}")
            return redirect("poll_update", poll_id=poll.id)

    return render(
        request,
        "poller/poll_detail.html",
        {
            "poll": poll,
            "user_vote": user_vote,
        },
    )


# DRF Views for decentralized polling
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.models import ScopeType, Scope, CredentialIssuance

from .models import Poll, PollOption, Vote
from .serializers import (
    PollSerializer,
    PollCreateSerializer,
    PollResultsSerializer,
    VoteSerializer,
    VoteCreateSerializer,
)


class PollViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing Polls with scope-aware filtering.
    """

    queryset = Poll.objects.all()
    serializer_class = PollSerializer

    def get_serializer_class(self):
        if self.action == "create":
            return PollCreateSerializer
        if self.action == "results":
            return PollResultsSerializer
        return PollSerializer

    def get_queryset(self):
        queryset = Poll.objects.all().select_related(
            "required_scope_type", "required_scope", "required_credential_type"
        ).prefetch_related("options")

        # Filter by embedding app (for embedded Poly)
        embedding_app = self.request.query_params.get("embedding_app")
        if embedding_app:
            queryset = queryset.filter(embedding_app=embedding_app)

        # Filter by poll type
        poll_type = self.request.query_params.get("poll_type")
        if poll_type:
            queryset = queryset.filter(poll_type=poll_type)

        # Filter by parent poll (family hierarchy)
        parent_id = self.request.query_params.get("parent_id")
        if parent_id:
            queryset = queryset.filter(parent_poll_id=parent_id)

        # Filter by scope
        scope_type = self.request.query_params.get("scope_type")
        scope_value = self.request.query_params.get("scope_value")
        if scope_type:
            queryset = queryset.filter(required_scope_type__name=scope_type)
        if scope_value:
            queryset = queryset.filter(required_scope__value__icontains=scope_value)

        # Filter by active status
        is_active = self.request.query_params.get("is_active")
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active.lower() == "true")

        # Filter to only show polls visible to the user based on their credentials
        queryset = self._filter_by_user_credentials(queryset)

        return queryset

    def _filter_by_user_credentials(self, queryset):
        """Filter polls based on user's credentials and scope."""
        user = self.request.user
        if not user.is_authenticated:
            # For anonymous users, only show public polls
            return queryset.filter(poll_type=Poll.PollType.PUBLIC)

        # Get user's credentials and their scopes
        from apps.core.models import VerifiableCredential

        user_credentials = VerifiableCredential.objects.filter(
            user=user, is_active=True
        ).select_related("credential_type", "credential_type__scope_type")

        if not user_credentials.exists():
            # No credentials = only public polls
            return queryset.filter(poll_type=Poll.PollType.PUBLIC)

        # Build OR query for visible poll types
        from django.db.models import Q

        visible_types = [Poll.PollType.PUBLIC]

        # Family-unit polls: user is the creator or has family credentials
        visible_types.append(Poll.PollType.FAMILY_UNIT)

        # Family-scoped: include polls from user's family/descendants
        # Organization: include polls from user's organizations

        # Filter by scopes matching user's credentials
        user_scopes = []
        for vc in user_credentials:
            cred_data = vc.credential or {}
            scope_value = cred_data.get("scope", {}).get("value")
            if scope_value:
                user_scopes.append(scope_value)

        if user_scopes:
            # Show polls requiring scopes that match user's credentials
            queryset = queryset.filter(
                Q(poll_type__in=visible_types) |
                Q(required_scope__value__in=user_scopes) |
                Q(required_scope__isnull=True)
            )
        else:
            queryset = queryset.filter(poll_type__in=visible_types)

        return queryset

    @action(detail=True, methods=["get"])
    def results(self, request, pk=None):
        """Get poll results."""
        poll = self.get_object()
        serializer = PollResultsSerializer(poll)
        return Response(serializer.data)

    @action(detail=True, methods=["post"])
    def fund(self, request, pk=None):
        """Add funding to a proposal poll."""
        poll = self.get_object()
        if not poll.is_proposal:
            return Response(
                {"error": "This poll is not a proposal"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        amount = request.data.get("amount")
        if not amount:
            return Response(
                {"error": "Amount is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            amount = float(amount)
            if amount <= 0:
                raise ValueError()
        except (ValueError, TypeError):
            return Response(
                {"error": "Invalid amount"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        poll.funding_current += amount
        poll.save()

        return Response({
            "status": "success",
            "funding_current": poll.funding_current,
            "funding_progress": poll.funding_progress,
        })


class VoteViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing Votes.
    """

    queryset = Vote.objects.all()
    serializer_class = VoteSerializer

    def get_queryset(self):
        queryset = Vote.objects.all()
        poll_id = self.request.query_params.get("poll_id")
        voter_did = self.request.query_params.get("voter_did")

        if poll_id:
            queryset = queryset.filter(poll_id=poll_id)
        if voter_did:
            queryset = queryset.filter(voter_did=voter_did)

        return queryset


class CastVoteAPIView(APIView):
    """
    API endpoint for casting a vote.

    POST /api/polls/{poll_id}/vote/
    """

    def post(self, request, poll_id):
        serializer = VoteCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {"error": "Validation error", "details": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )

        data = serializer.validated_data

        try:
            poll = Poll.objects.get(id=poll_id, is_active=True)
        except Poll.DoesNotExist:
            return Response(
                {"error": "Poll not found or inactive"},
                status=status.HTTP_404_NOT_FOUND,
            )

        if poll.is_expired:
            return Response(
                {"error": "Poll has ended"}, status=status.HTTP_400_BAD_REQUEST
            )

        voter_did = data.get("voter_did")

        if Vote.objects.filter(poll=poll, voter_did=voter_did).exists():
            return Response(
                {"error": "Already voted in this poll"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Verify credential if required
        if poll.required_scope_type and poll.required_credential_type:
            credential = data.get("credential")
            if not credential:
                return Response(
                    {"error": "Credential required to vote in this poll"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Verify credential
            verify_url = request.build_absolute_uri("/api/credentials/verify/")
            import requests as req

            verify_response = req.post(
                verify_url,
                json={
                    "credential": credential,
                    "required_scope_type": poll.required_scope_type.name
                    if poll.required_scope_type
                    else None,
                    "required_scope_value": poll.required_scope.value
                    if poll.required_scope
                    else None,
                },
            )

            if not verify_response.ok or not verify_response.json().get("can_vote"):
                return Response(
                    {
                        "error": "Credential verification failed",
                        "details": verify_response.json(),
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

        try:
            option = PollOption.objects.get(id=data["option_id"], poll=poll)
        except PollOption.DoesNotExist:
            return Response(
                {"error": "Option not found"}, status=status.HTTP_404_NOT_FOUND
            )

        # Get user by DID (username is the DID from OIDC)
        try:
            user = User.objects.get(username=voter_did)
        except User.DoesNotExist:
            user = None

        # Generate audit trail hash (bridge signing for votes comes later)
        import hashlib
        sign_data = {
            "poll_id": poll.id,
            "option_id": option.id,
            "voter_did": voter_did,
            "timestamp": datetime.datetime.now().isoformat()
        }
        signature = data.get("signature", "") or hashlib.sha256(json.dumps(sign_data, sort_keys=True).encode()).hexdigest()

        vote = Vote.objects.create(
            poll=poll,
            option=option,
            voter_did=voter_did,
            user=user,
            signature=signature,
            credential_cid=data.get("credential_cid", ""),
            credential_proof=data.get("credential", {}),
            is_verified=True,
            verification_details={"credential_verified": True},
        )

        # Counter increment handled by post_save signal on Vote

        return Response(
            {
                "vote_id": vote.id,
                "status": "success",
                "message": "Vote recorded successfully",
            },
            status=status.HTTP_201_CREATED,
        )


class CheckVotingEligibilityAPIView(APIView):
    """
    API endpoint for checking if a user can vote in a poll.

    GET /api/polls/{poll_id}/eligibility/?voter_did=<did>
    """

    def get(self, request, poll_id):
        voter_did = request.query_params.get("voter_did")

        if not voter_did:
            return Response(
                {"error": "voter_did query parameter required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            poll = Poll.objects.get(id=poll_id, is_active=True)
        except Poll.DoesNotExist:
            return Response(
                {"error": "Poll not found or inactive"},
                status=status.HTTP_404_NOT_FOUND,
            )

        if poll.is_expired:
            return Response({"eligible": False, "reason": "Poll has ended"})

        # Check if already voted
        if Vote.objects.filter(poll=poll, voter_did=voter_did).exists():
            return Response({"eligible": False, "reason": "Already voted in this poll"})

        # Check scope requirements
        eligibility = {
            "eligible": True,
            "requires_credential": False,
            "scope_type": None,
            "scope_value": None,
            "credential_type": None,
        }

        if poll.required_scope_type:
            eligibility["requires_credential"] = True
            eligibility["scope_type"] = poll.required_scope_type.name
            eligibility["scope_value"] = (
                poll.required_scope.value if poll.required_scope else None
            )
            eligibility["credential_type"] = (
                poll.required_credential_type.name
                if poll.required_credential_type
                else None
            )

            # Check if voter has valid credential
            if poll.required_credential_type:
                has_cred = CredentialIssuance.objects.filter(
                    holder_did=voter_did,
                    credential_type=poll.required_credential_type,
                    scope=poll.required_scope,
                    status="active",
                ).exists()

                if not has_cred:
                    eligibility["eligible"] = False
                    eligibility["reason"] = (
                        f"No valid {poll.required_credential_type.name} credential for scope {poll.required_scope.value if poll.required_scope else ''}"
                    )

        return Response(eligibility)


@login_required
def delete_poll(request: HttpRequest, poll_id: int) -> HttpResponse:
    """
    Delete a poll.

    Args:
        request: The HTTP request object.
        poll_id: The ID of the poll.

    Returns:
        HttpResponse: A response redirecting to the poll list page.
    """
    poll = get_object_or_404(Poll, id=poll_id, created_by=request.user)

    if request.method == "POST":
        try:
            poll.delete()
            messages.success(request, "Poll deleted successfully!")
        except Exception as e:
            logger.error(f"Error deleting poll: {e}")
            messages.error(request, f"Error deleting poll: {str(e)}")

        return redirect("poll_list")

    return render(request, "poller/poll_delete.html", {"poll": poll})


def get_votes(request: HttpRequest, poll_id: int) -> JsonResponse:
    """
    Get the votes for a specific poll for verification purposes.
    """
    poll = get_object_or_404(Poll, id=poll_id, is_active=True)
    votes = Vote.objects.filter(poll=poll).select_related("option", "user")

    data = []
    for vote in votes:
        vote_data = {
            "voter_did": vote.voter_did,
            "option_text": vote.option.text,
            "signature": vote.signature,
            "created_at": vote.created_at.isoformat(),
        }
        data.append(vote_data)

    return JsonResponse({
        "status": "success",
        "poll_title": poll.title,
        "merkle_root": poll.votes_merkle_root,
        "votes": data
    })


def poll_list(request: HttpRequest) -> HttpResponse:
    """
    View for listing all active polls.

    Args:
        request: The HTTP request object.

    Returns:
        HttpResponse: A response containing the poll list page.
    """
    from apps.core.models import CredentialIssuance, ScopeType, Scope

    polls = (
        Poll.objects.filter(is_active=True)
        .prefetch_related("options", "votes")
        .select_related(
            "required_scope_type",
            "required_scope",
            "required_credential_type",
            "created_by",
        )
    )

    # Get user's credentials if logged in
    user_scopes = []
    user_credentials = []
    if request.user.is_authenticated:
        from apps.accounts.models import User

        # Check new DID model
        dids = request.user.dids.filter(is_primary=True)
        did_uris = [did.did_uri for did in dids]

        # username is the DID from OIDC
        if request.user.username not in did_uris:
            did_uris.append(request.user.username)

        # Check CredentialIssuance table
        for did_uri in did_uris:
            credentials = CredentialIssuance.objects.filter(
                holder_did=did_uri, status="active"
            ).select_related("scope", "credential_type", "scope__scope_type")
            user_credentials.extend(credentials)
            user_scopes.extend([c.scope for c in credentials if c.scope])

        # Also include user's stored VCs as credentials
        user_vcs = request.user.get_other_vcs() or []
        for vc in user_vcs:
            # Create a pseudo-credential from stored VC
            vc_credential = vc.get("credential", {})
            vc_type = vc_credential.get("type", [])
            vc_subject = vc_credential.get("credentialSubject", {})

            credential_type_name = "unknown"
            for t in vc_type:
                if t != "VerifiableCredential":
                    credential_type_name = t
                    break

            user_credentials.append(
                {
                    "credential_type": {
                        "name": credential_type_name,
                        "display_name": credential_type_name.replace("_", " ").title(),
                    },
                    "scope": None,
                    "scope_value": vc.get("name", ""),
                    "is_vc": True,  # Flag to indicate this is from stored VC
                }
            )

    # Get available scope types for filtering
    scope_types = ScopeType.objects.filter(is_active=True).order_by(
        "hierarchy_depth", "name"
    )

    # Get filter params
    filter_scope_type = request.GET.get("scope_type")
    filter_scope = request.GET.get("scope")

    # Filter polls by scope if requested
    if filter_scope:
        polls = polls.filter(required_scope_id=filter_scope)
    elif filter_scope_type:
        polls = polls.filter(required_scope_type_id=filter_scope_type)

    return render(
        request,
        "poller/poll_list.html",
        {
            "polls": polls,
            "user_credentials": user_credentials,
            "user_scopes": user_scopes,
            "scope_types": scope_types,
            "filter_scope_type": filter_scope_type,
            "filter_scope": filter_scope,
            "user_has_credentials": len(user_credentials) > 0,
        },
    )


@method_decorator(login_required, name="dispatch")
class CreatePollView(View):
    """
    View for creating a new poll.
    """

    def get(self, request: HttpRequest) -> HttpResponse:
        """
        Handle GET requests to the poll creation page.

        Args:
            request: The HTTP request object.

        Returns:
            HttpResponse: A response containing the poll creation form.
        """
        from apps.core.models import ScopeType, Scope, CredentialType

        scope_types = ScopeType.objects.filter(is_active=True).order_by(
            "hierarchy_depth", "name"
        )

        # Get user's credential-based scopes if logged in
        user_scopes = []
        user_has_any_credentials = False
        if request.user.is_authenticated:
            from apps.core.models import CredentialIssuance

            # Check new DID model
            dids = request.user.dids.filter(is_primary=True)
            did_uris = [did.did_uri for did in dids]

            # username is the DID from OIDC
            if request.user.username not in did_uris:
                did_uris.append(request.user.username)

            # Check CredentialIssuance table
            if did_uris:
                credentials = CredentialIssuance.objects.filter(
                    holder_did__in=did_uris, status="active"
                ).select_related("scope", "scope__scope_type")

                user_scopes = [cred.scope for cred in credentials if cred.scope]
                if credentials.exists():
                    user_has_any_credentials = True

            # Also check stored VCs
            user_vcs = request.user.get_other_vcs() or []
            if user_vcs:
                user_has_any_credentials = True

        # If user has credentials with scopes, only show those scopes
        # Otherwise show all scopes (for admins or users without credentials yet)
        if user_scopes:
            # Deduplicate scopes while preserving order
            seen = set()
            unique_scopes = []
            for s in user_scopes:
                if s and s.id not in seen:
                    seen.add(s.id)
                    unique_scopes.append(s)
            scopes = unique_scopes
        else:
            scopes = Scope.objects.filter(is_active=True).select_related("scope_type")

        credential_types = CredentialType.objects.filter(is_active=True).order_by(
            "name"
        )

        return render(
            request,
            "poller/poll_create.html",
            {
                "scope_types": scope_types,
                "scopes": scopes,
                "credential_types": credential_types,
                "user_has_credentials": user_has_any_credentials,
            },
        )

    def post(self, request: HttpRequest) -> HttpResponse:
        """
        Handle POST requests to create a new poll.

        Args:
            request: The HTTP request object.

        Returns:
            HttpResponse: A response redirecting to the poll detail page or showing errors.
        """
        from apps.core.models import ScopeType, Scope, CredentialType

        title = request.POST.get("title")
        description = request.POST.get("description", "")

        # Handle options from textarea - one per line
        options_text = request.POST.get("options", "")
        options = [line.strip() for line in options_text.split("\n") if line.strip()]

        # Handle scope requirements
        required_scope_type_id = request.POST.get("required_scope_type")
        required_scope_id = request.POST.get("required_scope")
        required_credential_type_id = request.POST.get("required_credential_type")

        # Validate input
        if not title or not options:
            messages.error(request, "Title and options are required.")
            return redirect("poll_create")

        if len(options) < 2:
            messages.error(request, "At least two options are required.")
            return redirect("poll_create")

        # Check for duplicate options
        option_texts = [option.strip() for option in options]
        if len(option_texts) != len(set(option_texts)):
            messages.warning(request, "Duplicate options have been removed.")
            option_texts = list(set(option_texts))

        try:
            with transaction.atomic():
                # Get scope objects if provided
                required_scope_type = None
                required_scope = None
                required_credential_type = None

                if required_scope_type_id:
                    try:
                        required_scope_type = ScopeType.objects.get(
                            id=required_scope_type_id
                        )
                    except ScopeType.DoesNotExist:
                        pass

                if required_scope_id:
                    try:
                        required_scope = Scope.objects.get(id=required_scope_id)
                    except Scope.DoesNotExist:
                        pass

                if required_credential_type_id:
                    try:
                        required_credential_type = CredentialType.objects.get(
                            id=required_credential_type_id
                        )
                    except CredentialType.DoesNotExist:
                        pass

                # Create the poll
                poll = Poll.objects.create(
                    title=title,
                    description=description,
                    created_by=request.user,
                    required_scope_type=required_scope_type,
                    required_scope=required_scope,
                    required_credential_type=required_credential_type,
                )

                # Create the options
                for option_text in option_texts:
                    if option_text.strip():  # Skip empty options
                        PollOption.objects.create(poll=poll, text=option_text.strip())

                messages.success(request, "Poll created successfully!")
                return redirect("poll_detail", poll_id=poll.id)
        except Exception as e:
            logger.error(f"Error creating poll: {e}")
            messages.error(request, f"Error creating poll: {str(e)}")
            return redirect("poll_create")


def poll_detail(request: HttpRequest, poll_id: int) -> HttpResponse:
    """
    View for displaying a specific poll.

    Args:
        request: The HTTP request object.
        poll_id: The ID of the poll.

    Returns:
        HttpResponse: A response containing the poll detail page.
    """
    poll = get_object_or_404(Poll, id=poll_id, is_active=True)
    user_vote = None

    if request.user.is_authenticated:
        try:
            user_vote = Vote.objects.get(poll=poll, user=request.user)
        except Vote.DoesNotExist:
            pass

    return render(
        request,
        "poller/poll_detail.html",
        {
            "poll": poll,
            "user_vote": user_vote,
        },
    )
