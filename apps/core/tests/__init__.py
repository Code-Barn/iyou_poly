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
Unit tests for the `core` app.

This module contains tests for the models, signals, and API views in the `core` app.
It ensures that the decentralized identity and federated data functionality works as expected.
"""

import json

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

from apps.core.models import (
    DID,
    DataSyncLog,
    DIDDocument,
    DIDMethod,
    FederatedData,
    FederatedNode,
    VerifiableCredential,
)

User = get_user_model()


class DIDMethodModelTest(TestCase):
    """Test cases for the DIDMethod model."""

    def setUp(self):
        """Set up test data."""
        self.did_method = DIDMethod.objects.create(
            name="key",
            description="A DID method for cryptographic keys.",
            is_active=True,
        )

    def test_did_method_creation(self):
        """Test that a DIDMethod instance is created correctly."""
        self.assertEqual(self.did_method.name, "key")
        self.assertEqual(
            self.did_method.description, "A DID method for cryptographic keys."
        )
        self.assertTrue(self.did_method.is_active)
        self.assertEqual(str(self.did_method), "did:key")


class DIDModelTest(TestCase):
    """Test cases for the DID model."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(username="testuser", password="testpass")
        self.did_method = DIDMethod.objects.create(
            name="key",
            description="A DID method for cryptographic keys.",
            is_active=True,
        )
        self.did = DID.objects.create(
            user=self.user,
            method=self.did_method,
            identifier="example123456789",
            is_primary=True,
            is_active=True,
        )

    def test_did_creation(self):
        """Test that a DID instance is created correctly."""
        self.assertEqual(self.did.user, self.user)
        self.assertEqual(self.did.method, self.did_method)
        self.assertEqual(self.did.identifier, "example123456789")
        self.assertEqual(self.did.did_uri, "did:key:example123456789")
        self.assertTrue(self.did.is_primary)
        self.assertTrue(self.did.is_active)
        self.assertEqual(str(self.did), "did:key:example123456789")

    def test_did_save(self):
        """Test that the DID URI is correctly formatted on save."""
        self.did.identifier = "newidentifier"
        self.did.save()
        self.assertEqual(self.did.did_uri, "did:key:newidentifier")


class DIDDocumentModelTest(TestCase):
    """Test cases for the DIDDocument model."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(username="testuser", password="testpass")
        self.did_method = DIDMethod.objects.create(
            name="key",
            description="A DID method for cryptographic keys.",
            is_active=True,
        )
        self.did = DID.objects.create(
            user=self.user,
            method=self.did_method,
            identifier="example123456789",
            is_primary=True,
            is_active=True,
        )
        self.did_document = DIDDocument.objects.create(
            did=self.did,
            document={"id": self.did.did_uri, "verificationMethod": []},
        )

    def test_did_document_creation(self):
        """Test that a DIDDocument instance is created correctly."""
        self.assertEqual(self.did_document.did, self.did)
        self.assertEqual(self.did_document.document["id"], self.did.did_uri)
        self.assertEqual(str(self.did_document), f"DID Document for {self.did}")


class VerifiableCredentialModelTest(TestCase):
    """Test cases for the VerifiableCredential model."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(username="testuser", password="testpass")
        self.verifiable_credential = VerifiableCredential.objects.create(
            user=self.user,
            credential={"id": "example-vc", "type": "VerifiableCredential"},
            issuer="did:key:issuer123",
            is_active=True,
        )

    def test_verifiable_credential_creation(self):
        """Test that a VerifiableCredential instance is created correctly."""
        self.assertEqual(self.verifiable_credential.user, self.user)
        self.assertEqual(self.verifiable_credential.credential["id"], "example-vc")
        self.assertEqual(self.verifiable_credential.issuer, "did:key:issuer123")
        self.assertTrue(self.verifiable_credential.is_active)
        self.assertEqual(
            str(self.verifiable_credential),
            f"VC for {self.user} issued by did:key:issuer123",
        )


class FederatedNodeModelTest(TestCase):
    """Test cases for the FederatedNode model."""

    def setUp(self):
        """Set up test data."""
        self.federated_node = FederatedNode.objects.create(
            name="Node1",
            endpoint="https://node1.example.com",
            public_key="public-key-123",
            is_active=True,
        )

    def test_federated_node_creation(self):
        """Test that a FederatedNode instance is created correctly."""
        self.assertEqual(self.federated_node.name, "Node1")
        self.assertEqual(self.federated_node.endpoint, "https://node1.example.com")
        self.assertEqual(self.federated_node.public_key, "public-key-123")
        self.assertTrue(self.federated_node.is_active)
        self.assertEqual(str(self.federated_node), "Node1")


class FederatedDataModelTest(TestCase):
    """Test cases for the FederatedData model."""

    def setUp(self):
        """Set up test data."""
        self.federated_node = FederatedNode.objects.create(
            name="Node1",
            endpoint="https://node1.example.com",
            public_key="public-key-123",
            is_active=True,
        )
        self.federated_data = FederatedData.objects.create(
            node=self.federated_node,
            data_type="poll",
            data_id="poll123",
            data={
                "question": "What is your favorite color?",
                "options": ["Red", "Blue", "Green"],
            },
            version=1,
            is_active=True,
        )

    def test_federated_data_creation(self):
        """Test that a FederatedData instance is created correctly."""
        self.assertEqual(self.federated_data.node, self.federated_node)
        self.assertEqual(self.federated_data.data_type, "poll")
        self.assertEqual(self.federated_data.data_id, "poll123")
        self.assertEqual(
            self.federated_data.data["question"], "What is your favorite color?"
        )
        self.assertEqual(self.federated_data.version, 1)
        self.assertTrue(self.federated_data.is_active)
        self.assertEqual(
            str(self.federated_data), f"poll:poll123 (Node: {self.federated_node.name})"
        )


class DataSyncLogModelTest(TestCase):
    """Test cases for the DataSyncLog model."""

    def setUp(self):
        """Set up test data."""
        self.source_node = FederatedNode.objects.create(
            name="Node1",
            endpoint="https://node1.example.com",
            public_key="public-key-123",
            is_active=True,
        )
        self.target_node = FederatedNode.objects.create(
            name="Node2",
            endpoint="https://node2.example.com",
            public_key="public-key-456",
            is_active=True,
        )
        self.sync_log = DataSyncLog.objects.create(
            source_node=self.source_node,
            target_node=self.target_node,
            data_type="poll",
            data_id="poll123",
            version=1,
            status="success",
            details="Data synchronized successfully.",
        )

    def test_data_sync_log_creation(self):
        """Test that a DataSyncLog instance is created correctly."""
        self.assertEqual(self.sync_log.source_node, self.source_node)
        self.assertEqual(self.sync_log.target_node, self.target_node)
        self.assertEqual(self.sync_log.data_type, "poll")
        self.assertEqual(self.sync_log.data_id, "poll123")
        self.assertEqual(self.sync_log.version, 1)
        self.assertEqual(self.sync_log.status, "success")
        self.assertEqual(self.sync_log.details, "Data synchronized successfully.")
        self.assertEqual(
            str(self.sync_log),
            f"Sync {self.sync_log.status}: {self.sync_log.data_type}:{self.sync_log.data_id} from {self.sync_log.source_node} to {self.sync_log.target_node}",
        )


class FederatedDataSignalsTest(TestCase):
    """Test cases for the federated data signals."""

    def setUp(self):
        """Set up test data."""
        self.source_node = FederatedNode.objects.create(
            name="Node1",
            endpoint="https://node1.example.com",
            public_key="public-key-123",
            is_active=True,
        )
        self.target_node = FederatedNode.objects.create(
            name="Node2",
            endpoint="https://node2.example.com",
            public_key="public-key-456",
            is_active=True,
        )

    def test_sync_new_data(self):
        """Test that new federated data is synchronized to other nodes."""
        FederatedData.objects.create(
            node=self.source_node,
            data_type="poll",
            data_id="poll123",
            data={
                "question": "What is your favorite color?",
                "options": ["Red", "Blue", "Green"],
            },
            version=1,
            is_active=True,
        )

        # Check if a sync log was created for the target node
        sync_log = DataSyncLog.objects.filter(
            source_node=self.source_node,
            target_node=self.target_node,
            data_type="poll",
            data_id="poll123",
            status="success",
        ).first()

        self.assertIsNotNone(sync_log)
        self.assertEqual(sync_log.details, "Data synchronized: poll:poll123")

    def test_sync_updated_data(self):
        """Test that updated federated data is synchronized to other nodes."""
        federated_data = FederatedData.objects.create(
            node=self.source_node,
            data_type="poll",
            data_id="poll123",
            data={
                "question": "What is your favorite color?",
                "options": ["Red", "Blue", "Green"],
            },
            version=1,
            is_active=True,
        )

        # Update the data
        federated_data.data = {
            "question": "What is your favorite food?",
            "options": ["Pizza", "Burger", "Pasta"],
        }
        federated_data.save()

        # Check if the version was incremented
        self.assertEqual(federated_data.version, 2)

        # Check if a sync log was created for the target node
        sync_log = DataSyncLog.objects.filter(
            source_node=self.source_node,
            target_node=self.target_node,
            data_type="poll",
            data_id="poll123",
            version=2,
            status="success",
        ).first()

        self.assertIsNotNone(sync_log)
        self.assertEqual(sync_log.details, "Data synchronized: poll:poll123")

    def test_sync_deleted_data(self):
        """Test that deleted federated data is synchronized to other nodes."""
        federated_data = FederatedData.objects.create(
            node=self.source_node,
            data_type="poll",
            data_id="poll123",
            data={
                "question": "What is your favorite color?",
                "options": ["Red", "Blue", "Green"],
            },
            version=1,
            is_active=True,
        )

        # Delete the data by calling delete() instead of setting is_active=False
        federated_data.delete()

        # Check if a sync log was created for the target node
        sync_log = DataSyncLog.objects.filter(
            source_node=self.source_node,
            target_node=self.target_node,
            data_type="poll",
            data_id="poll123",
            status="success",
        ).first()

        self.assertIsNotNone(sync_log)
        self.assertEqual(sync_log.details, "Data deleted: poll:poll123")


class CoreAPIViewsTest(TestCase):
    """Test cases for the core app API views."""

    def setUp(self):
        """Set up test data."""
        self.client = Client()
        self.source_node = FederatedNode.objects.create(
            name="Node1",
            endpoint="https://node1.example.com",
            public_key="public-key-123",
            is_active=True,
        )
        self.target_node = FederatedNode.objects.create(
            name="Node2",
            endpoint="https://node2.example.com",
            public_key="public-key-456",
            is_active=True,
        )
        self.federated_data = FederatedData.objects.create(
            node=self.source_node,
            data_type="poll",
            data_id="poll123",
            data={
                "question": "What is your favorite color?",
                "options": ["Red", "Blue", "Green"],
            },
            version=1,
            is_active=True,
        )

    def test_get_federated_data(self):
        """Test the GET /api/federated-data/ endpoint."""
        response = self.client.get(reverse("federated_data_api"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "success")
        self.assertEqual(len(response.json()["data"]), 1)
        self.assertEqual(response.json()["data"][0]["data_type"], "poll")

    def test_get_federated_data_node(self):
        """Test the GET /api/federated-data/<node_name>/ endpoint."""
        response = self.client.get(reverse("federated_data_api_node", args=["Node1"]))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "success")
        self.assertEqual(len(response.json()["data"]), 1)
        self.assertEqual(response.json()["data"][0]["data_type"], "poll")

    def test_get_federated_data_detail(self):
        """Test the GET /api/federated-data/<node_name>/<data_type>/<data_id>/ endpoint."""
        response = self.client.get(
            reverse("federated_data_detail_api", args=["Node1", "poll", "poll123"])
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "success")
        self.assertEqual(response.json()["data"]["data_type"], "poll")
        self.assertEqual(response.json()["data"]["data_id"], "poll123")

    def test_create_federated_data(self):
        """Test the POST /api/federated-data/<node_name>/ endpoint."""
        data = {
            "data_type": "poll",
            "data_id": "poll456",
            "data": {
                "question": "What is your favorite food?",
                "options": ["Pizza", "Burger", "Pasta"],
            },
        }
        response = self.client.post(
            reverse("federated_data_api_node", args=["Node1"]),
            data=json.dumps(data),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["status"], "success")
        self.assertEqual(response.json()["data"]["data_type"], "poll")
        self.assertEqual(response.json()["data"]["data_id"], "poll456")

    def test_update_federated_data(self):
        """Test the PUT /api/federated-data/<node_name>/<data_type>/<data_id>/ endpoint."""
        data = {
            "data": {
                "question": "What is your favorite food?",
                "options": ["Pizza", "Burger", "Pasta"],
            },
        }
        response = self.client.put(
            reverse("federated_data_detail_api", args=["Node1", "poll", "poll123"]),
            data=json.dumps(data),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "success")
        self.assertEqual(response.json()["data"]["version"], 2)

    def test_delete_federated_data(self):
        """Test the DELETE /api/federated-data/<node_name>/<data_type>/<data_id>/ endpoint."""
        response = self.client.delete(
            reverse("federated_data_detail_api", args=["Node1", "poll", "poll123"])
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "success")
        self.assertEqual(response.json()["data"]["data_type"], "poll")
        self.assertEqual(response.json()["data"]["data_id"], "poll123")

        # Verify the data is marked as inactive
        federated_data = FederatedData.objects.get(
            node=self.source_node, data_type="poll", data_id="poll123"
        )
        self.assertFalse(federated_data.is_active)
