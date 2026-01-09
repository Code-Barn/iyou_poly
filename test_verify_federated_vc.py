#!/usr/bin/env python
"""
Test script to verify the VC using the verify_federated_vc function.
"""

import json
import os
import sys

import django

# Configure Django settings
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from apps.accounts.utils.did_utils import verify_federated_vc


def test_verify_federated_vc():
    """Test VC verification using verify_federated_vc."""
    # Read the test VC from the file
    with open("/home/user/CODE_BASE/polly/test_vc.json", "r") as f:
        vc_json = f.read()

    print("VC JSON:")
    print(vc_json)
    print()

    # Parse the VC to extract the issuer DID
    vc_data = json.loads(vc_json)
    issuer_did = vc_data.get("issuer")

    print(f"Issuer DID: {issuer_did}")
    print()

    # Verify the VC using verify_federated_vc
    try:
        is_valid = verify_federated_vc(vc_json, issuer_did)
        print(f"Verification result: {is_valid}")

        if is_valid:
            print("VC is valid!")
        else:
            print("VC is invalid!")
    except Exception as e:
        print(f"Error: {e}")
        print(f"Failed to verify VC: {e}")


if __name__ == "__main__":
    test_verify_federated_vc()
