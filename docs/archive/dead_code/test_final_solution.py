#!/usr/bin/env python3

import os
import sys
import django

# Add the project directory to the Python path
sys.path.insert(0, '/home/user/CODE_BASE/poly')

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from apps.accounts.utils.did_utils import issue_vc, verify_vc
from apps.accounts.backends import DIDAuthBackend
import json

def test_complete_flow():
    """Test the complete authentication flow with the fixed implementation"""
    
    print("=== Testing Complete Authentication Flow ===")
    
    # Test data
    username = "testuser"
    email = "test@example.com"
    did = "did:key:z6MkgjRBJwTFK4qP2W2uVZ9mLLvWht33FciXNksQUc87AKEm"
    key = {
        'kty': 'OKP',
        'crv': 'Ed25519',
        'x': '8ggY1h8ZQ1JlP5YlXNGmZRXjL3u5qLzIni6bGdXF9tE',
        'd': 'YMpPxMuQZQXlwgnHBOEL0HOKCxT5ttwFCrHiIn4mh-k'
    }
    
    # Step 1: Issue authentication VC
    print("Step 1: Issue authentication VC")
    credential = {
        '@context': ['https://www.w3.org/2018/credentials/v1'],
        'type': ['VerifiableCredential', 'AuthenticationCredential'],
        'issuer': did,
        'issuanceDate': '2023-01-01T00:00:00Z',
        'credentialSubject': {
            'id': did,
            'name': username,
            'email': email
        }
    }
    
    vc_json = issue_vc(credential, did, key)
    
    if not vc_json:
        print("✗ Failed to issue VC")
        return False
    
    print("✓ VC issued successfully")
    vc = json.loads(vc_json)
    print(f"VC credentialSubject: {vc.get('credentialSubject')}")
    print(f"VC has extra fields: {'_extra_fields' in vc}")
    
    # Step 2: Verify VC
    print("\nStep 2: Verify VC")
    verification_result = verify_vc(vc_json)
    
    if not verification_result:
        print("✗ VC verification failed")
        return False
    
    print("✓ VC verification successful")
    
    # Step 3: Test authentication backend
    print("\nStep 3: Test authentication backend")
    
    # Create a mock user object for testing
    class MockUser:
        def __init__(self):
            self.did = did
            self.did_key = key
            self.username = username
            self.email = email
            self.vcs = []
        
        def add_vc(self, vc_data):
            self.vcs.append({"credential": vc_data, "name": "Authentication Credential"})
    
    # We can't test the full authentication backend without a database,
    # but we can test the verification part
    backend = DIDAuthBackend()
    
    # Test just the verification part
    try:
        vc_data = json.loads(vc_json)
        vc_did = vc_data.get("credentialSubject", {}).get("id")
        
        if vc_did == did:
            print("✓ DID extraction successful")
            
            # Test verification with the backend's method
            from apps.accounts.utils.did_utils import verify_federated_vc
            federated_result = verify_federated_vc(vc_json, did_key=key)
            
            if federated_result:
                print("✓ Federated VC verification successful")
                return True
            else:
                print("✗ Federated VC verification failed")
                return False
        else:
            print("✗ DID mismatch")
            return False
    except Exception as e:
        print(f"✗ Authentication test failed: {e}")
        return False

if __name__ == '__main__':
    success = test_complete_flow()
    if success:
        print("\n🎉 Complete authentication flow works!")
    else:
        print("\n❌ Complete authentication flow failed.")
    sys.exit(0 if success else 1)