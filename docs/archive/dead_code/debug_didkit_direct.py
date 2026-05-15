#!/usr/bin/env python3

import didkit
import json

def test_didkit_direct():
    """Test didkit directly to isolate the issue"""
    
    print("=== Direct didkit test ===")
    
    # Generate a key
    key = {
        'kty': 'OKP',
        'crv': 'Ed25519',
        'x': '8ggY1h8ZQ1JlP5YlXNGmZRXjL3u5qLzIni6bGdXF9tE',
        'd': 'YMpPxMuQZQXlwgnHBOEL0HOKCxT5ttwFCrHiIn4mh-k'
    }
    
    key_json = json.dumps(key)
    
    # Generate DID from key
    did = didkit.keyToDID('key', key_json)
    print(f"Generated DID: {did}")
    
    # Create credential
    credential = {
        '@context': ['https://www.w3.org/2018/credentials/v1'],
        'type': ['VerifiableCredential', 'AuthenticationCredential'],
        'issuer': did,
        'issuanceDate': '2023-01-01T00:00:00Z',
        'credentialSubject': {
            'id': did
        }
    }
    
    # Create options
    verification_method = f"{did}#{did.split(':')[-1]}"
    options = {
        'proofPurpose': 'assertionMethod',
        'verificationMethod': verification_method
    }
    
    print(f"Verification method: {verification_method}")
    
    # Issue VC
    print("Issuing VC...")
    vc_json = didkit.issueCredential(
        json.dumps(credential),
        json.dumps(options),
        key_json
    )
    
    print("VC issued successfully")
    vc = json.loads(vc_json)
    print(f"VC proof type: {vc.get('proof', {}).get('type')}")
    print(f"VC JWS: {vc.get('proof', {}).get('jws')[:50]}...")
    
    # Verify VC
    print("\nVerifying VC...")
    verification_options = {'proofPurpose': 'assertionMethod'}
    
    result = didkit.verifyCredential(vc_json, json.dumps(verification_options))
    result_dict = json.loads(result)
    
    print(f"Verification result: {result_dict}")
    
    if result_dict.get('errors'):
        print(f"Errors: {result_dict.get('errors')}")
        return False
    else:
        print("✓ Verification successful!")
        return True

if __name__ == '__main__':
    success = test_didkit_direct()
    sys.exit(0 if success else 1)