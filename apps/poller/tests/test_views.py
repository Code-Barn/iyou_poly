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
from django.test import TestCase, override_settings
from django.urls import reverse

from apps.poller.models import Poll, PollOption, PollType

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
        self.option.refresh_from_db()
        self.assertEqual(self.option.votes, 1)

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
