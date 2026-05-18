# VC Utilities - Quick Reference

## Overview

This directory contains utility functions for working with Decentralized Identifiers (DIDs) and Verifiable Credentials (VCs) in the Poly project.

## Key Functions

### `generate_did(method: str = "key", key_type: str = "Ed25519") -> str`
Generates a new DID using the specified method and key type.

### `validate_did(did_str: str) -> bool`
Validates a DID string according to W3C DID Core specification.

### `issue_vc(credential: Dict, did: str, key: str, proof_type: str = "Ed25519Signature2020") -> Optional[str]`
**Main function** - Issues a Verifiable Credential using DIDKit.

### `verify_vc(vc: str, proof_options: Optional[Dict] = None) -> bool`
Verifies a Verifiable Credential using DIDKit.

## VC Generation Fix

The `issue_vc` function has been enhanced to handle the "key expansion failed" error by automatically managing extra fields in the credential subject.

### What Changed

- **Before**: VC generation failed when credentialSubject contained extra fields (name, email, etc.)
- **After**: Extra fields are automatically preserved while maintaining W3C compliance

### Usage Example

```python
from apps.accounts.utils.did_utils import issue_vc

credential = {
    "@context": ["https://www.w3.org/2018/credentials/v1"],
    "type": ["VerifiableCredential", "AuthenticationCredential"],
    "issuer": user.did,
    "credentialSubject": {
        "id": user.did,
        "name": user.username,  # Automatically preserved
        "email": user.email,    # Automatically preserved
    },
}

vc = issue_vc(credential, user.did, user.did_key)
```

## Documentation

For detailed documentation, see:
- [VcGenerationDocs.md](VcGenerationDocs.md) - Complete technical documentation
- [DIDKit Documentation](https://github.com/spruid/didkit)
- [W3C Verifiable Credentials](https://www.w3.org/TR/vc-data-model/)

## Testing

Run tests with:
```bash
uv run python test_fixed_vc.py
```

## Support

For issues or questions, refer to the main project documentation or contact the development team.
