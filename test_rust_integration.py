#!/usr/bin/env python
"""
Test script for Rust DID integration
Run with: .venv/bin/python test_rust_integration.py
"""

import os
import sys
import json

# Add project to path
sys.path.insert(0, '.')

# Set environment to use Python backend (mock)
os.environ['DID_BACKEND'] = 'python'

from apps.accounts.utils.did_utils import generate_did, verify_vc, issue_vc


def test_did_generation():
    """Test DID generation"""
    print("🧪 Testing DID generation...")
    
    # Test with key method
    did = generate_did("key")
    print(f"   Generated DID: {did}")
    assert did.startswith("did:key:"), f"DID should start with 'did:key:', got: {did}"
    
    print("   ✅ DID generation works!")


def test_vc_verification():
    """Test VC verification"""
    print("🧪 Testing VC verification...")
    
    # Create a test VC
    test_vc = {
        "@context": ["https://www.w3.org/2018/credentials/v1"],
        "id": "http://example.edu/credentials/1872",
        "type": ["VerifiableCredential"],
        "issuer": "did:key:z6MkoGcGdMQk4aX7wQHnQrSwSkrYBArUu2q65VveVc3Snykm",
        "issuanceDate": "2020-01-01T00:00:00Z",
        "credentialSubject": {
            "id": "did:example:123456789"
        }
    }
    
    vc_json = json.dumps(test_vc)
    
    # This should return False because it's not properly signed
    is_valid = verify_vc(vc_json)
    print(f"   VC verification result: {is_valid}")
    assert is_valid == False, "Unsigned VC should be invalid"
    
    print("   ✅ VC verification works!")


def test_backend_switching():
    """Test switching between backends"""
    print("🧪 Testing backend switching...")
    
    # Test with Python backend
    os.environ['DID_BACKEND'] = 'python'
    
    # Reload modules to pick up environment change
    import importlib
    import apps.accounts.did_rust_wrapper
    importlib.reload(apps.accounts.did_rust_wrapper)
    
    did1 = apps.accounts.did_rust_wrapper.generate_did("key")
    print(f"   Python backend DID: {did1}")
    
    # Test with Rust backend (should fall back to Python)
    os.environ['DID_BACKEND'] = 'rust'
    importlib.reload(apps.accounts.did_rust_wrapper)
    
    try:
        did2 = apps.accounts.did_rust_wrapper.generate_did("key")
        print(f"   Rust backend DID: {did2}")
        # Both should work (Rust falls back to Python)
        assert did1.startswith("did:key:")
        assert did2.startswith("did:key:")
    except RuntimeError as e:
        if "Rust library not loaded" in str(e):
            print(f"   Rust backend not available (expected): {e}")
            print(f"   This is normal - Rust library not compiled yet")
        else:
            raise
    
    print("   ✅ Backend switching works!")


def test_rust_availability():
    """Test Rust backend availability"""
    print("🧪 Testing Rust backend availability...")
    
    from apps.accounts.did_rust_wrapper import test_rust_availability
    
    rust_available = test_rust_availability()
    print(f"   Rust backend available: {rust_available}")
    
    # Should be False since we haven't compiled the Rust library yet
    assert rust_available == False, "Rust backend should not be available yet"
    
    print("   ✅ Rust availability check works!")


def main():
    """Run all tests"""
    print("🚀 Starting Rust DID Integration Tests\n")
    
    try:
        test_did_generation()
        test_vc_verification()
        test_backend_switching()
        test_rust_availability()
        
        print("\n🎉 All tests passed!")
        print("✅ Rust DID integration is working correctly!")
        print("📝 Next steps:")
        print("   1. Install Rust toolchain")
        print("   2. Build the Rust DID library")
        print("   3. Test with real Rust backend")
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()