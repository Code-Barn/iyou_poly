"""
API views for the `poller` app.

This module defines API views for managing polls and votes in the Polly project.
These views provide endpoints for creating, retrieving, updating, and deleting polls,
as well as casting and retrieving votes.
"""

import json

from django.contrib.auth import get_user_model
from django.core.exceptions import ObjectDoesNotExist
from django.http import JsonResponse
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
    return cast_vote(request, poll_id)


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


def cast_vote(request, poll_id):
    """
    Cast a vote in a poll.

    Args:
        request: The HTTP request object.
        poll_id: The ID of the poll.

    Returns:
        JsonResponse: A JSON response confirming the vote.
    """
    try:
        user = request.user if request.user.is_authenticated else None
        if not user:
            return JsonResponse(
                {"status": "error", "message": "Authentication required."}, status=401
            )

        data = json.loads(request.body)
        option_id = data.get("option_id")
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
