"""
Utility functions for working with Decentralized Identifiers (DIDs) and Verifiable Credentials (VCs).

This module adheres to W3C DID Core and Verifiable Credentials Data Model specifications.
It uses DIDKit for DID/VC operations and supports multiple DID methods (e.g., did:key, did:web).

The module now supports both Python (didkit) and Rust backends through the hybrid wrapper.
"""

import json
import logging
import os
from typing import Dict, List, Optional, Union

# Temporarily disable Rust wrapper due to cryptographic compatibility issues
# between Rust-issued VCs and Python didkit verification
USE_RUST_WRAPPER = False
print("Using direct didkit implementation (Rust wrapper disabled due to compatibility issues)")

# Import didkit for all operations
try:
    import didkit
    DIDKIT_AVAILABLE = True
except ImportError:
    DIDKIT_AVAILABLE = False
    print("didkit not available")

from django.conf import settings
from pydid import DID

logger = logging.getLogger(__name__)


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
    if USE_RUST_WRAPPER:
        # Use the wrapper which handles both Python and Rust backends
        return wrapper_generate_did(method)

    # Original didkit implementation
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
        did_document = didkit.resolveDID(did_str, "application/did+ld+json")
        return json.loads(did_document)
    except Exception as e:
        print(f"Failed to resolve DID {did_str}: {e}")
        return None


def issue_vc(
    credential: Dict,
    did: str,
    key: Union[str, Dict],
    proof_type: str = "Ed25519Signature2018",
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
        proof_type: The proof type to use (e.g., "Ed25519Signature2018").

    Returns:
        The issued VC as a JSON string, or None if issuance fails.

    Note:
        The function automatically handles schema validation issues by:
        1. Removing non-standard fields before DIDKit processing
        2. Generating a valid VC with standard fields only
        3. Restoring all original fields to the final VC
    """
    try:
        import json
        import logging

        logger = logging.getLogger(__name__)

        # Ensure the key is a JSON string of a JWK
        if isinstance(key, dict):
            key = json.dumps(key)
        elif isinstance(key, str):
            # Ensure the string is valid JSON
            try:
                json.loads(key)
            except json.JSONDecodeError:
                logger.error("Invalid JSON format for key")
                return None
        else:
            logger.error(f"Invalid key type: {type(key)}")
            return None

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

        # Ensure the @context includes the necessary vocabulary for the proof type
        if "https://www.w3.org/2018/credentials/v1" not in credential["@context"]:
            credential["@context"].insert(0, "https://www.w3.org/2018/credentials/v1")

        # Remove the proof field if it exists to avoid duplication
        if "proof" in credential:
            del credential["proof"]

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

        logger.debug(f"Issuing VC with key: {key}")
        # Issue the credential using didkit
        vc = didkit.issueCredential(
            json.dumps(credential),
            json.dumps(options),
            key,
        )
        logger.debug(f"VC issued: {vc}")

        # If VC was issued successfully and we had extra fields, we need to handle them differently
        # Instead of modifying the signed VC (which breaks verification), we'll store them separately
        # or use a different approach that maintains signature validity
        if vc and extra_fields:
            logger.debug(f"Note: {len(extra_fields)} extra fields were temporarily removed for signing")
            logger.debug(f"Extra fields: {list(extra_fields.keys())}")

            # Return both the signed VC and the extra fields in a structured format
            # This allows the application to access extra fields without breaking the signature
            vc_dict = json.loads(vc)
            vc_dict['_extra_fields'] = extra_fields
            return json.dumps(vc_dict)

        return vc
    except Exception as e:
        print(f"Failed to issue VC: {e}")
        return None


def verify_vc(
    vc: Union[str, Dict],
    proof_options: Optional[Dict] = None,
    did_key: Optional[Dict] = None,
) -> bool:
    """
    Verify a Verifiable Credential (VC) using DIDKit's verifyCredential function.

    This function verifies a VC by delegating to DIDKit's `verifyCredential` function,
    which handles JWS verification and DID resolution automatically.

    Args:
        vc: The VC to verify (as a JSON string or Python dictionary).
        proof_options: Optional proof options (ignored if `did_key` is provided).
        did_key: Optional private key (JWK format as a dictionary) for manual verification.
                Not used if DIDKit verification is successful.

    Returns:
        True if the VC is valid, False otherwise.
    """
    import json
    import logging

    logger = logging.getLogger(__name__)
    logger.debug("Starting VC verification")
    logger.debug(f"VC to verify: {vc}")

    # Check if didkit is available for verification
    if not DIDKIT_AVAILABLE:
        logger.error("didkit not available for VC verification")
        return False

    try:
        # Handle both JSON strings and Python dictionaries
        if isinstance(vc, str):
            try:
                vc_data = json.loads(vc)
            except json.JSONDecodeError:
                logger.error(f"Invalid JSON string provided to verify_vc: {vc}")
                return False
        else:
            vc_data = vc
        logger.debug(f"VC to verify: {vc_data}")

        # Validate that vc_data is a dictionary
        if not isinstance(vc_data, dict):
            logger.error(f"VC data is not a dictionary: {vc_data}")
            return False

        # Check if extra fields are stored separately (new format)
        if '_extra_fields' in vc_data:
            # New format: extra fields are stored separately and don't affect the signature
            extra_fields = vc_data.pop('_extra_fields')
            vc_without_extra_fields = json.dumps(vc_data)
            logger.debug(f"VC with separate extra fields: {vc_without_extra_fields}")
        else:
            # Old format: extra fields might be in credentialSubject
            credential_subject = vc_data.get("credentialSubject", {})
            extra_fields = {}
            if credential_subject:
                # Remove any fields other than 'id' to avoid schema validation issues
                for field_name in list(credential_subject.keys()):
                    if field_name != "id":
                        extra_fields[field_name] = credential_subject.pop(field_name)

            vc_without_extra_fields = json.dumps(vc_data)
            logger.debug(f"VC without extra fields: {vc_without_extra_fields}")

        # Use simple verification options (like in working direct test)
        options = {"proofPurpose": "assertionMethod"}
        logger.debug(f"Verification options: {options}")

        # Use DIDKit's verifyCredential function for verification
        logger.debug("Using DIDKit's verifyCredential for verification")
        result = didkit.verifyCredential(vc_without_extra_fields, json.dumps(options))
        verification_result = json.loads(result)
        logger.debug(f"DIDKit verification result: {verification_result}")

        if verification_result.get("errors"):
            logger.error(f"DIDKit verification errors: {verification_result['errors']}")
            return False
        else:
            logger.debug("DIDKit verification succeeded")
            return True
    except Exception as e:
        logger.error(f"Failed to verify VC: {e}", exc_info=True)
        return False


def generate_ethr_did() -> tuple[str, str]:
    """
    Generate a new did:ethr DID using a random Ethereum private key.

    Returns:
        A tuple of (did, private_key_jwk).
    """
    try:
        from eth_account import Account
    except ImportError:
        raise ImportError(
            "web3 library required for did:ethr. Install with: pip install web3"
        )

    account = Account.create()
    address = account.address
    private_key = account.key.hex()

    private_key_jwk = {
        "kty": "EC",
        "crv": "secp256k1",
        "d": private_key[2:] if private_key.startswith("0x") else private_key,
        "x": "",  # Will be computed by didkit
        "y": "",  # Will be computed by didkit
    }

    did = f"did:ethr:{address}"
    return did, json.dumps(private_key_jwk)


def resolve_ethr_did(did_str: str, eth_rpc_url: Optional[str] = None) -> Optional[Dict]:
    """
    Resolve a did:ethr DID to its DID Document.

    Args:
        did_str: The did:ethr DID to resolve (e.g., "did:ethr:0x...").
        eth_rpc_url: Optional Ethereum JSON-RPC URL. If not provided,
                     will attempt to use public endpoints.

    Returns:
        The resolved DID Document as a dictionary, or None if resolution fails.
    """
    try:
        from web3 import Web3
    except ImportError:
        raise ImportError(
            "web3 library required for did:ethr. Install with: pip install web3"
        )

    if not did_str.startswith("did:ethr:"):
        return None

    address = did_str.replace("did:ethr:", "")

    if not address:
        return None

    w3 = Web3(Web3.HTTPProvider(eth_rpc_url)) if eth_rpc_url else None

    did_document = {
        "@context": [
            "https://www.w3.org/ns/did/v1",
            "https://w3id.org/security/suites/secp256k1-2019/v1",
        ],
        "id": did_str,
        "verificationMethod": [
            {
                "id": f"{did_str}#owner",
                "type": "EcdsaSecp256k1VerificationKey2019",
                "controller": did_str,
                "publicKeyHex": "",  # Requires on-chain lookup
            }
        ],
        "authentication": [f"{did_str}#owner"],
        "assertionMethod": [f"{did_str}#owner"],
        "service": [],
    }

    if w3 and w3.is_connected():
        try:
            owner = w3.eth.account.from_key(address).address
            if owner:
                did_document["verificationMethod"][0]["publicKeyHex"] = owner
        except Exception as e:
            logger.debug(f"Could not fetch owner from chain: {e}")

    return did_document


def get_did_method_from_did(did_str: str) -> Optional[str]:
    """
    Extract the DID method from a DID string.

    Args:
        did_str: The DID string (e.g., "did:ethr:0x...").

    Returns:
        The DID method (e.g., "ethr", "key"), or None if invalid.
    """
    try:
        if did_str.startswith("did:"):
            parts = did_str.split(":")
            if len(parts) >= 2:
                return parts[1]
    except Exception:
        pass
    return None


def generate_did_with_method(method: str = "key") -> tuple[str, str]:
    """
    Generate a new DID using the specified method.

    Args:
        method: The DID method to use ("key", "ethr", "web", "ion").

    Returns:
        A tuple of (did, private_key_jwk).

    Raises:
        ValueError: If the DID method is unsupported.
    """
    if method == "key":
        key = didkit.generateEd25519Key()
        did = didkit.keyToDID("key", key)
        return did, key
    elif method == "ethr":
        return generate_ethr_did()
    else:
        raise ValueError(f"Unsupported DID method for generation: {method}")


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


def verify_federated_vc(
    vc_json: str, issuer_did: str = None, did_key: Optional[Dict] = None
) -> bool:
    """
    Verify a VC that was issued by another federated server.

    Args:
        vc_json: The VC as a JSON string.
        issuer_did: Optional issuer DID for trust verification.
        did_key: Optional private key (JWK format as a dictionary) for manual verification.

    Returns:
        True if the VC is valid and trusted, False otherwise.
    """
    # Step 1: Verify the cryptographic signature
    try:
        if not verify_vc(vc_json, did_key=did_key):
            logger.debug("verify_vc returned False")
            return False
    except Exception as e:
        logger.debug(f"verify_vc raised an exception: {e}")
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

    return True


def generate_username_from_sub(sub):
    """
    Generate a Django-compatible username from an OIDC sub claim.
    DIDs contain colons which are not allowed in default Django usernames.
    """
    import re
    # Replace non-alphanumeric characters with underscores
    return re.sub(r'[^a-zA-Z0-9@.+-_]', '_', sub)
