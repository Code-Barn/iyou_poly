import pytest
from django.contrib.auth import get_user_model
from django.test import Client

User = get_user_model()


@pytest.fixture
def test_user(db):
    return User.objects.create_user(username="testuser", password="testpass123")


@pytest.fixture
def client():
    return Client()


@pytest.fixture
def auth_client(test_user):
    c = Client()
    c.force_login(test_user)
    return c


@pytest.fixture
def sample_vc(test_user):
    return {
        "@context": ["https://www.w3.org/2018/credentials/v1"],
        "type": ["VerifiableCredential", "MembershipCredential"],
        "issuer": test_user.username,
        "issuanceDate": "2026-05-14T00:00:00Z",
        "credentialSubject": {
            "id": test_user.username,
            "name": test_user.username,
            "description": "Test credential",
        },
    }
