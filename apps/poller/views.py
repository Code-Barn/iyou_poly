"""
Views for the `poller` app.

This module defines views for rendering polls, managing poll-related functionality,
and creating polls in the Polly project. It includes both API views and template views
for server-side rendering.

"""

import logging

from django.shortcuts import redirect, render

logger = logging.getLogger(__name__)

import json

from django.contrib.auth import get_user_model
from django.http import JsonResponse
from django.shortcuts import render
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from apps.poller.models import GeographicalScope, Poll, PollOption, Vote

User = get_user_model()


@csrf_exempt
@require_http_methods(["GET", "POST"])
def poll_api(request):
    """
    API endpoint for managing polls.

    Args:
        request: The HTTP request object.

    Returns:
        JsonResponse: A JSON response containing the result of the API call.
    """
    if request.method == "GET":
        return get_polls(request)
    elif request.method == "POST":
        return create_poll(request)


@csrf_exempt
@require_http_methods(["GET", "PUT", "DELETE"])
def poll_detail_api(request, poll_id):
    """
    API endpoint for managing a specific poll.

    Args:
        request: The HTTP request object.
        poll_id: The ID of the poll.

    Returns:
        JsonResponse: A JSON response containing the result of the API call.
    """
    if request.method == "GET":
        return get_poll_detail(request, poll_id)
    elif request.method == "PUT":
        return update_poll(request, poll_id)
    elif request.method == "DELETE":
        return delete_poll(request, poll_id)


@csrf_exempt
@require_http_methods(["POST"])
def vote_api(request, poll_id):
    """
    API endpoint for casting a vote in a poll.

    Args:
        request: The HTTP request object.
        poll_id: The ID of the poll.

    Returns:
        JsonResponse: A JSON response containing the result of the API call.
    """
    logger.debug(f"Vote API called for poll_id: {poll_id}")
    logger.debug(f"Request method: {request.method}")
    logger.debug(f"Request headers: {request.headers}")
    logger.debug(f"User authenticated: {request.user.is_authenticated}")
    logger.debug(f"User: {request.user}")

    # Handle JSON data
    if request.content_type == "application/json":
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error: {e}")
            return JsonResponse(
                {"status": "error", "message": "Invalid JSON data."},
                status=400,
            )
    else:
        data = request.POST

    return cast_vote(request, poll_id, data)

    # Handle form data or JSON data
    if request.content_type == "application/json":
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error: {e}")
            return JsonResponse(
                {"status": "error", "message": "Invalid JSON data."},
                status=400,
            )
    else:
        data = request.POST

    logger.debug(f"Request data: {data}")
    response = cast_vote(request, poll_id, data)

    # If the vote was successful, return the updated vote results
    if response.status_code == 200:
        poll = Poll.objects.prefetch_related("options", "votes").get(
            id=poll_id, is_active=True
        )
        return render(request, "poller/partials/vote_results.html", {"poll": poll})

    return response


@csrf_exempt
@require_http_methods(["GET"])
def vote_detail_api(request, poll_id):
    """
    API endpoint for retrieving votes for a poll.

    Args:
        request: The HTTP request object.
        poll_id: The ID of the poll.

    Returns:
        JsonResponse: A JSON response containing the votes for the poll.
    """
    return get_votes(request, poll_id)


def get_polls(request):
    """
    Retrieve all active polls.

    Args:
        request: The HTTP request object.

    Returns:
        JsonResponse: A JSON response containing the list of polls.
    """
    try:
        geographical_scope = request.GET.get("geographical_scope")
        if geographical_scope:
            polls = Poll.objects.filter(
                is_active=True,
                geographical_scope__name=geographical_scope,
            )
        else:
            polls = Poll.objects.filter(is_active=True)

        poll_list = [
            {
                "id": poll.id,
                "title": poll.title,
                "description": poll.description,
                "created_by": poll.created_by.username,
                "geographical_scope": poll.geographical_scope.name,
                "is_active": poll.is_active,
                "created_at": poll.created_at.isoformat(),
                "updated_at": poll.updated_at.isoformat(),
                "options": [
                    {"id": option.id, "text": option.text, "votes": option.votes}
                    for option in poll.options.all()
                ],
            }
            for poll in polls
        ]

        return JsonResponse({"status": "success", "data": poll_list})
    except Exception as e:
        return JsonResponse({"status": "error", "message": str(e)}, status=500)


def create_poll(request):
    """
    Create a new poll.

    Args:
        request: The HTTP request object.

    Returns:
        JsonResponse: A JSON response containing the created poll.
    """
    try:
        data = json.loads(request.body)
        user = request.user if request.user.is_authenticated else None
        if not user:
            return JsonResponse(
                {"status": "error", "message": "Authentication required."}, status=401
            )

        geographical_scope = GeographicalScope.objects.get(
            name=data.get("geographical_scope", "local")
        )
        poll = Poll.objects.create(
            title=data.get("title"),
            description=data.get("description", ""),
            created_by=user,
            geographical_scope=geographical_scope,
            is_active=data.get("is_active", True),
        )

        options = data.get("options", [])
        for option_text in options:
            PollOption.objects.create(poll=poll, text=option_text)

        return JsonResponse(
            {
                "status": "success",
                "message": "Poll created successfully.",
                "data": {
                    "id": poll.id,
                    "title": poll.title,
                    "description": poll.description,
                    "created_by": poll.created_by.username,
                    "geographical_scope": poll.geographical_scope.name,
                    "is_active": poll.is_active,
                },
            },
            status=201,
        )
    except GeographicalScope.DoesNotExist:
        return JsonResponse(
            {"status": "error", "message": "Geographical scope not found."}, status=404
        )
    except Exception as e:
        return JsonResponse({"status": "error", "message": str(e)}, status=500)


def get_poll_detail(request, poll_id):
    """
    Retrieve a specific poll.

    Args:
        request: The HTTP request object.
        poll_id: The ID of the poll.

    Returns:
        JsonResponse: A JSON response containing the poll details.
    """
    try:
        poll = Poll.objects.get(id=poll_id, is_active=True)
        poll_data = {
            "id": poll.id,
            "title": poll.title,
            "description": poll.description,
            "created_by": poll.created_by.username,
            "geographical_scope": poll.geographical_scope.name,
            "is_active": poll.is_active,
            "created_at": poll.created_at.isoformat(),
            "updated_at": poll.updated_at.isoformat(),
            "options": [
                {"id": option.id, "text": option.text, "votes": option.votes}
                for option in poll.options.all()
            ],
        }

        return JsonResponse({"status": "success", "data": poll_data})
    except Poll.DoesNotExist:
        return JsonResponse(
            {"status": "error", "message": "Poll not found or inactive."}, status=404
        )
    except Exception as e:
        return JsonResponse({"status": "error", "message": str(e)}, status=500)


def update_poll(request, poll_id):
    """
    Update a specific poll.

    Args:
        request: The HTTP request object.
        poll_id: The ID of the poll.

    Returns:
        JsonResponse: A JSON response containing the updated poll.
    """
    try:
        poll = Poll.objects.get(id=poll_id, is_active=True)
        data = json.loads(request.body)

        if "title" in data:
            poll.title = data["title"]
        if "description" in data:
            poll.description = data["description"]
        if "is_active" in data:
            poll.is_active = data["is_active"]
        if "geographical_scope" in data:
            geographical_scope = GeographicalScope.objects.get(
                name=data["geographical_scope"]
            )
            poll.geographical_scope = geographical_scope

        poll.save()

        if "options" in data:
            # Clear existing options and add new ones
            poll.options.all().delete()
            for option_text in data["options"]:
                PollOption.objects.create(poll=poll, text=option_text)

        return JsonResponse(
            {
                "status": "success",
                "message": "Poll updated successfully.",
                "data": {
                    "id": poll.id,
                    "title": poll.title,
                    "description": poll.description,
                    "geographical_scope": poll.geographical_scope.name,
                    "is_active": poll.is_active,
                },
            }
        )
    except Poll.DoesNotExist:
        return JsonResponse(
            {"status": "error", "message": "Poll not found or inactive."}, status=404
        )
    except GeographicalScope.DoesNotExist:
        return JsonResponse(
            {"status": "error", "message": "Geographical scope not found."}, status=404
        )
    except Exception as e:
        return JsonResponse({"status": "error", "message": str(e)}, status=500)


def delete_poll(request, poll_id):
    """
    Delete a specific poll.

    Args:
        request: The HTTP request object.
        poll_id: The ID of the poll.

    Returns:
        JsonResponse: A JSON response confirming the deletion.
    """
    try:
        poll = Poll.objects.get(id=poll_id, is_active=True)
        poll.is_active = False
        poll.save()

        return JsonResponse(
            {
                "status": "success",
                "message": "Poll deleted successfully.",
                "data": {"id": poll.id, "title": poll.title},
            }
        )
    except Poll.DoesNotExist:
        return JsonResponse(
            {"status": "error", "message": "Poll not found or inactive."}, status=404
        )
    except Exception as e:
        return JsonResponse({"status": "error", "message": str(e)}, status=500)


def cast_vote(request, poll_id, data):
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
        user = request.user if request.user.is_authenticated else None
        if not user:
            logger.debug("User not authenticated")
            return JsonResponse(
                {"status": "error", "message": "You must be logged in to vote."},
                status=401,
            )

        # Handle both form data and JSON data
        if isinstance(data, dict):
            option_id = data.get("option_id")
        else:
            option_id = data.get("option_id") or json.loads(data).get("option_id")

        if not option_id:
            return JsonResponse(
                {"status": "error", "message": "Option ID is required."}, status=400
            )

        poll = Poll.objects.get(id=poll_id, is_active=True)
        option = PollOption.objects.get(id=option_id, poll=poll)

        # Check if the user has already voted in this poll
        if Vote.objects.filter(poll=poll, user=user).exists():
            return JsonResponse(
                {"status": "error", "message": "You have already voted in this poll."},
                status=400,
            )

        # Create the vote
        Vote.objects.create(poll=poll, option=option, user=user)

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
    except PollOption.DoesNotExist:
        return JsonResponse(
            {"status": "error", "message": "Option not found."}, status=404
        )
    except Exception as e:
        return JsonResponse({"status": "error", "message": str(e)}, status=500)


def get_votes(request, poll_id):
    """
    Retrieve all votes for a poll.

    Args:
        request: The HTTP request object.
        poll_id: The ID of the poll.

    Returns:
        JsonResponse: A JSON response containing the votes for the poll.
    """
    try:
        poll = Poll.objects.get(id=poll_id, is_active=True)
        votes = Vote.objects.filter(poll=poll)

        vote_list = [
            {
                "id": vote.id,
                "poll_id": vote.poll.id,
                "option_id": vote.option.id,
                "user": vote.user.username,
                "created_at": vote.created_at.isoformat(),
            }
            for vote in votes
        ]

        return JsonResponse({"status": "success", "data": vote_list})
    except Poll.DoesNotExist:
        return JsonResponse(
            {"status": "error", "message": "Poll not found or inactive."}, status=404
        )
    except Exception as e:
        return JsonResponse({"status": "error", "message": str(e)}, status=500)


def poll_list(request):
    """
    Render a list of active polls.

    Args:
        request: The HTTP request object.

    Returns:
        HttpResponse: A rendered template response containing the list of polls.
    """
    polls = Poll.objects.filter(is_active=True).prefetch_related("options", "votes")
    return render(request, "poller/poll_list.html", {"polls": polls})


class CreatePollView(View):
    """
    View for creating a new poll.

    This view handles the creation of new polls by rendering a form and processing
    the form submission.
    """

    def get(self, request):
        """Render the poll creation form."""
        if not request.user.is_authenticated:
            return redirect("login")
        return render(request, "poller/poll_create.html")

    def post(self, request):
        """Process the poll creation form submission."""
        if not request.user.is_authenticated:
            return redirect("login")

        title = request.POST.get("title")
        description = request.POST.get("description")
        options = request.POST.get("options").split("\n")

        if not title or not options:
            return render(
                request,
                "poller/poll_create.html",
                {"error": "Title and options are required."},
            )

        poll = Poll.objects.create(
            title=title,
            description=description,
            created_by=request.user,
            geographical_scope=GeographicalScope.objects.get(name="local"),
        )

        for option_text in options:
            if option_text.strip():
                PollOption.objects.create(poll=poll, text=option_text.strip())

        return redirect("poll_detail", poll_id=poll.id)


def poll_detail(request, poll_id):
    """
    Render a single poll and its voting options.

    Args:
        request: The HTTP request object.
        poll_id: The ID of the poll to render.

    Returns:
        HttpResponse: A rendered template response containing the poll details.
    """
    try:
        poll = Poll.objects.prefetch_related("options", "votes").get(
            id=poll_id, is_active=True
        )
        user_vote = None
        if request.user.is_authenticated:
            user_vote = Vote.objects.filter(poll=poll, user=request.user).first()
        return render(
            request,
            "poller/poll_detail.html",
            {
                "poll": poll,
                "user_vote": user_vote,
            },
        )
    except Poll.DoesNotExist:
        return render(request, "poller/poll_not_found.html", status=404)
