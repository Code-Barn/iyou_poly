#!/usr/bin/env python
"""
Simple test for voting functionality in the Poller app.

This script tests the voting functionality by:
1. Creating a test poll with options
2. Simulating a vote from a user
3. Verifying that the vote is correctly recorded
"""

import os
import sys

import django
from django.test import Client
from django.urls import reverse

# Set up Django environment
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from django.contrib.auth import get_user_model

from apps.poller.models import GeographicalScope, Poll, PollOption, Vote

User = get_user_model()


def create_test_data():
    """Create test data for voting test."""
    # Create geographical scope
    geo_scope, _ = GeographicalScope.objects.get_or_create(
        name="local", defaults={"description": "Local scope"}
    )

    # Create test user
    username = "testuser"
    email = "test@example.com"
    password = "testpass123"

    user, created = User.objects.get_or_create(
        username=username, defaults={"email": email}
    )
    if created:
        user.set_password(password)
        user.save()

    # Create test poll
    poll = Poll.objects.create(
        title="Test Poll for Voting",
        description="A test poll for voting functionality",
        created_by=user,
        geographical_scope=geo_scope,
    )

    # Create options
    options = ["Option 1", "Option 2", "Option 3"]
    for option_text in options:
        PollOption.objects.create(poll=poll, text=option_text)

    return user, password, poll


def test_voting():
    """Test the voting functionality."""
    # Create test data
    user, password, poll = create_test_data()

    # Create test client and login
    client = Client()
    client.login(username=user.username, password=password)

    # Get the first option
    option = poll.options.first()

    # Vote for the option
    url = reverse("vote_api", args=[poll.id])
    response = client.post(
        url,
        f"option_id={option.id}",
        HTTP_HX_REQUEST="true",
        content_type="application/x-www-form-urlencoded",
    )

    # Print response details
    print(f"Response status code: {response.status_code}")
    print(f"Response content: {response.content.decode('utf-8')}")

    # Check if the vote was recorded
    vote_count = Vote.objects.filter(poll=poll, option=option).count()
    print(f"Votes for option: {vote_count}")

    # Check total votes
    total_votes = poll.votes.count()
    print(f"Total votes: {total_votes}")

    # Verify the vote was recorded
    if vote_count == 1 and total_votes == 1:
        print("✅ Vote was successfully recorded!")
        return True
    else:
        print("❌ Vote was not recorded correctly.")
        return False


if __name__ == "__main__":
    print("Running simple voting test...")
    success = test_voting()
    sys.exit(0 if success else 1)
