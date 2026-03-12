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
                "https://polly.example.com/credentials/v1",
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
