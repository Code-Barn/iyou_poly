#!/usr/bin/env python
"""
Test script to verify the VC using the didkit Python library directly.
"""

import json

import didkit


def test_didkit_verify():
    """Test VC verification using didkit directly."""
    # Read the test VC from the file
    with open("/home/user/CODE_BASE/polly/test_vc.json", "r") as f:
        vc_json = f.read()

    print("VC JSON:")
    print(vc_json)
    print()

    # Verify the VC using didkit
    try:
        result = didkit.verifyCredential(vc_json, "{}")
        result = json.loads(result)
        print(f"Verification result: {result}")
        print(f"Verification errors: {result.get('errors')}")
        print(f"Verification warnings: {result.get('warnings')}")
        print(f"Verification checks: {result.get('checks')}")
        print(f"Verification status: {not result.get('errors')}")
    except Exception as e:
        print(f"Failed to verify VC: {e}")


if __name__ == "__main__":
    test_didkit_verify()
