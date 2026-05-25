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

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from apps.poller.models import Poll, PollOption, PollType, TemporalPollType, Vote

User = get_user_model()

_no_session_refresh = override_settings(
    MIDDLEWARE=[
        "debug_toolbar.middleware.DebugToolbarMiddleware",
        "django.middleware.security.SecurityMiddleware",
        "django.contrib.sessions.middleware.SessionMiddleware",
        "django.middleware.common.CommonMiddleware",
        "django.middleware.csrf.CsrfViewMiddleware",
        "django.contrib.auth.middleware.AuthenticationMiddleware",
        "django.contrib.messages.middleware.MessageMiddleware",
        "django.middleware.clickjacking.XFrameOptionsMiddleware",
    ]
)


class PollListViewTests(TestCase):

    def test_poll_list_publicly_accessible(self):
        response = self.client.get(reverse("poll_list"))
        self.assertEqual(response.status_code, 200)

    def test_poll_list_shows_polls(self):
        user = User.objects.create_user(username="creator")
        Poll.objects.create(
            title="Visible Poll",
            created_by=user,
            poll_type=PollType.PUBLIC,
        )
        response = self.client.get(reverse("poll_list"))
        self.assertContains(response, "Visible Poll")


class PollDetailViewTests(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(username="creator")
        self.poll = Poll.objects.create(
            title="Detail Test Poll",
            created_by=self.user,
            poll_type=PollType.PUBLIC,
        )
        PollOption.objects.create(poll=self.poll, text="Test Option")

    def test_poll_detail_publicly_accessible(self):
        response = self.client.get(reverse("poll_detail", args=[self.poll.id]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Detail Test Poll")


@_no_session_refresh
class PollCreateViewTests(TestCase):

    def test_poll_create_requires_auth(self):
        response = self.client.get(reverse("poll_create"))
        self.assertEqual(response.status_code, 302)
        self.assertIn("authenticate", response.url)

    def test_poll_create_accessible_when_authenticated(self):
        user = User.objects.create_user(username="creator", password="pass123")
        self.client.force_login(user)
        response = self.client.get(reverse("poll_create"))
        self.assertEqual(response.status_code, 200)


@_no_session_refresh
class VoteAPITests(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(username="voter")
        self.poll = Poll.objects.create(
            title="Votable Poll",
            created_by=self.user,
            poll_type=PollType.PUBLIC,
        )
        self.option = PollOption.objects.create(poll=self.poll, text="Option A")

    def test_authenticated_user_can_vote(self):
        self.client.force_login(self.user)
        response = self.client.post(
            reverse("vote_api", args=[self.poll.id]),
            {"option_id": self.option.id},
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("Vote cast successfully", str(response.content))

    def test_vote_increments_option_counter(self):
        self.client.force_login(self.user)
        self.client.post(
            reverse("vote_api", args=[self.poll.id]),
            {"option_id": self.option.id},
        )
        self.assertEqual(
            Vote.objects.filter(option=self.option, is_current=True).count(), 1
        )

    def test_unauthenticated_user_cannot_vote(self):
        response = self.client.post(
            reverse("vote_api", args=[self.poll.id]),
            {"option_id": self.option.id},
        )
        self.assertEqual(response.status_code, 401)

    def test_duplicate_vote_prevented(self):
        self.client.force_login(self.user)
        self.client.post(
            reverse("vote_api", args=[self.poll.id]),
            {"option_id": self.option.id},
        )
        response = self.client.post(
            reverse("vote_api", args=[self.poll.id]),
            {"option_id": self.option.id},
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("already voted", str(response.content))

    def test_vote_without_option_id_returns_error(self):
        self.client.force_login(self.user)
        response = self.client.post(
            reverse("vote_api", args=[self.poll.id]),
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("Option ID is required", str(response.content))

    def test_public_poll_does_not_require_credential(self):
        self.client.force_login(self.user)
        response = self.client.post(
            reverse("vote_api", args=[self.poll.id]),
            {"option_id": self.option.id},
        )
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("requires_credential", str(response.content))

    def test_vote_api_htmx_success_returns_html(self):
        self.client.force_login(self.user)
        response = self.client.post(
            reverse("vote_api", args=[self.poll.id]),
            {"option_id": self.option.id},
            HTTP_HX_REQUEST="true",
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "You voted for")


class TemporalPollingTests(TestCase):
    """Temporal validation: TIMED / SCHEDULED / ONGOING polls."""

    def setUp(self):
        self.user = User.objects.create_user(username="creator")

    def _make_vote_data(self, option_id):
        return {"option_id": option_id}

    # --- Scheduled poll: reject before start ---

    def test_scheduled_poll_rejects_vote_before_start(self):
        poll = Poll.objects.create(
            title="Future Poll",
            created_by=self.user,
            poll_type=PollType.PUBLIC,
            temporal_type=TemporalPollType.SCHEDULED,
            starts_at=timezone.now() + timezone.timedelta(hours=1),
            ends_at=timezone.now() + timezone.timedelta(hours=2),
        )
        option = PollOption.objects.create(poll=poll, text="Later")
        self.client.force_login(self.user)
        response = self.client.post(
            reverse("vote_api", args=[poll.id]),
            {"option_id": option.id},
        )
        self.assertIn("not started yet", str(response.content).lower())

    # --- Timed poll: reject after end ---

    def test_timed_poll_rejects_vote_after_end(self):
        poll = Poll.objects.create(
            title="Expired Poll",
            created_by=self.user,
            poll_type=PollType.PUBLIC,
            temporal_type=TemporalPollType.TIMED,
            starts_at=timezone.now() - timezone.timedelta(hours=2),
            ends_at=timezone.now() - timezone.timedelta(hours=1),
        )
        option = PollOption.objects.create(poll=poll, text="Too Late")
        self.client.force_login(self.user)
        response = self.client.post(
            reverse("vote_api", args=[poll.id]),
            {"option_id": option.id},
        )
        self.assertIn("ended", str(response.content).lower())

    # --- Ongoing poll: always active ---

    def test_ongoing_poll_accepts_vote_anytime(self):
        poll = Poll.objects.create(
            title="Evergreen Poll",
            created_by=self.user,
            poll_type=PollType.PUBLIC,
            temporal_type=TemporalPollType.ONGOING,
        )
        option = PollOption.objects.create(poll=poll, text="Forever")
        self.client.force_login(self.user)
        response = self.client.post(
            reverse("vote_api", args=[poll.id]),
            {"option_id": option.id},
        )
        self.assertEqual(response.status_code, 200)

    # --- Immutable poll rejects duplicate ---

    def test_immutable_poll_rejects_duplicate_vote(self):
        poll = Poll.objects.create(
            title="Immutable Poll",
            created_by=self.user,
            poll_type=PollType.PUBLIC,
            temporal_type=TemporalPollType.TIMED,
            is_mutable=False,
            starts_at=timezone.now() - timezone.timedelta(hours=1),
            ends_at=timezone.now() + timezone.timedelta(hours=1),
        )
        option = PollOption.objects.create(poll=poll, text="One Shot")
        self.client.force_login(self.user)
        self.client.post(
            reverse("vote_api", args=[poll.id]),
            {"option_id": option.id},
        )
        response = self.client.post(
            reverse("vote_api", args=[poll.id]),
            {"option_id": option.id},
        )
        self.assertEqual(response.status_code, 400)

    # --- Mutable (ongoing) poll allows re-vote ---

    def test_mutable_poll_allows_revote(self):
        poll = Poll.objects.create(
            title="Mutable Poll",
            created_by=self.user,
            poll_type=PollType.PUBLIC,
            temporal_type=TemporalPollType.ONGOING,
            is_mutable=True,
        )
        option_a = PollOption.objects.create(poll=poll, text="Option A")
        option_b = PollOption.objects.create(poll=poll, text="Option B")

        self.client.force_login(self.user)

        # First vote
        self.client.post(
            reverse("vote_api", args=[poll.id]),
            {"option_id": option_a.id},
        )
        self.assertEqual(
            Vote.objects.filter(poll=poll, voter_did=self.user.username, is_current=True).count(),
            1,
        )

        # Re-vote on different option
        self.client.post(
            reverse("vote_api", args=[poll.id]),
            {"option_id": option_b.id},
        )
        current_vote = Vote.objects.filter(
            poll=poll, voter_did=self.user.username, is_current=True
        ).first()
        self.assertIsNotNone(current_vote)
        self.assertEqual(current_vote.option_id, option_b.id)

        # Old vote is still in the DB (historical record) but not current
        old_votes = Vote.objects.filter(
            poll=poll, voter_did=self.user.username, is_current=False
        )
        self.assertEqual(old_votes.count(), 1)
        self.assertEqual(old_votes.first().option_id, option_a.id)

        # Dynamic tally reflects only the current vote
        self.assertEqual(
            Vote.objects.filter(option=option_a, is_current=True).count(), 0
        )
        self.assertEqual(
            Vote.objects.filter(option=option_b, is_current=True).count(), 1
        )

    # --- Model validation ---

    def test_timed_poll_must_have_ends_at(self):
        from django.core.exceptions import ValidationError

        poll = Poll(
            title="Bad Timed Poll",
            created_by=self.user,
            temporal_type=TemporalPollType.TIMED,
            ends_at=None,
        )
        with self.assertRaises(ValidationError):
            poll.clean()

    def test_scheduled_poll_must_have_starts_at(self):
        from django.core.exceptions import ValidationError

        poll = Poll(
            title="Bad Scheduled Poll",
            created_by=self.user,
            temporal_type=TemporalPollType.SCHEDULED,
            starts_at=None,
            ends_at=timezone.now() + timezone.timedelta(hours=1),
        )
        with self.assertRaises(ValidationError):
            poll.clean()

    # --- Ongoing poll is_expired is always False ---

    def test_ongoing_poll_never_expires(self):
        poll = Poll.objects.create(
            title="Forever Poll",
            created_by=self.user,
            temporal_type=TemporalPollType.ONGOING,
        )
        self.assertFalse(poll.is_expired)
        self.assertTrue(poll.is_active_now)

    # --- Dynamic tally vs deprecated counter ---

    def test_dynamic_vote_count_matches_active_votes(self):
        poll = Poll.objects.create(
            title="Dynamic Tally Poll",
            created_by=self.user,
            poll_type=PollType.PUBLIC,
            temporal_type=TemporalPollType.ONGOING,
            is_mutable=True,
        )
        option = PollOption.objects.create(poll=poll, text="Tally Me")

        self.client.force_login(self.user)
        self.client.post(
            reverse("vote_api", args=[poll.id]),
            {"option_id": option.id},
        )

        option.refresh_from_db()
        # Deprecated field stays at 0
        self.assertEqual(option.votes, 0)
        # Dynamic property returns correct value
        self.assertEqual(option.dynamic_vote_count, 1)
