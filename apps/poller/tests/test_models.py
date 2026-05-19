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

from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.poller.models import Poll, PollOption, PollType, Vote
from apps.core.models import ScopeType, Scope

User = get_user_model()


class PollModelTests(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(username="pollcreator")

    def test_create_public_poll(self):
        poll = Poll.objects.create(
            title="Test Poll",
            description="A test poll",
            created_by=self.user,
            poll_type=PollType.PUBLIC,
        )
        self.assertEqual(str(poll), "Test Poll")
        self.assertTrue(poll.is_active_now)
        self.assertEqual(poll.total_votes, 0)

    def test_create_poll_with_options(self):
        poll = Poll.objects.create(
            title="Options Poll",
            created_by=self.user,
            poll_type=PollType.PUBLIC,
        )
        opt1 = PollOption.objects.create(poll=poll, text="Option A")
        opt2 = PollOption.objects.create(poll=poll, text="Option B")
        self.assertEqual(poll.options.count(), 2)
        self.assertEqual(opt1.votes, 0)
        self.assertEqual(opt2.votes, 0)

    def test_poll_vote_count(self):
        poll = Poll.objects.create(
            title="Vote Count Poll",
            created_by=self.user,
            poll_type=PollType.PUBLIC,
        )
        opt = PollOption.objects.create(poll=poll, text="Option 1")
        Vote.objects.create(poll=poll, option=opt, voter_did=self.user.username)
        # Refresh from DB to pick up signal-based counter increment
        opt.refresh_from_db()
        self.assertEqual(poll.total_votes, 1)

    def test_poll_scope_requirement(self):
        scope_type = ScopeType.objects.create(name="TestScopeType")
        scope = Scope.objects.create(
            scope_type=scope_type, value="test-value", is_active=True
        )
        poll = Poll.objects.create(
            title="Scoped Poll",
            created_by=self.user,
            poll_type=PollType.PUBLIC,
            required_scope=scope,
            required_scope_type=scope_type,
        )
        self.assertEqual(poll.required_scope, scope)
        self.assertEqual(poll.required_scope_type, scope_type)

    def test_family_scoped_poll(self):
        poll = Poll.objects.create(
            title="Family Poll",
            created_by=self.user,
            poll_type=PollType.FAMILY_UNIT,
        )
        self.assertEqual(poll.poll_type, PollType.FAMILY_UNIT)


class VoteModelTests(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(username="voter")
        self.poll = Poll.objects.create(
            title="Vote Test Poll",
            created_by=self.user,
            poll_type=PollType.PUBLIC,
        )
        self.option = PollOption.objects.create(poll=self.poll, text="Option 1")

    def test_create_vote(self):
        vote = Vote.objects.create(
            poll=self.poll,
            option=self.option,
            voter_did=self.user.username,
        )
        self.assertEqual(vote.voter_did, self.user.username)
        self.assertEqual(vote.poll, self.poll)
        self.assertEqual(vote.option, self.option)
        self.assertIsNone(vote.signature)
        self.assertIsNone(vote.merkle_root)

    def test_vote_str(self):
        vote = Vote.objects.create(
            poll=self.poll,
            option=self.option,
            user=self.user,
            voter_did=self.user.username,
        )
        self.assertIn("cast vote for", str(vote))
        self.assertIn(self.user.username, str(vote))
        self.assertIn("'Option 1'", str(vote))
        self.assertIn("[Vote Test Poll]", str(vote))
