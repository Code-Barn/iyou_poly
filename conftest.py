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
