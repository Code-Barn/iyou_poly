"""
Views for the `poller` app.

This module defines the views for managing polls and votes, including
creating polls, casting votes, and viewing poll results.
"""

import json
import logging
from typing import Any, Dict

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.http import require_GET, require_http_methods, require_POST

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
                geographical_scope_id=1,  # Default geographical scope
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
            poll = Poll.objects.get(id=poll_id, is_active=True)
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

        # Create the vote
        Vote.objects.create(poll=poll, option=option, user=user)

        # Increment the vote count on the option
        option.votes = option.votes + 1
        option.save()

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
                    geographical_scope_id=1,  # Default geographical scope
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
        "poller/poll_update.html",
        {
            "poll": poll,
            "options": [option.text for option in poll.options.all()],
        },
    )


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
    Get the votes for a specific poll.

    Args:
        request: The HTTP request object.
        poll_id: The ID of the poll.

    Returns:
        JsonResponse: A JSON response containing the votes for the poll.
    """
    poll = get_object_or_404(Poll, id=poll_id, is_active=True)
    votes = Vote.objects.filter(poll=poll).select_related("option", "user")

    data = []
    for vote in votes:
        vote_data = {
            "id": vote.id,
            "option_id": vote.option.id,
            "option_text": vote.option.text,
            "user_id": vote.user.id,
            "username": vote.user.username,
            "created_at": vote.created_at.isoformat(),
        }
        data.append(vote_data)

    return JsonResponse({"status": "success", "data": data})


def poll_list(request: HttpRequest) -> HttpResponse:
    """
    View for listing all active polls.

    Args:
        request: The HTTP request object.

    Returns:
        HttpResponse: A response containing the poll list page.
    """
    polls = Poll.objects.filter(is_active=True).prefetch_related("options", "votes")
    return render(request, "poller/poll_list.html", {"polls": polls})


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
        return render(request, "poller/poll_create.html")

    def post(self, request: HttpRequest) -> HttpResponse:
        """
        Handle POST requests to create a new poll.

        Args:
            request: The HTTP request object.

        Returns:
            HttpResponse: A response redirecting to the poll detail page or showing errors.
        """
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
                    geographical_scope_id=1,  # Default geographical scope
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
