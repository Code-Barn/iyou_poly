"""
URL configuration for the `core` app.

This module defines the URL routes for the API endpoints provided by the `core` app,
including endpoints for managing decentralized identity and federated data.
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter

from apps.core.views import (
    did_api,
    federated_data_api,
    federated_data_detail_api,
    ScopeTypeViewSet,
    ScopeViewSet,
    CredentialTypeViewSet,
    CredentialIssuanceViewSet,
    IssuerAuthorizationViewSet,
    IssueCredentialAPIView,
    VerifyCredentialAPIView,
    GetCredentialsAPIView,
)

router = DefaultRouter()
router.register(r"scope-types", ScopeTypeViewSet)
router.register(r"scopes", ScopeViewSet)
router.register(r"credential-types", CredentialTypeViewSet)
router.register(r"credential-issuances", CredentialIssuanceViewSet)
router.register(r"issuer-authorizations", IssuerAuthorizationViewSet)

urlpatterns = [
    # Federated Data API
    path(
        "api/federated-data/",
        federated_data_api,
        name="federated_data_api",
    ),
    path(
        "api/federated-data/<str:node_name>/",
        federated_data_api,
        name="federated_data_api_node",
    ),
    path(
        "api/federated-data/<str:node_name>/<str:data_type>/<str:data_id>/",
        federated_data_detail_api,
        name="federated_data_detail_api",
    ),
    # DID API
    path(
        "api/dids/",
        did_api,
        name="did_api",
    ),
    path(
        "api/dids/<str:did_uri>/",
        did_api,
        name="did_detail_api",
    ),
    # Scope and Credential APIs
    path("api/", include(router.urls)),
    path(
        "api/credentials/issue/",
        IssueCredentialAPIView.as_view(),
        name="issue_credential",
    ),
    path(
        "api/credentials/verify/",
        VerifyCredentialAPIView.as_view(),
        name="verify_credential",
    ),
    path("api/credentials/", GetCredentialsAPIView.as_view(), name="get_credentials"),
]
