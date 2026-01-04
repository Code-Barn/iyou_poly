"""
Utility functions for working with Decentralized Identifiers (DIDs).
"""

from pydid import DID


def generate_did(method="key"):
    """
    Generate a new DID using the specified method.

    Args:
        method (str): The DID method to use (e.g., "key", "web").

    Returns:
        str: The generated DID.
    """
    # Placeholder for DID generation logic
    # In a real implementation, you would use a library like `didkit` or a custom method.
    return f"did:{method}:example123456789"


def validate_did(did_str):
    """
    Validate a DID string.

    Args:
        did_str (str): The DID string to validate.

    Returns:
        bool: True if the DID is valid, False otherwise.
    """
    try:
        DID.from_string(did_str)
        return True
    except Exception:
        return False


def create_did_document(did_str, verification_methods=None):
    """
    Create a DID Document for the given DID.

    Args:
        did_str (str): The DID string.
        verification_methods (list): List of verification methods (e.g., public keys).

    Returns:
        dict: The DID Document as a dictionary.
    """
    did_document = {
        "id": did_str,
        "verificationMethod": verification_methods or [],
        "authentication": [],
        "assertionMethod": [],
    }
    return did_document


def add_verification_method(
    did_document, method_id, method_type, controller, public_key
):
    """
    Add a verification method to a DID Document.

    Args:
        did_document (dict): The DID Document to update.
        method_id (str): The ID of the verification method.
        method_type (str): The type of verification method (e.g., "Ed25519VerificationKey2020").
        controller (str): The controller of the verification method.
        public_key (str): The public key associated with the method.

    Returns:
        dict: The updated DID Document.
    """
    verification_method = {
        "id": method_id,
        "type": method_type,
        "controller": controller,
        "publicKeyBase58": public_key,
    }
    did_document["verificationMethod"].append(verification_method)
    did_document["authentication"].append(method_id)
    did_document["assertionMethod"].append(method_id)
    return did_document


def resolve_did(did_str):
    """
    Resolve a DID to its DID Document.

    Args:
        did_str (str): The DID string to resolve.

    Returns:
        dict: The resolved DID Document, or None if resolution fails.
    """
    # Placeholder for DID resolution logic
    # In a real implementation, you would use a DID resolver or a library like `didkit`.
    return None
