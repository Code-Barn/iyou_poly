#!/usr/bin/env python3

import os
import sys
import django

# Add the project directory to the Python path
sys.path.insert(0, '/home/user/CODE_BASE/polly')

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from apps.accounts.utils.did_utils import issue_vc
import json

def debug_key_issue():
    """Debug the key issue step by step"""
    
    # Test data
    did = "did:key:z6MkgjRBJwTFK4qP2W2uVZ9mLLvWht33FciXNksQUc87AKEm"
    key = {
        'kty': 'OKP',
        'crv': 'Ed25519',
        'x': '8ggY1h8ZQ1JlP5YlXNGmZRXjL3u5qLzIni6bGdXF9tE',
        'd': 'YMpPxMuQZQXlwgnHBOEL0HOKCxT5ttwFCrHiIn4mh-k'
    }
    
    credential = {
        '@context': ['https://www.w3.org/2018/credentials/v1'],
        'type': ['VerifiableCredential', 'AuthenticationCredential'],
        'issuer': did,
        'issuanceDate': '2023-01-01T00:00:00Z',
        'credentialSubject': {
            'id': did
        }
    }
    
    print("Step 1: Test simple VC (no extra fields)")
    vc_json = issue_vc(credential, did, key)
    
    if vc_json:
        print("✓ Simple VC issued successfully")
        
        # Test verification
        from apps.accounts.utils.did_utils import verify_vc
        verification_result = verify_vc(vc_json)
        print(f"Simple VC verification: {verification_result}")
        
        if verification_result:
            print("✓ Simple VC verification successful")
        else:
            print("✗ Simple VC verification failed")
            
        # Now test with extra fields
        print("\nStep 2: Test VC with extra fields")
        credential_with_extras = dict(credential)
        credential_with_extras['credentialSubject'] = {
            'id': did,
            'name': 'testuser',
            'email': 'test@example.com'
        }
        
        vc_json_extras = issue_vc(credential_with_extras, did, key)
        
        if vc_json_extras:
            print("✓ VC with extras issued successfully")
            vc_extras = json.loads(vc_json_extras)
            print(f"VC structure: {list(vc_extras.keys())}")
            print(f"CredentialSubject: {vc_extras.get('credentialSubject')}")
            print(f"Extra fields: {vc_extras.get('_extra_fields')}")
            
            # Test verification
            verification_result_extras = verify_vc(vc_json_extras)
            print(f"VC with extras verification: {verification_result_extras}")
        else:
            print("✗ VC with extras failed to issue")
    else:
        print("✗ Simple VC failed to issue")

if __name__ == '__main__':
    debug_key_issue()