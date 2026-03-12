#!/usr/bin/env python
"""
Final test for voting functionality in the Poller app.

This script tests the voting functionality by:
1. Creating a test poll with options
2. Simulating votes from different users
3. Verifying that votes are correctly recorded and counted
"""

import os

import django
from django.contrib.auth import get_user_model
from django.test import Client

from apps.poller.models import GeographicalScope, Poll, PollOption, Vote

# Set up Django environment
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()


User = get_user_model()


def create_test_data():
    """Create test data for voting tests."""
    # Create geographical scope
    geo_scope, _ = GeographicalScope.objects.get_or_create(
        name="local", defaults={"description": "Local scope"}
    )

    # Create test users
    users = []
    for i in range(2):
        username = f"testuser{i}"
        email = f"test{i}@example.com"
        password = "testpass123"

        user, created = User.objects.get_or_create(
            username=username, defaults={"email": email}
        )
        if created:
            user.set_password(password)
            user.save()

        users.append((user, password))

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

    return users, poll


def test_voting_functionality():
    """Test the voting functionality."""
    # Create test data
    users, poll = create_test_data()

    # Create test client and login for first user
    client1 = Client()
    client1.login(username=users[0][0].username, password=users[0][1])

    # Test 1: Vote for Option 1
    option1 = poll.options.get(text="Option 1")
    response = client1.post(
        f"/api/polls/{poll.id}/votes/",
        {"option_id": option1.id},
        HTTP_HX_REQUEST="true",
    )
    assert response.status_code == 200, (
        f"Test 1 - Expected status 200, got {response.status_code}"
    )

    # Verify vote was recorded
    vote_count = Vote.objects.filter(poll=poll, option=option1).count()
    assert vote_count == 1, f"Test 1 - Expected 1 vote for Option 1, got {vote_count}"

    # Create test client and login for second user
    client2 = Client()
    client2.login(username=users[1][0].username, password=users[1][1])

    # Test 2: Try to vote again with first user (should fail)
    response = client1.post(
        f"/api/polls/{poll.id}/votes/",
        {"option_id": option1.id},
        HTTP_HX_REQUEST="true",
    )
    assert response.status_code == 400, (
        f"Test 2 - Expected status 400, got {response.status_code}"
    )

    # Test 3: Vote for Option 2 with second user

    option2 = poll.options.get(text="Option 2")
    response = client2.post(
        f"/api/polls/{poll.id}/votes/",
        {"option_id": option2.id},
        HTTP_HX_REQUEST="true",
    )
    assert response.status_code == 200, (
        f"Test 3 - Expected status 200, got {response.status_code}"
    )

    # Verify vote was recorded
    vote_count = Vote.objects.filter(poll=poll, option=option2).count()
    assert vote_count == 1, f"Test 3 - Expected 1 vote for Option 2, got {vote_count}"

    # Test 4: Verify total votes
    total_votes = poll.votes.count()
    assert total_votes == 2, f"Test 4 - Expected 2 total votes, got {total_votes}"

    # Verify votes per option
    option1_votes = Vote.objects.filter(poll=poll, option=option1).count()
    option2_votes = Vote.objects.filter(poll=poll, option=option2).count()
    option3_votes = Vote.objects.filter(poll=poll, option__text="Option 3").count()

    assert option1_votes == 1, (
        f"Test 4 - Expected 1 vote for Option 1, got {option1_votes}"
    )
    assert option2_votes == 1, (
        f"Test 4 - Expected 1 vote for Option 2, got {option2_votes}"
    )
    assert option3_votes == 0, (
        f"Test 4 - Expected 0 votes for Option 3, got {option3_votes}"
    )

    print("✅ All voting functionality tests passed!")


def test_vote_validation():
    """Test vote validation."""
    # Create test data
    users, poll = create_test_data()

    # Create test client and login
    client = Client()
    client.login(username=users[0][0].username, password=users[0][1])

    # Test 1: Vote without option_id (should fail)
    response = client.post(f"/api/polls/{poll.id}/votes/", {}, HTTP_HX_REQUEST="true")
    assert response.status_code == 400, (
        f"Test 1 - Expected status 400, got {response.status_code}"
    )

    # Test 2: Vote with invalid option_id (should fail)
    response = client.post(
        f"/api/polls/{poll.id}/votes/", {"option_id": 9999}, HTTP_HX_REQUEST="true"
    )
    assert response.status_code == 404, (
        f"Test 2 - Expected status 404, got {response.status_code}"
    )

    # Test 3: Vote without authentication (should fail)
    client.logout()
    option1 = poll.options.get(text="Option 1")
    response = client.post(
        f"/api/polls/{poll.id}/votes/",
        {"option_id": option1.id},
        HTTP_HX_REQUEST="true",
    )
    assert response.status_code == 401, (
        f"Test 3 - Expected status 401, got {response.status_code}"
    )

    print("✅ All vote validation tests passed!")


if __name__ == "__main__":
    print("Running voting functionality tests...")
    test_voting_functionality()
    test_vote_validation()
    print("All tests completed!")
