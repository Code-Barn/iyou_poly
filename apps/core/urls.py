"""
URL configuration for the `core` app.

This module defines the URL routes for the API endpoints provided by the `core` app,
including endpoints for managing decentralized identity and federated data.
"""

from django.urls import path

from apps.core.views import (
    did_api,
    federated_data_api,
    federated_data_detail_api,
)

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
]
