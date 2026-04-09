"""
Test the DID Rust Wrapper
"""

import os
import json

# Set to use Python backend for testing
os.environ['DID_BACKEND'] = 'python'

from . import generate_did, verify_vc, issue_vc, test_rust_availability


def test_python_backend():
    """Test that Python backend works"""
    print("Testing Python backend...")
    
    # Test DID generation
    did = generate_did("key")
    print(f"Generated DID: {did}")
    assert did.startswith("did:key:")
    
    # Test VC verification
    test_vc = {
        "@context": ["https://www.w3.org/2018/credentials/v1"],
        "id": "http://example.edu/credentials/1872",
        "type": ["VerifiableCredential"],
        "issuer": did,
        "issuanceDate": "2020-01-01T00:00:00Z",
        "credentialSubject": {
            "id": "did:example:123456789"
        }
    }
    
    vc_json = json.dumps(test_vc)
    # This should fail because it's not properly signed
    is_valid = verify_vc(vc_json)
    print(f"VC verification result: {is_valid}")
    
    # Test Rust availability (should be False)
    rust_available = test_rust_availability()
    print(f"Rust backend available: {rust_available}")
    assert not rust_available
    
    print("✅ Python backend tests passed!")


def test_backend_switching():
    """Test switching between backends"""
    print("Testing backend switching...")
    
    # Test with Python backend
    os.environ['DID_BACKEND'] = 'python'
    from importlib import reload
    import apps.accounts.did_rust_wrapper
    reload(apps.accounts.did_rust_wrapper)
    
    did1 = apps.accounts.did_rust_wrapper.generate_did("key")
    assert did1.startswith("did:key:")
    
    # Test with Rust backend (should fall back to Python)
    os.environ['DID_BACKEND'] = 'rust'
    reload(apps.accounts.did_rust_wrapper)
    
    did2 = apps.accounts.did_rust_wrapper.generate_did("key")
    assert did2.startswith("did:key:")
    
    print("✅ Backend switching tests passed!")


if __name__ == "__main__":
    test_python_backend()
    test_backend_switching()
    print("🎉 All tests passed!")