"""
Unit tests for the `poller` app.

This module contains tests for the models, views, and signals in the `poller` app.
It ensures that the polling functionality works as expected and integrates correctly
with the federated database.
"""

import json

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

from apps.core.models import FederatedData, FederatedNode
from apps.poller.models import GeographicalScope, Poll, PollOption, Vote

User = get_user_model()


class GeographicalScopeModelTest(TestCase):
    """Test cases for the GeographicalScope model."""

    def setUp(self):
        """Set up test data."""
        self.geographical_scope = GeographicalScope.objects.create(
            name="local",
            description="Local scope (e.g., city, town).",
            is_active=True,
        )

    def test_geographical_scope_creation(self):
        """Test that a GeographicalScope instance is created correctly."""
        self.assertEqual(self.geographical_scope.name, "local")
        self.assertEqual(
            self.geographical_scope.description, "Local scope (e.g., city, town)."
        )
        self.assertTrue(self.geographical_scope.is_active)
        self.assertEqual(str(self.geographical_scope), "local")


class PollModelTest(TestCase):
    """Test cases for the Poll model."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(username="testuser", password="testpass")
        self.geographical_scope = GeographicalScope.objects.create(
            name="local",
            description="Local scope (e.g., city, town).",
            is_active=True,
        )
        self.poll = Poll.objects.create(
            title="Favorite Color",
            description="What is your favorite color?",
            created_by=self.user,
            geographical_scope=self.geographical_scope,
            is_active=True,
        )
        # Refresh the poll instance to ensure it is up-to-date
        self.poll.refresh_from_db()
        self.option1 = PollOption.objects.create(poll=self.poll, text="Red", votes=0)
        self.option2 = PollOption.objects.create(poll=self.poll, text="Blue", votes=0)

    def test_poll_creation(self):
        """Test that a Poll instance is created correctly."""
        self.assertEqual(self.poll.title, "Favorite Color")
        self.assertEqual(self.poll.description, "What is your favorite color?")
        self.assertEqual(self.poll.created_by, self.user)
        self.assertEqual(self.poll.geographical_scope, self.geographical_scope)
        self.assertTrue(self.poll.is_active)
        self.assertEqual(str(self.poll), "Favorite Color")

    def test_poll_options(self):
        """Test that poll options are correctly associated with the poll."""
        self.assertEqual(self.poll.options.count(), 2)
        self.assertEqual(self.poll.options.first().text, "Red")
        self.assertEqual(self.poll.options.last().text, "Blue")


class VoteModelTest(TestCase):
    """Test cases for the Vote model."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(username="testuser", password="testpass")
        self.other_user = User.objects.create_user(
            username="otheruser", password="testpass"
        )
        self.geographical_scope = GeographicalScope.objects.create(
            name="local",
            description="Local scope (e.g., city, town).",
            is_active=True,
        )
        self.poll = Poll.objects.create(
            title="Favorite Color",
            description="What is your favorite color?",
            created_by=self.user,
            geographical_scope=self.geographical_scope,
            is_active=True,
        )
        self.option = PollOption.objects.create(poll=self.poll, text="Red", votes=0)
        self.vote = Vote.objects.create(
            poll=self.poll, option=self.option, user=self.user
        )

    def test_vote_creation(self):
        """Test that a Vote instance is created correctly."""
        self.assertEqual(self.vote.poll, self.poll)
        self.assertEqual(self.vote.option, self.option)
        self.assertEqual(self.vote.user, self.user)
        self.assertEqual(str(self.vote), "testuser voted for Red in Favorite Color")

    def test_unique_vote_per_user(self):
        """Test that a user can only vote once in a poll."""
        with self.assertRaises(Exception):
            Vote.objects.create(poll=self.poll, option=self.option, user=self.user)


class FederatedPollTest(TestCase):
    """Test cases for the FederatedPoll model."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(username="testuser", password="testpass")
        self.geographical_scope = GeographicalScope.objects.create(
            name="local",
            description="Local scope (e.g., city, town).",
            is_active=True,
        )
        self.poll = Poll.objects.create(
            title="Favorite Color",
            description="What is your favorite color?",
            created_by=self.user,
            geographical_scope=self.geographical_scope,
            is_active=True,
        )
        self.option1 = PollOption.objects.create(poll=self.poll, text="Red", votes=0)
        self.option2 = PollOption.objects.create(poll=self.poll, text="Blue", votes=0)
        self.node, _ = FederatedNode.objects.get_or_create(
            name="local",
            defaults={
                "endpoint": "https://local.example.com",
                "public_key": "public-key-123",
                "is_active": True,
            },
        )

    def test_federated_poll_creation(self):
        """Test that a FederatedPoll instance is created correctly."""
        federated_data, _ = FederatedData.objects.get_or_create(
            node=self.node,
            data_type="poll",
            data_id=str(self.poll.id),
            defaults={
                "data": {
                    "title": self.poll.title,
                    "description": self.poll.description,
                    "created_by": self.poll.created_by.username,
                    "geographical_scope": self.poll.geographical_scope.name,
                    "is_active": self.poll.is_active,
                    "options": [
                        {"text": option.text, "votes": option.votes}
                        for option in self.poll.options.all()
                    ],
                },
                "version": 1,
                "is_active": True,
            },
        )

        self.assertEqual(federated_data.data_type, "poll")
        self.assertEqual(federated_data.data_id, str(self.poll.id))
        self.assertEqual(federated_data.data["title"], self.poll.title)
        self.assertEqual(federated_data.version, 1)
        self.assertTrue(federated_data.is_active)


class PollerSignalsTest(TestCase):
    """Test cases for the poller app signals."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(username="testuser", password="testpass")
        self.geographical_scope = GeographicalScope.objects.create(
            name="local",
            description="Local scope (e.g., city, town).",
            is_active=True,
        )
        # Create options first
        self.poll = Poll(
            title="Favorite Color",
            description="What is your favorite color?",
            created_by=self.user,
            geographical_scope=self.geographical_scope,
            is_active=True,
        )
        self.poll.save()  # Save the poll first
        self.option1 = PollOption.objects.create(poll=self.poll, text="Red", votes=0)
        self.option2 = PollOption.objects.create(poll=self.poll, text="Blue", votes=0)
        self.node, _ = FederatedNode.objects.get_or_create(
            name="local",
            defaults={
                "endpoint": "https://local.example.com",
                "public_key": "public-key-123",
                "is_active": True,
            },
        )

    def test_sync_poll_on_save(self):
        """Test that a poll is synchronized when it is saved."""
        # Check if a federated data entry was created
        federated_data = FederatedData.objects.filter(
            data_type="poll",
            data_id=str(self.poll.id),
        ).first()

        self.assertIsNotNone(federated_data)
        self.assertEqual(federated_data.data["title"], self.poll.title)
        self.assertEqual(len(federated_data.data["options"]), 2)
        self.assertEqual(federated_data.data["options"][0]["text"], "Red")
        self.assertEqual(federated_data.data["options"][1]["text"], "Blue")

    def test_sync_poll_on_delete(self):
        """Test that a poll is synchronized when it is deleted."""
        self.poll.is_active = False
        self.poll.save()

        # Check if the federated data entry was marked as inactive
        federated_data = FederatedData.objects.filter(
            data_type="poll",
            data_id=str(self.poll.id),
        ).first()

        self.assertIsNotNone(federated_data)
        self.assertFalse(federated_data.is_active)

    def test_sync_vote_on_save(self):
        """Test that a vote is synchronized when it is saved."""
        Vote.objects.create(poll=self.poll, option=self.option1, user=self.user)

        # Check if the vote count was updated in the federated data
        federated_data = FederatedData.objects.filter(
            data_type="poll",
            data_id=str(self.poll.id),
        ).first()

        self.assertIsNotNone(federated_data)
        self.assertEqual(len(federated_data.data["options"]), 2)
        self.assertEqual(federated_data.data["options"][0]["votes"], 1)


class PollerAPIViewsTest(TestCase):
    """Test cases for the poller app API views."""

    def setUp(self):
        """Set up test data."""
        self.client = Client()
        self.user = User.objects.create_user(username="testuser", password="testpass")
        self.geographical_scope = GeographicalScope.objects.create(
            name="local",
            description="Local scope (e.g., city, town).",
            is_active=True,
        )
        self.poll = Poll.objects.create(
            title="Favorite Color",
            description="What is your favorite color?",
            created_by=self.user,
            geographical_scope=self.geographical_scope,
            is_active=True,
        )
        self.option1 = PollOption.objects.create(poll=self.poll, text="Red", votes=0)
        self.option2 = PollOption.objects.create(poll=self.poll, text="Blue", votes=0)

    def test_get_polls(self):
        """Test the GET /api/polls/ endpoint."""
        response = self.client.get(reverse("poll_api"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "success")
        self.assertEqual(len(response.json()["data"]), 1)
        self.assertEqual(response.json()["data"][0]["title"], "Favorite Color")

    def test_get_polls_by_geographical_scope(self):
        """Test the GET /api/polls/ endpoint with a geographical scope filter."""
        response = self.client.get(reverse("poll_api"), {"geographical_scope": "local"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "success")
        self.assertEqual(len(response.json()["data"]), 1)
        self.assertEqual(response.json()["data"][0]["title"], "Favorite Color")

    def test_create_poll(self):
        """Test the POST /api/polls/ endpoint."""
        self.client.force_login(self.user)
        data = {
            "title": "Favorite Food",
            "description": "What is your favorite food?",
            "geographical_scope": "local",
            "options": ["Pizza", "Burger", "Pasta"],
        }
        response = self.client.post(
            reverse("poll_api"),
            data=json.dumps(data),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["status"], "success")
        self.assertEqual(response.json()["data"]["title"], "Favorite Food")

    def test_get_poll_detail(self):
        """Test the GET /api/polls/<poll_id>/ endpoint."""
        response = self.client.get(reverse("poll_detail_api", args=[self.poll.id]))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "success")
        self.assertEqual(response.json()["data"]["title"], "Favorite Color")

    def test_update_poll(self):
        """Test the PUT /api/polls/<poll_id>/ endpoint."""
        self.client.force_login(self.user)
        data = {
            "title": "Updated Favorite Color",
            "description": "What is your updated favorite color?",
            "options": ["Red", "Blue", "Green"],
        }
        response = self.client.put(
            reverse("poll_detail_api", args=[self.poll.id]),
            data=json.dumps(data),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "success")
        self.assertEqual(response.json()["data"]["title"], "Updated Favorite Color")

    def test_delete_poll(self):
        """Test the DELETE /api/polls/<poll_id>/ endpoint."""
        self.client.force_login(self.user)
        response = self.client.delete(reverse("poll_detail_api", args=[self.poll.id]))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "success")
        self.assertEqual(response.json()["data"]["title"], "Favorite Color")

        # Verify the poll is marked as inactive
        poll = Poll.objects.get(id=self.poll.id)
        self.assertFalse(poll.is_active)

    def test_cast_vote(self):
        """Test the POST /api/polls/<poll_id>/votes/ endpoint."""
        self.client.force_login(self.user)
        data = {
            "option_id": self.option1.id,
        }
        response = self.client.post(
            reverse("vote_api", args=[self.poll.id]),
            data=json.dumps(data),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "success")
        self.assertEqual(response.json()["data"]["option_id"], self.option1.id)

        # Verify the vote count was updated
        option = PollOption.objects.get(id=self.option1.id)
        self.assertEqual(option.votes, 1)

    def test_get_votes(self):
        """Test the GET /api/polls/<poll_id>/votes/detail/ endpoint."""
        Vote.objects.create(poll=self.poll, option=self.option1, user=self.user)
        response = self.client.get(reverse("vote_detail_api", args=[self.poll.id]))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "success")
        self.assertEqual(len(response.json()["data"]), 1)
        self.assertEqual(response.json()["data"][0]["option_id"], self.option1.id)
