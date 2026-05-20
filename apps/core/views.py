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
API views for the `core` app.

This module defines API views for interacting with decentralized identity and federated data.
These views provide endpoints for managing DIDs, verifiable credentials, and federated data.
"""

import datetime
import json
import uuid

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


from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import (
    ScopeType,
    Scope,
    CredentialType,
    CredentialIssuance,
    IssuerAuthorization,
)
from .serializers import (
    ScopeTypeSerializer,
    ScopeSerializer,
    CredentialTypeSerializer,
    CredentialIssuanceSerializer,
    IssuerAuthorizationSerializer,
    ScopeTypeListSerializer,
    ScopeListSerializer,
    CredentialIssueRequestSerializer,
    CredentialVerifyRequestSerializer,
)


class ScopeTypeViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing ScopeTypes.

    Provides CRUD operations for scope types.
    """

    queryset = ScopeType.objects.all()
    serializer_class = ScopeTypeSerializer

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = ScopeTypeListSerializer(queryset, many=True)
        return Response({"scope_types": serializer.data})

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response(serializer.data)


class ScopeViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing Scopes.

    Provides CRUD operations for scope instances.
    """

    queryset = Scope.objects.all()
    serializer_class = ScopeSerializer

    def get_queryset(self):
        queryset = Scope.objects.all()
        scope_type = self.request.query_params.get("scope_type")
        if scope_type:
            queryset = queryset.filter(scope_type__name=scope_type)
        return queryset

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = ScopeListSerializer(queryset, many=True)
        scope_type = request.query_params.get("scope_type", "all")
        return Response({"scope_type": scope_type, "scopes": serializer.data})


class CredentialTypeViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing CredentialTypes.

    Provides CRUD operations for credential types.
    """

    queryset = CredentialType.objects.all()
    serializer_class = CredentialTypeSerializer

    def get_queryset(self):
        queryset = CredentialType.objects.all()
        scope_type = self.request.query_params.get("scope_type")
        if scope_type:
            queryset = queryset.filter(scope_type__name=scope_type)
        return queryset


class CredentialIssuanceViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing CredentialIssuances.

    Provides CRUD operations for credential issuances.
    """

    queryset = CredentialIssuance.objects.all()
    serializer_class = CredentialIssuanceSerializer

    def get_queryset(self):
        queryset = CredentialIssuance.objects.all()
        holder_did = self.request.query_params.get("holder_did")
        issuer_did = self.request.query_params.get("issuer_did")
        credential_type = self.request.query_params.get("credential_type")

        if holder_did:
            queryset = queryset.filter(holder_did=holder_did)
        if issuer_did:
            queryset = queryset.filter(issuer_did=issuer_did)
        if credential_type:
            queryset = queryset.filter(credential_type__name=credential_type)

        return queryset


class IssuerAuthorizationViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing IssuerAuthorizations.

    Provides CRUD operations for issuer authorizations.
    """

    queryset = IssuerAuthorization.objects.all()
    serializer_class = IssuerAuthorizationSerializer

    def get_queryset(self):
        queryset = IssuerAuthorization.objects.all()
        issuer_did = self.request.query_params.get("issuer_did")
        scope = self.request.query_params.get("scope")

        if issuer_did:
            queryset = queryset.filter(issuer_did=issuer_did)
        if scope:
            queryset = queryset.filter(scope__value=scope)

        return queryset


class IssueCredentialAPIView(APIView):
    """
    API endpoint for issuing credentials.

    POST /api/credentials/issue/
    """

    def post(self, request):
        serializer = CredentialIssueRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {"error": "Validation error", "details": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )

        data = serializer.validated_data

        credential_type = CredentialType.objects.get(name=data["credential_type"])
        scope_type = ScopeType.objects.get(name=data["scope_type"])

        scope, created = Scope.objects.get_or_create(
            scope_type=scope_type,
            value=data["scope_value"],
            defaults={"is_active": True},
        )

        if not scope.is_active:
            scope.is_active = True
            scope.save()

        expires_at = None
        if data.get("expiration_days"):
            from datetime import timedelta

            expires_at = datetime.datetime.now() + timedelta(
                days=data["expiration_days"]
            )

        credential_data = {
            "@context": [
                "https://www.w3.org/2018/credentials/v1",
                "https://poly.example.com/credentials/v1",
            ],
            "id": f"urn:uuid:{uuid.uuid4()}",
            "type": ["VerifiableCredential", data["credential_type"]],
            "issuer": data.get("issuer_did", ""),
            "issuanceDate": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "expirationDate": expires_at.isoformat() if expires_at else None,
            "credentialSubject": {
                "id": data["holder_did"],
                "scope": {"type": data["scope_type"], "value": data["scope_value"]},
                "authorizationLevel": "standard",
            },
        }

        issuance = CredentialIssuance.objects.create(
            credential=credential_data,
            holder_did=data["holder_did"],
            issuer_did=data.get("issuer_did", ""),
            credential_type=credential_type,
            scope=scope,
            expires_at=expires_at,
            status="active",
        )

        return Response(
            {
                "credential": issuance.credential,
                "ipfs_cid": issuance.ipfs_cid or "",
                "blockchain_tx": issuance.blockchain_tx or "",
                "issuance_id": str(issuance.id),
                "status": issuance.status,
            },
            status=status.HTTP_201_CREATED,
        )


class VerifyCredentialAPIView(APIView):
    """
    API endpoint for verifying credentials.

    POST /api/credentials/verify/
    """

    def post(self, request):
        serializer = CredentialVerifyRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {"error": "Validation error", "details": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )

        data = serializer.validated_data
        credential = data.get("credential")

        verification_details = {
            "signature_valid": False,
            "issuer_authorized": False,
            "scope_matches": False,
            "not_expired": True,
            "issuer_trust_score": 0.0,
        }

        holder_did = credential.get("credentialSubject", {}).get("id")
        issuer_did = credential.get("issuer")

        if not holder_did or not issuer_did:
            return Response(
                {
                    "is_valid": False,
                    "verification_details": verification_details,
                    "can_vote": False,
                    "reason": "Invalid credential structure",
                }
            )

        scope = credential.get("credentialSubject", {}).get("scope", {})
        credential_scope_type = scope.get("type")
        credential_scope_value = scope.get("value")

        required_scope_type = data.get("required_scope_type")
        required_scope_value = data.get("required_scope_value")

        if required_scope_type and credential_scope_type != required_scope_type:
            verification_details["scope_matches"] = False
            return Response(
                {
                    "is_valid": False,
                    "verification_details": verification_details,
                    "can_vote": False,
                    "reason": f"Scope type mismatch: expected {required_scope_type}, got {credential_scope_type}",
                }
            )

        if required_scope_value and credential_scope_value != required_scope_value:
            verification_details["scope_matches"] = False
            return Response(
                {
                    "is_valid": False,
                    "verification_details": verification_details,
                    "can_vote": False,
                    "reason": f"Scope value mismatch: expected {required_scope_value}, got {credential_scope_value}",
                }
            )

        verification_details["scope_matches"] = True

        issuance = CredentialIssuance.objects.filter(
            holder_did=holder_did, issuer_did=issuer_did, status="active"
        ).first()

        if issuance:
            verification_details["issuer_authorized"] = True

            if issuance.expires_at:
                now = datetime.datetime.now(datetime.timezone.utc)
                if issuance.expires_at.tzinfo is None:
                    issuance.expires_at = issuance.expires_at.replace(
                        tzinfo=datetime.timezone.utc
                    )
                if issuance.expires_at < now:
                    verification_details["not_expired"] = False

        verification_details["signature_valid"] = True

        can_vote = (
            verification_details["signature_valid"]
            and verification_details["issuer_authorized"]
            and verification_details["scope_matches"]
            and verification_details["not_expired"]
        )

        return Response(
            {
                "is_valid": can_vote,
                "verification_details": verification_details,
                "can_vote": can_vote,
                "reason": None if can_vote else "Credential verification failed",
            }
        )


class GetCredentialsAPIView(APIView):
    """
    API endpoint for retrieving credentials for a holder.

    GET /api/credentials/?holder_did=<did>
    """

    def get(self, request):
        holder_did = request.query_params.get("holder_did")

        if not holder_did:
            return Response(
                {"error": "holder_did query parameter required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        issuances = CredentialIssuance.objects.filter(
            holder_did=holder_did, status="active"
        )

        credentials = []
        for issuance in issuances:
            credentials.append(
                {
                    "id": issuance.id,
                    "credential": issuance.credential,
                    "issuer_did": issuance.issuer_did,
                    "credential_type": issuance.credential_type.name,
                    "scope": {
                        "type": issuance.scope.scope_type.name,
                        "value": issuance.scope.value,
                    },
                    "issued_at": issuance.issued_at.isoformat(),
                    "expires_at": issuance.expires_at.isoformat()
                    if issuance.expires_at
                    else None,
                }
            )

        return Response({"holder_did": holder_did, "credentials": credentials})


from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.models import (
    FederatedNode,
    FederatedData,
    SyncMessage,
    DataSyncLog,
)
from apps.core.serializers import (
    FederatedNodeSerializer,
    FederatedDataSerializer,
    SyncMessageSerializer,
    SyncMessageCreateSerializer,
    DataSyncLogSerializer,
    SyncRequestSerializer,
    AnnounceRequestSerializer,
)


class FederatedNodeViewSet(viewsets.ModelViewSet):
    """ViewSet for managing federated nodes."""

    queryset = FederatedNode.objects.all()
    serializer_class = FederatedNodeSerializer
    lookup_field = "name"

    def get_queryset(self):
        queryset = FederatedNode.objects.all()
        is_active = self.request.query_params.get("is_active")
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active.lower() == "true")
        return queryset

    @action(detail=True, methods=["post"])
    def sync(self, request, name=None):
        """Sync data with this node."""
        node = self.get_object()
        serializer = SyncRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {"error": "Validation error", "details": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )

        since_version = serializer.validated_data.get("since_version", 0)
        data_types = serializer.validated_data.get("data_types", None)

        queryset = FederatedData.objects.filter(version__gt=since_version).order_by(
            "version"
        )[:1000]

        if data_types:
            queryset = queryset.filter(data_type__in=data_types)

        serializer = FederatedDataSerializer(queryset, many=True)
        return Response(
            {
                "data": serializer.data,
                "latest_version": queryset.last().version
                if queryset.exists()
                else since_version,
            }
        )

    @action(detail=True, methods=["post"])
    def announce(self, request, name=None):
        """Announce new data to this node."""
        node = self.get_object()
        serializer = AnnounceRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {"error": "Validation error", "details": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )

        data = serializer.validated_data

        message = SyncMessage.objects.create(
            message_type=data["message_type"],
            sender_node=node,
            sender_endpoint=data.get("sender_endpoint", ""),
            payload=data["payload"],
            previous_hash=data.get("previous_hash", ""),
            signature=data.get("signature", ""),
        )

        self.process_announce(message)

        return Response({"status": "announced", "message_id": str(message.message_id)})

    def process_announce(self, message: SyncMessage):
        """Process an announce message and store the data."""
        payload = message.payload
        data_type = payload.get("data_type")
        data_id = payload.get("data_id")
        data = payload.get("data", {})
        version = payload.get("version", 1)

        if not all([data_type, data_id]):
            message.is_processed = True
            message.save(update_fields=["is_processed"])
            return

        existing = FederatedData.objects.filter(
            node=message.sender_node, data_type=data_type, data_id=data_id
        ).first()

        if existing:
            if version > existing.version:
                existing.data = data
                existing.version = version
                existing.save(update_fields=["data", "version"])
                DataSyncLog.objects.create(
                    source_node=message.sender_node,
                    target_node=message.sender_node,
                    data_type=data_type,
                    data_id=data_id,
                    version=version,
                    status="conflict",
                    details="Updated with higher version",
                )
        else:
            FederatedData.objects.create(
                node=message.sender_node,
                data_type=data_type,
                data_id=data_id,
                data=data,
                version=version,
            )

        message.is_processed = True
        message.save(update_fields=["is_processed"])

    @action(detail=True, methods=["get"])
    def peers(self, request, name=None):
        """Get list of active peer nodes."""
        node = self.get_object()
        peers = FederatedNode.objects.filter(is_active=True).exclude(name=node.name)
        serializer = FederatedNodeSerializer(peers, many=True)
        return Response({"peers": serializer.data})


class DataSyncView(APIView):
    """View for handling data synchronization between nodes."""

    def get(self, request):
        """Get all data since version."""
        since = int(request.query_params.get("since", 0))
        data_types = request.query_params.getlist("data_types")

        queryset = FederatedData.objects.filter(version__gt=since).order_by("version")

        if data_types:
            queryset = queryset.filter(data_type__in=data_types)

        latest_version = since
        items = list(queryset[:500])
        if items:
            latest_version = items[-1].version

        serializer = FederatedDataSerializer(items, many=True)
        return Response(
            {
                "items": serializer.data,
                "latest_version": latest_version,
            }
        )

    def post(self, request):
        """Push data to the network."""
        node_name = request.data.get("node_name")
        if not node_name:
            return Response(
                {"error": "node_name required"}, status=status.HTTP_400_BAD_REQUEST
            )

        try:
            node = FederatedNode.objects.get(name=node_name, is_active=True)
        except FederatedNode.DoesNotExist:
            return Response(
                {"error": "Node not found or inactive"},
                status=status.HTTP_404_NOT_FOUND,
            )

        data_type = request.data.get("data_type")
        data_id = request.data.get("data_id")
        data = request.data.get("data", {})
        version = request.data.get("version", 1)

        federated_data, created = FederatedData.objects.update_or_create(
            node=node,
            data_type=data_type,
            data_id=data_id,
            defaults={"data": data, "version": version},
        )

        return Response(
            {
                "status": "synced",
                "data_type": data_type,
                "data_id": data_id,
                "version": federated_data.version,
                "created": created,
            }
        )


class SyncMessagesViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for viewing sync messages."""

    queryset = SyncMessage.objects.all()
    serializer_class = SyncMessageSerializer

    def get_queryset(self):
        queryset = SyncMessage.objects.all()
        message_type = self.request.query_params.get("message_type")
        is_processed = self.request.query_params.get("is_processed")
        sender = self.request.query_params.get("sender")

        if message_type:
            queryset = queryset.filter(message_type=message_type)
        if is_processed is not None:
            queryset = queryset.filter(is_processed=is_processed.lower() == "true")
        if sender:
            queryset = queryset.filter(sender_node__name=sender)

        return queryset[:1000]


class DataSyncLogViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for viewing sync logs."""

    queryset = DataSyncLog.objects.all()
    serializer_class = DataSyncLogSerializer

    def get_queryset(self):
        queryset = DataSyncLog.objects.all()
        status_filter = self.request.query_params.get("status")
        source = self.request.query_params.get("source")
        target = self.request.query_params.get("target")

        if status_filter:
            queryset = queryset.filter(status=status_filter)
        if source:
            queryset = queryset.filter(source_node__name=source)
        if target:
            queryset = queryset.filter(target_node__name=target)

        return queryset[:500]


from apps.core.models import IssuerMetrics, IssuerEndorsement
from apps.core.serializers import (
    IssuerMetricsSerializer,
    IssuerMetricsCreateSerializer,
    IssuerEndorsementSerializer,
    IssuerEndorsementCreateSerializer,
    TrustScoreRequestSerializer,
    TrustScoreResponseSerializer,
)
from apps.core.utils import TrustScorer, TRUST_THRESHOLDS


class IssuerMetricsViewSet(viewsets.ModelViewSet):
    """ViewSet for managing issuer metrics."""

    queryset = IssuerMetrics.objects.all()
    serializer_class = IssuerMetricsSerializer

    def get_serializer_class(self):
        if self.action == "create":
            return IssuerMetricsCreateSerializer
        return IssuerMetricsSerializer

    def get_queryset(self):
        queryset = IssuerMetrics.objects.all()
        issuer_did = self.request.query_params.get("issuer_did")
        scope_value = self.request.query_params.get("scope_value")

        if issuer_did:
            queryset = queryset.filter(issuer_did=issuer_did)
        if scope_value:
            queryset = queryset.filter(scope__value=scope_value)

        return queryset


class IssuerEndorsementViewSet(viewsets.ModelViewSet):
    """ViewSet for managing issuer endorsements."""

    queryset = IssuerEndorsement.objects.all()
    serializer_class = IssuerEndorsementSerializer

    def get_serializer_class(self):
        if self.action == "create":
            return IssuerEndorsementCreateSerializer
        return IssuerEndorsementSerializer

    def get_queryset(self):
        queryset = IssuerEndorsement.objects.all()
        endorser = self.request.query_params.get("endorser_did")
        endorsed = self.request.query_params.get("endorsed_issuer_did")
        is_positive = self.request.query_params.get("is_positive")

        if endorser:
            queryset = queryset.filter(endorser_did=endorser)
        if endorsed:
            queryset = queryset.filter(endorsed_issuer_did=endorsed)
        if is_positive is not None:
            queryset = queryset.filter(is_positive=is_positive.lower() == "true")

        return queryset

    @action(detail=True, methods=["post"])
    def toggle(self, request, pk=None):
        """Toggle endorsement active status."""
        endorsement = self.get_object()
        endorsement.is_active = not endorsement.is_active
        endorsement.save(update_fields=["is_active"])
        serializer = self.get_serializer(endorsement)
        return Response(serializer.data)


class GetTrustScoreAPIView(APIView):
    """API endpoint for getting trust score of an issuer."""

    def get(self, request):
        """Get trust score for an issuer."""
        issuer_did = request.query_params.get("issuer_did")
        scope_value = request.query_params.get("scope_value")
        scope_type = request.query_params.get("scope_type")
        threshold = request.query_params.get("threshold", "medium")

        if not issuer_did or not scope_value:
            return Response(
                {"error": "issuer_did and scope_value query parameters required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            scope = Scope.objects.get(value=scope_value)
            if scope_type and scope.scope_type.name != scope_type:
                return Response(
                    {"error": f"Scope does not match scope_type '{scope_type}'"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        except Scope.DoesNotExist:
            return Response(
                {"error": f"Scope '{scope_value}' not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        metrics = IssuerMetrics.objects.filter(
            issuer_did=issuer_did, scope=scope
        ).first()

        if not metrics:
            return Response(
                {
                    "issuer_did": issuer_did,
                    "scope": scope_value,
                    "trust_score": 0.0,
                    "trust_level": "low",
                    "meets_threshold": False,
                    "threshold": threshold,
                    "metrics": None,
                    "message": "No metrics found for this issuer",
                }
            )

        score = TrustScorer.calculate_score(metrics)
        meets_threshold = score >= TRUST_THRESHOLDS.get(threshold, 0.0)

        metrics_serializer = IssuerMetricsSerializer(metrics)

        return Response(
            {
                "issuer_did": issuer_did,
                "scope": scope_value,
                "trust_score": score,
                "trust_level": TrustScorer.get_trust_level(score),
                "meets_threshold": meets_threshold,
                "threshold": threshold,
                "threshold_value": TRUST_THRESHOLDS.get(threshold, 0.0),
                "metrics": metrics_serializer.data,
            }
        )


class CheckIssuerTrustAPIView(APIView):
    """API endpoint for checking if an issuer meets trust threshold."""

    def post(self, request):
        """Check if issuer meets trust threshold for voting."""
        serializer = TrustScoreRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {"error": "Validation error", "details": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )

        data = serializer.validated_data
        issuer_did = data["issuer_did"]
        scope_value = data["scope_value"]
        threshold = data.get("threshold", "medium")

        try:
            scope = Scope.objects.get(value=scope_value)
        except Scope.DoesNotExist:
            return Response(
                {"eligible": False, "reason": f"Scope '{scope_value}' not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        metrics = IssuerMetrics.objects.filter(
            issuer_did=issuer_did, scope=scope
        ).first()

        if not metrics:
            return Response(
                {
                    "eligible": False,
                    "reason": f"No trust metrics found for issuer {issuer_did}",
                    "trust_score": 0.0,
                }
            )

        score = TrustScorer.calculate_score(metrics)
        threshold_value = TRUST_THRESHOLDS.get(threshold, 0.0)

        if score >= threshold_value:
            return Response(
                {
                    "eligible": True,
                    "trust_score": score,
                    "trust_level": TrustScorer.get_trust_level(score),
                    "threshold": threshold,
                }
            )
        else:
            return Response(
                {
                    "eligible": False,
                    "reason": f"Trust score {score:.2f} below threshold {threshold_value}",
                    "trust_score": score,
                    "threshold": threshold,
                }
            )
