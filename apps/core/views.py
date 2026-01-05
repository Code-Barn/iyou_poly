"""
API views for the `core` app.

This module defines API views for interacting with decentralized identity and federated data.
These views provide endpoints for managing DIDs, verifiable credentials, and federated data.
"""

import json

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from apps.core.models import (
    DID,
    DIDDocument,
    FederatedData,
    FederatedNode,
)


@csrf_exempt
@require_http_methods(["GET", "POST"])
def federated_data_api(request, node_name=None):
    """
    API endpoint for managing federated data.

    Args:
        request: The HTTP request object.
        node_name: The name of the federated node (optional).

    Returns:
        JsonResponse: A JSON response containing the result of the API call.
    """
    if request.method == "GET":
        return get_federated_data(request, node_name)
    elif request.method == "POST":
        return create_federated_data(request, node_name)


@csrf_exempt
@require_http_methods(["GET", "PUT", "DELETE"])
def federated_data_detail_api(request, node_name, data_type, data_id):
    """
    API endpoint for managing a specific federated data entry.

    Args:
        request: The HTTP request object.
        node_name: The name of the federated node.
        data_type: The type of data (e.g., 'poll', 'user_profile').
        data_id: The unique identifier for the data.

    Returns:
        JsonResponse: A JSON response containing the result of the API call.
    """
    if request.method == "GET":
        return get_federated_data_detail(request, node_name, data_type, data_id)
    elif request.method == "PUT":
        return update_federated_data(request, node_name, data_type, data_id)
    elif request.method == "DELETE":
        return delete_federated_data(request, node_name, data_type, data_id)


def get_federated_data(request, node_name=None):
    """
    Retrieve federated data for a node or across all nodes.

    Args:
        request: The HTTP request object.
        node_name: The name of the federated node (optional).

    Returns:
        JsonResponse: A JSON response containing the federated data.
    """
    try:
        if node_name:
            node = FederatedNode.objects.get(name=node_name, is_active=True)
            data = FederatedData.objects.filter(node=node, is_active=True)
        else:
            data = FederatedData.objects.filter(is_active=True)

        data_list = [
            {
                "node": item.node.name,
                "data_type": item.data_type,
                "data_id": item.data_id,
                "data": item.data,
                "version": item.version,
                "created_at": item.created_at.isoformat(),
                "updated_at": item.updated_at.isoformat(),
            }
            for item in data
        ]

        return JsonResponse({"status": "success", "data": data_list})
    except FederatedNode.DoesNotExist:
        return JsonResponse(
            {"status": "error", "message": "Node not found or inactive."}, status=404
        )
    except Exception as e:
        return JsonResponse({"status": "error", "message": str(e)}, status=500)


def create_federated_data(request, node_name):
    """
    Create a new federated data entry.

    Args:
        request: The HTTP request object.
        node_name: The name of the federated node.

    Returns:
        JsonResponse: A JSON response containing the result of the API call.
    """
    try:
        node = FederatedNode.objects.get(name=node_name, is_active=True)
        data = json.loads(request.body)

        federated_data = FederatedData.objects.create(
            node=node,
            data_type=data.get("data_type"),
            data_id=data.get("data_id"),
            data=data.get("data", {}),
        )

        return JsonResponse(
            {
                "status": "success",
                "message": "Federated data created successfully.",
                "data": {
                    "node": federated_data.node.name,
                    "data_type": federated_data.data_type,
                    "data_id": federated_data.data_id,
                    "version": federated_data.version,
                },
            },
            status=201,
        )
    except FederatedNode.DoesNotExist:
        return JsonResponse(
            {"status": "error", "message": "Node not found or inactive."}, status=404
        )
    except Exception as e:
        return JsonResponse({"status": "error", "message": str(e)}, status=500)


def get_federated_data_detail(request, node_name, data_type, data_id):
    """
    Retrieve a specific federated data entry.

    Args:
        request: The HTTP request object.
        node_name: The name of the federated node.
        data_type: The type of data.
        data_id: The unique identifier for the data.

    Returns:
        JsonResponse: A JSON response containing the federated data.
    """
    try:
        node = FederatedNode.objects.get(name=node_name, is_active=True)
        data = FederatedData.objects.get(
            node=node, data_type=data_type, data_id=data_id, is_active=True
        )

        return JsonResponse(
            {
                "status": "success",
                "data": {
                    "node": data.node.name,
                    "data_type": data.data_type,
                    "data_id": data.data_id,
                    "data": data.data,
                    "version": data.version,
                    "created_at": data.created_at.isoformat(),
                    "updated_at": data.updated_at.isoformat(),
                },
            }
        )
    except FederatedNode.DoesNotExist:
        return JsonResponse(
            {"status": "error", "message": "Node not found or inactive."}, status=404
        )
    except FederatedData.DoesNotExist:
        return JsonResponse(
            {"status": "error", "message": "Data not found or inactive."}, status=404
        )
    except Exception as e:
        return JsonResponse({"status": "error", "message": str(e)}, status=500)


def update_federated_data(request, node_name, data_type, data_id):
    """
    Update a specific federated data entry.

    Args:
        request: The HTTP request object.
        node_name: The name of the federated node.
        data_type: The type of data.
        data_id: The unique identifier for the data.

    Returns:
        JsonResponse: A JSON response containing the result of the API call.
    """
    try:
        node = FederatedNode.objects.get(name=node_name, is_active=True)
        data = FederatedData.objects.get(
            node=node, data_type=data_type, data_id=data_id, is_active=True
        )

        request_data = json.loads(request.body)
        data.data = request_data.get("data", data.data)
        # Version is incremented in the signal, so we don't increment it here
        data.save(update_fields=["data"])

        return JsonResponse(
            {
                "status": "success",
                "message": "Federated data updated successfully.",
                "data": {
                    "node": data.node.name,
                    "data_type": data.data_type,
                    "data_id": data.data_id,
                    "version": data.version,
                },
            }
        )
    except FederatedNode.DoesNotExist:
        return JsonResponse(
            {"status": "error", "message": "Node not found or inactive."}, status=404
        )
    except FederatedData.DoesNotExist:
        return JsonResponse(
            {"status": "error", "message": "Data not found or inactive."}, status=404
        )
    except Exception as e:
        return JsonResponse({"status": "error", "message": str(e)}, status=500)


def delete_federated_data(request, node_name, data_type, data_id):
    """
    Delete a specific federated data entry.

    Args:
        request: The HTTP request object.
        node_name: The name of the federated node.
        data_type: The type of data.
        data_id: The unique identifier for the data.

    Returns:
        JsonResponse: A JSON response containing the result of the API call.
    """
    try:
        node = FederatedNode.objects.get(name=node_name, is_active=True)
        data = FederatedData.objects.get(
            node=node, data_type=data_type, data_id=data_id, is_active=True
        )

        data.is_active = False
        data.save()

        return JsonResponse(
            {
                "status": "success",
                "message": "Federated data deleted successfully.",
                "data": {
                    "node": data.node.name,
                    "data_type": data.data_type,
                    "data_id": data.data_id,
                },
            }
        )
    except FederatedNode.DoesNotExist:
        return JsonResponse(
            {"status": "error", "message": "Node not found or inactive."}, status=404
        )
    except FederatedData.DoesNotExist:
        return JsonResponse(
            {"status": "error", "message": "Data not found or inactive."}, status=404
        )
    except Exception as e:
        return JsonResponse({"status": "error", "message": str(e)}, status=500)


@csrf_exempt
@require_http_methods(["GET"])
def did_api(request, did_uri=None):
    """
    API endpoint for retrieving DID and DID Document information.

    Args:
        request: The HTTP request object.
        did_uri: The DID URI (optional).

    Returns:
        JsonResponse: A JSON response containing the DID and DID Document.
    """
    if did_uri:
        return get_did_detail(request, did_uri)
    else:
        return get_all_dids(request)


def get_all_dids(request):
    """
    Retrieve all DIDs.

    Args:
        request: The HTTP request object.

    Returns:
        JsonResponse: A JSON response containing all DIDs.
    """
    try:
        dids = DID.objects.filter(is_active=True)
        did_list = [
            {
                "did_uri": did.did_uri,
                "user": did.user.username,
                "method": did.method.name,
                "is_primary": did.is_primary,
                "created_at": did.created_at.isoformat(),
            }
            for did in dids
        ]

        return JsonResponse({"status": "success", "data": did_list})
    except Exception as e:
        return JsonResponse({"status": "error", "message": str(e)}, status=500)


def get_did_detail(request, did_uri):
    """
    Retrieve a specific DID and its DID Document.

    Args:
        request: The HTTP request object.
        did_uri: The DID URI.

    Returns:
        JsonResponse: A JSON response containing the DID and DID Document.
    """
    try:
        did = DID.objects.get(did_uri=did_uri, is_active=True)
        did_document = DIDDocument.objects.get(did=did)

        return JsonResponse(
            {
                "status": "success",
                "data": {
                    "did_uri": did.did_uri,
                    "user": did.user.username,
                    "method": did.method.name,
                    "is_primary": did.is_primary,
                    "did_document": did_document.document,
                    "created_at": did.created_at.isoformat(),
                    "updated_at": did.updated_at.isoformat(),
                },
            }
        )
    except DID.DoesNotExist:
        return JsonResponse(
            {"status": "error", "message": "DID not found or inactive."}, status=404
        )
    except DIDDocument.DoesNotExist:
        return JsonResponse(
            {"status": "error", "message": "DID Document not found."}, status=404
        )
    except Exception as e:
        return JsonResponse({"status": "error", "message": str(e)}, status=500)
