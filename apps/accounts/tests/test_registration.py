# polly/apps/accounts/tests/test_registration.py
import json
import re

from playwright.sync_api import expect, sync_playwright


def test_user_registration_and_did_generation():
    """Test that a new user can register and a DID is generated."""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()

        # Navigate to the registration page
        page.goto("http://localhost:8000/register/")

        # Fill out the registration form
        page.fill("input[name='username']", "testuser")
        page.fill("input[name='password1']", "testpass123")
        page.fill("input[name='password2']", "testpass123")

        # Submit the form
        page.click("button[type='submit']")

        # Verify that the user is redirected to the poll list
        expect(page).to_have_url(re.compile(r"http://localhost:8000/$"))

        # Verify that the user is logged in
        expect(page.locator("text=Logged in as testuser")).to_be_visible()

        # Navigate to the VC management page
        page.click("text=Credentials")
        expect(page).to_have_url("http://localhost:8000/accounts/vcs/")

        # Verify that the user has a DID and VC
        expect(page.locator("text=Authentication Credential")).to_be_visible()
        expect(page.locator("pre")).to_contain_text("did:key:")

        # Close the browser
        browser.close()


def test_did_based_login():
    """Test that a user can log in using their DID and VC."""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()

        # Navigate to the DID login page
        page.goto("http://localhost:8000/login/did/")

        # Get a pre-registered user's DID and VC from the database
        # In a real test, you would fetch this from the database or use a fixture
        did = "did:key:example123456789"  # Replace with a real DID from the database
        vc = json.dumps(
            {
                "@context": ["https://www.w3.org/2018/credentials/v1"],
                "type": ["VerifiableCredential", "AuthenticationCredential"],
                "issuer": did,
                "credentialSubject": {
                    "id": did,
                    "name": "testuser",
                },
            }
        )
        vc_proof = json.dumps(
            {
                "type": "Ed25519Signature2020",
                "proofPurpose": "authentication",
            }
        )

        # Fill out the DID login form
        page.fill("input[name='did']", did)
        page.fill("textarea[name='vc']", vc)
        page.fill("textarea[name='vc_proof']", vc_proof)

        # Submit the form
        page.click("button[type='submit']")

        # Verify that the user is redirected to the poll list
        expect(page).to_have_url(re.compile(r"http://localhost:8000/$"))

        # Verify that the user is logged in
        expect(page.locator("text=Logged in as testuser")).to_be_visible()

        # Close the browser
        browser.close()
