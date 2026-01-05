"""
Utility functions for working with Decentralized Identifiers (DIDs) and Verifiable Credentials (VCs).

This module adheres to W3C DID Core and Verifiable Credentials Data Model specifications.
It uses DIDKit for DID/VC operations and supports multiple DID methods (e.g., did:key, did:web).
"""

import json
from typing import Dict, List, Optional, Union

import didkit
from pydid import DID


def generate_did(method: str = "key", key_type: str = "Ed25519") -> str:
    """
    Generate a new DID using the specified method and key type.

    Args:
        method: The DID method to use (e.g., "key", "web").
        key_type: The key type to use (e.g., "Ed25519", "Secp256k1").

    Returns:
        The generated DID.

    Raises:
        ValueError: If the DID method or key type is unsupported.
    """
    if method == "key":
        if key_type == "Ed25519":
            key = didkit.generateEd25519Key()
        elif key_type == "Secp256k1":
            key = didkit.generateSecp256k1Key()
        else:
            raise ValueError(f"Unsupported key type: {key_type}")
        did = didkit.keyToDID(method, key)
        return did
    else:
        raise ValueError(f"Unsupported DID method: {method}")


def validate_did(did_str: str) -> bool:
    """
    Validate a DID string according to the W3C DID Core specification.

    Args:
        did_str: The DID string to validate.

    Returns:
        True if the DID is valid, False otherwise.
    """
    try:
        DID.from_string(did_str)
        return True
    except Exception:
        return False


def create_did_document(
    did_str: str,
    verification_methods: Optional[List[Dict]] = None,
    services: Optional[List[Dict]] = None,
) -> Dict:
    """
    Create a DID Document for the given DID according to W3C DID Core specification.

    Args:
        did_str: The DID string.
        verification_methods: List of verification methods (e.g., public keys).
        services: List of services associated with the DID.

    Returns:
        The DID Document as a dictionary.
    """
    did_document = {
        "@context": [
            "https://www.w3.org/ns/did/v1",
            "https://w3id.org/security/suites/ed25519-2020/v1",
        ],
        "id": did_str,
        "verificationMethod": verification_methods or [],
        "authentication": [],
        "assertionMethod": [],
        "service": services or [],
    }
    return did_document


def add_verification_method(
    did_document: Dict,
    method_id: str,
    method_type: str,
    controller: str,
    public_key: str,
    purposes: Optional[List[str]] = None,
) -> Dict:
    """
    Add a verification method to a DID Document according to W3C DID Core specification.

    Args:
        did_document: The DID Document to update.
        method_id: The ID of the verification method.
        method_type: The type of verification method (e.g., "Ed25519VerificationKey2020").
        controller: The controller of the verification method.
        public_key: The public key associated with the method.
        purposes: List of purposes for the verification method (e.g., ["authentication", "assertionMethod"]).

    Returns:
        The updated DID Document.
    """
    verification_method = {
        "id": method_id,
        "type": method_type,
        "controller": controller,
        "publicKeyBase58": public_key,
    }
    did_document["verificationMethod"].append(verification_method)

    if purposes is None:
        purposes = ["authentication", "assertionMethod"]

    for purpose in purposes:
        if purpose not in did_document:
            did_document[purpose] = []
        if method_id not in did_document[purpose]:
            did_document[purpose].append(method_id)

    return did_document


def resolve_did(did_str: str) -> Optional[Dict]:
    """
    Resolve a DID to its DID Document using DIDKit according to W3C DID Resolution specification.

    Args:
        did_str: The DID string to resolve.

    Returns:
        The resolved DID Document as a dictionary, or None if resolution fails.
    """
    try:
        did_document = didkit.resolve_did(did_str, "application/did+ld+json")
        return json.loads(did_document)
    except Exception as e:
        print(f"Failed to resolve DID {did_str}: {e}")
        return None


def issue_vc(
    credential: Dict,
    did: str,
    key: str,
    proof_type: str = "Ed25519Signature2020",
) -> Optional[str]:
    """
    Issue a Verifiable Credential (VC) using DIDKit.

    Args:
        credential: The credential to issue (as a dictionary).
        did: The DID of the issuer.
        key: The private key of the issuer (in JWK format).
        proof_type: The proof type to use (e.g., "Ed25519Signature2020").

    Returns:
        The issued VC as a JSON string, or None if issuance fails.
    """
    try:
        vc = didkit.issueCredential(
            json.dumps(credential),
            json.dumps({"proofPurpose": "assertionMethod"}),
            key,
        )
        return vc
    except Exception as e:
        print(f"Failed to issue VC: {e}")
        return None


def verify_vc(vc: str, proof_options: Optional[Dict] = None) -> bool:
    """
    Verify a Verifiable Credential (VC) using DIDKit.

    Args:
        vc: The VC to verify (as a JSON string).
        proof_options: Optional proof options (as a dictionary).

    Returns:
        True if the VC is valid, False otherwise.
    """
    try:
        options = proof_options or {"proofPurpose": "assertionMethod"}
        result = didkit.verifyCredential(vc, json.dumps(options))
        result = json.loads(result)
        return not result.get("errors")
    except Exception as e:
        print(f"Failed to verify VC: {e}")
        return False
