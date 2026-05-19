#!/usr/bin/env python

# Copyright (C) 2026 Byers Brands, LLC
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

import os
import sys

import django

from apps.poller.models import Poll, Vote

# Set up Django environment
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()


def check_votes(poll_id):
    """Check votes for a specific poll."""
    try:
        poll = Poll.objects.get(id=poll_id)
        print(f"Poll: {poll.title}")
        print(f"Total votes: {poll.votes.count()}")

        # Count votes per option
        print("\nVotes per option:")
        for option in poll.options.all():
            vote_count = Vote.objects.filter(option=option).count()
            print(f"Option {option.id} ({option.text}): {vote_count} vote(s)")

        # List all votes
        print("\nAll votes:")
        for vote in poll.votes.all():
            print(
                f"Vote ID: {vote.id}, User: {vote.user.username}, Option ID: {vote.option.id}, Option Text: {vote.option.text}"
            )

    except Poll.DoesNotExist:
        print(f"Poll with ID {poll_id} does not exist.")
    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        poll_id = int(sys.argv[1])
        check_votes(poll_id)
    else:
        print("Usage: python check_votes.py <poll_id>")
