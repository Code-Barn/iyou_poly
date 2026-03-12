#!/usr/bin/env python
"""
Simple test for voting functionality in the Poller app.

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

import django
from django.contrib.auth import get_user_model
from django.test import Client
from django.urls import reverse

from apps.poller.models import GeographicalScope, Poll, PollOption, Vote

# Set up Django environment
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()


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


def start_server():
    """Start the Django development server."""
    # Start the server in a subprocess
    process = subprocess.Popen(
        ["uv", "run", "python", "manage.py", "runserver", "8002"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    # Wait for server to start
    time.sleep(2)

    return process


def stop_server(process):
    """Stop the Django development server."""
    # Terminate the server process
    process.send_signal(signal.SIGTERM)
    process.wait()


def test_voting():
    """Test the voting functionality."""
    # Create test data
    user, password, poll = create_test_data()

    # Start the server
    server_process = start_server()

    try:
        # Create test client
        client = Client()

        # Login the user
        login_success = client.login(username=user.username, password=password)
        print(f"Login successful: {login_success}")

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

        print(f"API Response status code: {response.status_code}")
        print(f"API Response content: {response.content.decode('utf-8')}")

        # Check if the vote was recorded
        vote_count = Vote.objects.filter(poll=poll, option=option).count()
        print(f"Votes for option: {vote_count}")

        # Check total votes
        total_votes = poll.votes.count()
        print(f"Total votes: {total_votes}")

        # Test the UI update by fetching the poll detail page
        detail_url = reverse("poll_detail", args=[poll.id])
        detail_response = client.get(detail_url)
        print(f"Poll detail status code: {detail_response.status_code}")
        print(f"Poll detail content length: {len(detail_response.content)}")

        # Check if the user's vote is displayed
        if f"You voted for {option.text}" in detail_response.content.decode("utf-8"):
            print("✅ User's vote is displayed in the UI")
        else:
            print("❌ User's vote is not displayed in the UI")

        # Verify the vote was recorded
        if vote_count == 1 and total_votes == 1:
            print("✅ Vote was successfully recorded!")
            return True
        else:
            print("❌ Vote was not recorded correctly.")
            return False

    finally:
        # Stop the server
        stop_server(server_process)


if __name__ == "__main__":
    print("Running simple voting test...")
    success = test_voting()
    sys.exit(0 if success else 1)
