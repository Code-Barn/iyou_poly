"""
Test utilities for accounts app tests.

This module provides utility functions and classes to simplify test writing
and reduce duplication across test files.
"""

import json
from typing import Any, Dict

from django.contrib.auth import get_user_model

User = get_user_model()


def create_test_user(
    username: str = "testuser",
    password: str = "testpass123",
    did: str = None,
    did_key: str = None,
) -> User:
    """
    Create a test user with DID and key.

    Args:
        username: Username for the test user
        password: Password for the test user
        did: DID for the test user (auto-generated if None)
        did_key: DID key for the test user (auto-generated if None)

    Returns:
        The created User object
    """
    if did is None:
        did = f"did:key:z6Mk{username}123456789"

    if did_key is None:
        did_key = json.dumps(
            {
                "kty": "OKP",
                "crv": "Ed25519",
                "x": f"{username}_public_key",
                "d": f"{username}_private_key",
            }
        )

    return User.objects.create_user(
        username=username,
        password=password,
        did=did,
        did_key=did_key,
    )


def create_test_vc(
    user: User,
    vc_type: str = "TestCredential",
    name: str = None,
    include_proof: bool = False,
) -> Dict[str, Any]:
    """
    Create a test verifiable credential.

    Args:
        user: User object to use as issuer and subject
        vc_type: Type of credential to create
        name: Name for the credential (auto-generated if None)
        include_proof: Whether to include a mock proof

    Returns:
        Dictionary representing the verifiable credential
    """
    vc = {
        "@context": ["https://www.w3.org/2018/credentials/v1"],
        "type": ["VerifiableCredential", vc_type],
        "issuer": user.did,
        "issuanceDate": "2023-01-01T00:00:00Z",
        "credentialSubject": {
            "id": user.did,
            "name": user.username,
            "description": f"{vc_type} for {user.username}",
        },
    }

    if include_proof:
        vc["proof"] = {
            "type": "Ed25519Signature2018",
            "proofPurpose": "assertionMethod",
            "verificationMethod": f"{user.did}#key-1",
            "created": "2023-01-01T00:00:00Z",
            "jws": "mock_jws_signature",
        }

    return vc


def create_vc_with_metadata(vc: Dict[str, Any], name: str = None) -> Dict[str, Any]:
    """
    Create a VC with metadata wrapper.

    Args:
        vc: The verifiable credential
        name: Custom name for the credential (auto-generated if None)

    Returns:
        Dictionary with credential and metadata
    """
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
    """
    Log in a test user.

    Args:
        client: Django test client
        username: Username to log in
        password: Password to log in

    Returns:
        Response from the login request
    """
    return client.login(username=username, password=password)
