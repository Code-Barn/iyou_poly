import json
from typing import Any, Dict

from django.contrib.auth import get_user_model

User = get_user_model()


def create_test_user(
    username: str = "testuser",
    password: str = "testpass123",
) -> User:
    return User.objects.create_user(
        username=username,
        password=password,
    )


def create_test_vc(
    user: User,
    vc_type: str = "TestCredential",
    include_proof: bool = False,
) -> Dict[str, Any]:
    vc = {
        "@context": ["https://www.w3.org/2018/credentials/v1"],
        "type": ["VerifiableCredential", vc_type],
        "issuer": user.username,
        "issuanceDate": "2023-01-01T00:00:00Z",
        "credentialSubject": {
            "id": user.username,
            "name": user.username,
            "description": f"{vc_type} for {user.username}",
        },
    }

    if include_proof:
        vc["proof"] = {
            "type": "Ed25519Signature2018",
            "proofPurpose": "assertionMethod",
            "verificationMethod": f"{user.username}#key-1",
            "created": "2023-01-01T00:00:00Z",
            "jws": "mock_jws_signature",
        }

    return vc


def create_vc_with_metadata(vc: Dict[str, Any], name: str = None) -> Dict[str, Any]:
    if name is None:
        vc_types = vc.get("type", [])
        if len(vc_types) > 1:
            name = vc_types[1]
        else:
            name = "Verifiable Credential"

    return {
        "credential": vc,
        "name": name,
        "added_date": "2023-01-01T00:00:00.000000Z",
    }


def login_test_user(client, username: str = "testuser", password: str = "testpass123"):
    return client.login(username=username, password=password)
