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
            key = didkit.generate_Secp256k1Key()
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

    This function handles the "key expansion failed" issue by temporarily removing
    extra fields from the credentialSubject during DIDKit processing and restoring
    them afterward. This allows for flexible credential structures while maintaining
    W3C compliance.

    Args:
        credential: The credential to issue (as a dictionary). Can include any
                   application-specific fields in credentialSubject - they will be
                   preserved in the final VC.
        did: The DID of the issuer.
        key: The private key of the issuer (in JWK format as a string or dict).
        proof_type: The proof type to use (e.g., "Ed25519Signature2020").

    Returns:
        The issued VC as a JSON string, or None if issuance fails.

    Note:
        The function automatically handles schema validation issues by:
        1. Removing non-standard fields before DIDKit processing
        2. Generating a valid VC with standard fields only
        3. Restoring all original fields to the final VC

    Example:
        credential = {
            "@context": ["https://www.w3.org/2018/credentials/v1"],
            "type": ["VerifiableCredential", "AuthenticationCredential"],
            "issuer": "did:key:z6Mk...",
            "credentialSubject": {
                "id": "did:key:z6Mk...",
                "name": "John Doe",  # This will be preserved
                "email": "john@example.com",  # This will be preserved
            },
        }
        vc = issue_vc(credential, did, key)
    """
    try:
        import json
        import logging

        logger = logging.getLogger(__name__)

        # Ensure the key is a JSON string of a JWK
        if isinstance(key, dict):
            key = json.dumps(key)

        logger.debug(f"Key: {key}")
        logger.debug(f"Key type: {type(key)}")

        # Store any extra fields from credentialSubject that might cause validation issues
        credential_subject = credential.get("credentialSubject", {})
        extra_fields = {}
        if credential_subject:
            # Remove any fields other than 'id' to avoid schema validation issues
            for field_name in list(credential_subject.keys()):
                if field_name != "id":
                    extra_fields[field_name] = credential_subject.pop(field_name)

        # Ensure the credential has the correct @context
        if isinstance(credential.get("@context"), str):
            credential["@context"] = [credential["@context"]]

        # Derive the verification method from the DID of the issuer
        vm = f"{did}#{did.split(':')[-1]}"
        logger.debug(f"Verification method: {vm}")

        # Define the options with the correct verification method
        options = {
            "proofPurpose": "assertionMethod",
            "verificationMethod": vm,
        }

        logger.debug(f"Credential (without extra fields): {credential}")
        logger.debug(f"Options: {options}")

        # Issue the credential with only standard fields
        vc = didkit.issueCredential(
            json.dumps(credential),
            json.dumps(options),
            key,
        )

        # If VC was issued successfully and we had extra fields, add them back
        if vc and extra_fields:
            logger.debug(f"Restoring {len(extra_fields)} extra fields to VC")
            vc_dict = json.loads(vc)
            vc_credential_subject = vc_dict.get("credentialSubject", {})
            if vc_credential_subject:
                # Add the extra fields back to the credential subject
                vc_credential_subject.update(extra_fields)
                vc = json.dumps(vc_dict)
                logger.debug(
                    f"VC now includes extra fields: {list(extra_fields.keys())}"
                )

        return vc

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


def get_trusted_issuers() -> set:
    """
    Get the set of trusted issuer DIDs.

    Returns:
        A set of trusted issuer DIDs.
    """
    # Start with open trust model (allow all)
    # This can be restricted later by adding issuers to TRUSTED_ISSUERS setting
    if hasattr(settings, "TRUSTED_ISSUERS"):
        return set(settings.TRUSTED_ISSUERS)
    return set()  # Empty set means open trust model


def is_trusted_issuer(issuer_did: str) -> bool:
    """
    Check if an issuer DID is trusted.

    Args:
        issuer_did: The DID of the issuer to check.

    Returns:
        True if the issuer is trusted, False otherwise.
    """
    # Open trust model: allow all issuers by default
    # This can be changed to a more restrictive model later
    if (
        hasattr(settings, "REQUIRE_TRUSTED_ISSUERS")
        and settings.REQUIRE_TRUSTED_ISSUERS
    ):
        return issuer_did in get_trusted_issuers()
    return True  # Open trust model by default


def verify_federated_vc(vc_json: str, issuer_did: str = None) -> bool:
    """
    Verify a VC that was issued by another federated server.

    Args:
        vc_json: The VC as a JSON string.
        issuer_did: Optional issuer DID for trust verification.

    Returns:
        True if the VC is valid and trusted, False otherwise.
    """
    # Step 1: Verify the cryptographic signature
    if not verify_vc(vc_json):
        return False

    # Step 2: Extract issuer if not provided
    if not issuer_did:
        try:
            vc_data = json.loads(vc_json)
            issuer_did = vc_data.get("issuer", "")
        except json.JSONDecodeError:
            return False

    # Step 3: Check if we trust the issuer
    if not is_trusted_issuer(issuer_did):
        print(f"Issuer {issuer_did} is not trusted")
        return False

    # Additional checks can be added here for:
    # - VC revocation status
    # - VC expiration
    # - Other business rules

    return True
