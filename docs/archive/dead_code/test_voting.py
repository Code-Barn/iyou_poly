"""
Test for vote results update functionality.
"""

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from apps.poller.models import GeographicalScope, Poll, PollOption

User = get_user_model()


class VoteResultsTestCase(TestCase):
    """Test case for vote results update functionality."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            username="testuser", password="testpass123"
        )
        self.client.login(username="testuser", password="testpass123")

        # Create a geographical scope
        self.geographical_scope = GeographicalScope.objects.create(
            name="Test Scope", description="Test geographical scope", is_active=True
        )

        # Create a poll
        self.poll = Poll.objects.create(
            title="Test Poll",
            description="A test poll for voting functionality",
            created_by=self.user,
            geographical_scope=self.geographical_scope,
        )

        # Create poll options
        self.option1 = PollOption.objects.create(poll=self.poll, text="Option 1")
        self.option2 = PollOption.objects.create(poll=self.poll, text="Option 2")

    def test_vote_results_update(self):
        """Test that vote results are updated after voting."""
        # Get the first option
        option = self.poll.options.first()

        # Get the initial vote counts
        initial_option_votes = option.votes
        initial_vote_options_count = option.vote_options.count()
        initial_poll_vote_count = self.poll.votes.count()

        # Vote for the option
        url = reverse("vote_api", args=[self.poll.id])
        response = self.client.post(
            url, {"option_id": option.id}, HTTP_HX_REQUEST="true"
        )

        # Check that the response is successful
        self.assertEqual(response.status_code, 200)

        # Refresh the option to get the updated data
        option.refresh_from_db()

        # Check that the denormalized vote count increased
        self.assertEqual(option.votes, initial_option_votes + 1)

        # Check that the vote record was created
        self.assertEqual(option.vote_options.count(), initial_vote_options_count + 1)

        # Check that the poll's total vote count increased
        self.poll.refresh_from_db()
        self.assertEqual(self.poll.votes.count(), initial_poll_vote_count + 1)
