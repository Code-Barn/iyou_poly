#!/usr/bin/env python
"""
Final test for voting functionality in the Poller app.

This script tests the voting functionality by:
1. Creating a test poll with options
2. Simulating a vote from a user
3. Verifying that the vote is correctly recorded
4. Testing the UI update
"""

import os
import signal
import subprocess
import sys
import time
from urllib.parse import urljoin

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
        title="Final Test Poll",
        description="A final test poll for voting functionality",
        created_by=user,
        geographical_scope=geo_scope,
    )

    # Create options
    options = ["Option A", "Option B", "Option C"]
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
    print(f"Voting for option: {option.text} (ID: {option.id})")

    # Vote for the option using the API
    url = reverse("vote_api", args=[poll.id])
    response = client.post(
        url,
        f"option_id={option.id}",
        HTTP_HX_REQUEST="true",
        content_type="application/x-www-form-urlencoded",
    )

    # Print response details
    print(f"API Response status code: {response.status_code}")
    print(f"API Response content type: {response.get('Content-Type', 'Unknown')}")
    print(f"API Response content length: {len(response.content)}")

    # Print response content for debugging
    print("API Response content (first 500 chars):")
    print(response.content[:500].decode("utf-8"))

    # Check if the response is HTML
    if "text/html" in response.get("Content-Type", ""):
        print("✅ Response is HTML as expected for HTMX request")
    else:
        print("❌ Response is not HTML")

    # Check if the vote was recorded
    vote_count = Vote.objects.filter(poll=poll, option=option).count()
    print(f"Votes for option: {vote_count}")

    # Check total votes
    total_votes = poll.votes.count()
    print(f"Total votes: {total_votes}")

    # Verify the vote was recorded
    if vote_count == 1 and total_votes == 1:
        print("✅ Vote was successfully recorded!")

        # Test the UI update by fetching the poll detail page
        detail_url = reverse("poll_detail", args=[poll.id])
        detail_response = client.get(detail_url)
        print(f"Poll detail status code: {detail_response.status_code}")
        print(f"Poll detail content length: {len(detail_response.content)}")

        # Print detail response content for debugging
        print("Poll detail content (first 500 chars):")
        print(detail_response.content[:500].decode("utf-8"))

        # Check if the user's vote is displayed
        if f"You voted for {option.text}" in detail_response.content.decode("utf-8"):
            print("✅ User's vote is displayed in the UI")
            return True
        else:
            print("❌ User's vote is not displayed in the UI")
            return False
    else:
        print("❌ Vote was not recorded correctly.")
        return False


def test_vote_validation():
    """Test vote validation."""
    # Create test data
    user, password, poll = create_test_data()

    # Create test client and login
    client = Client()
    client.login(username=user.username, password=password)

    # Test 1: Vote without option_id (should fail)
    response = client.post(
        reverse("vote_api", args=[poll.id]),
        "",
        HTTP_HX_REQUEST="true",
        content_type="application/x-www-form-urlencoded",
    )
    print(f"Test 1 - Vote without option_id: {response.status_code}")
    if response.status_code == 400:
        print("✅ Correctly rejected vote without option_id")
    else:
        print("❌ Should have rejected vote without option_id")

    # Test 2: Vote with invalid option_id (should fail)
    response = client.post(
        reverse("vote_api", args=[poll.id]),
        "option_id=9999",
        HTTP_HX_REQUEST="true",
        content_type="application/x-www-form-urlencoded",
    )
    print(f"Test 2 - Vote with invalid option_id: {response.status_code}")
    if response.status_code == 404:
        print("✅ Correctly rejected vote with invalid option_id")
    else:
        print("❌ Should have rejected vote with invalid option_id")

    # Test 3: Vote without authentication (should fail)
    client.logout()
    option = poll.options.first()
    response = client.post(
        reverse("vote_api", args=[poll.id]),
        f"option_id={option.id}",
        HTTP_HX_REQUEST="true",
        content_type="application/x-www-form-urlencoded",
    )
    print(f"Test 3 - Vote without authentication: {response.status_code}")
    if response.status_code == 401:
        print("✅ Correctly rejected vote without authentication")
        return True
    else:
        print("❌ Should have rejected vote without authentication")
        return False


if __name__ == "__main__":
    print("Running final voting test...")
    print("\n=== Testing Voting Functionality ===")
    voting_success = test_voting()

    print("\n=== Testing Vote Validation ===")
    validation_success = test_vote_validation()

    if voting_success and validation_success:
        print("\n🎉 All tests passed! Voting functionality is working correctly.")
        sys.exit(0)
    else:
        print("\n❌ Some tests failed. Please check the implementation.")
        sys.exit(1)
