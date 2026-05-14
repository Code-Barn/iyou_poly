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
