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
    import json

    from django.contrib.auth import get_user_model

    from apps.accounts.utils.did_utils import issue_vc

    # Create a test user and generate DID/VC
    User = get_user_model()
    user = User.objects.create_user(
        username="testuser_did_login", password="testpass123"
    )
    user.did = "did:key:test_did_login"
    user.did_method = "key"
    user.did_key = json.dumps(
        json.loads('{"kty": "OKP", "crv": "Ed25519", "x": "test_key"}')
    )
    user.save()

    # Issue an authentication VC for the test user
    credential = {
        "@context": ["https://www.w3.org/2018/credentials/v1"],
        "type": ["VerifiableCredential", "AuthenticationCredential"],
        "issuer": user.did,
        "issuanceDate": "2023-01-01T00:00:00Z",
        "credentialSubject": {
            "id": user.did,
            "name": user.username,
        },
    }
    vc = issue_vc(credential, user.did, user.did_key)
    if vc:
        user.add_vc(json.loads(vc))

    # Extract the VC proof from the user's VC
    vc_data = user.get_authentication_vc()
    vc_proof = json.dumps(vc_data.get("proof", {}))

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()

        # Navigate to the DID login page
        page.goto("http://localhost:8000/login/did/")

        # Use the test user's DID and VC for login
        did = user.did
        vc = json.dumps(vc_data)

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


def test_voting_flow():
    """Test that a user can create a poll and vote on it."""
    import json

    from django.contrib.auth import get_user_model

    from apps.accounts.utils.did_utils import issue_vc
    from apps.poller.models import Poll, PollOption

    # Create a test user and generate DID/VC
    User = get_user_model()
    user = User.objects.create_user(username="testuser_voting", password="testpass123")
    user.did = "did:key:test_voting"
    user.did_method = "key"
    user.did_key = json.dumps(
        json.loads('{"kty": "OKP", "crv": "Ed25519", "x": "test_key_voting"}')
    )
    user.save()

    # Issue an authentication VC for the test user
    credential = {
        "@context": ["https://www.w3.org/2018/credentials/v1"],
        "type": ["VerifiableCredential", "AuthenticationCredential"],
        "issuer": user.did,
        "issuanceDate": "2023-01-01T00:00:00Z",
        "credentialSubject": {
            "id": user.did,
            "name": user.username,
        },
    }
    vc = issue_vc(credential, user.did, user.did_key)
    if vc:
        user.add_vc(json.loads(vc))

    # Create a test poll
    poll = Poll.objects.create(
        question="Test Poll",
        created_by=user,
    )
    PollOption.objects.create(poll=poll, text="Option 1")
    PollOption.objects.create(poll=poll, text="Option 2")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()

        # Navigate to the DID login page
        page.goto("http://localhost:8000/login/did/")

        # Use the test user's DID and VC for login
        vc_data = user.get_authentication_vc()
        did = user.did
        vc = json.dumps(vc_data)

        # Extract the VC proof from the user's VC
        vc_proof = json.dumps(vc_data.get("proof", {}))

        # Fill out the DID login form
        page.fill("input[name='did']", did)
        page.fill("textarea[name='vc']", vc)
        page.fill("textarea[name='vc_proof']", vc_proof)

        # Submit the form
        page.click("button[type='submit']")

        # Verify that the user is redirected to the poll list
        expect(page).to_have_url(re.compile(r"http://localhost:8000/$"))

        # Navigate to the poll detail page
        page.click(f"text={poll.question}")
        expect(page).to_have_url(
            re.compile(rf"http://localhost:8000/polls/{poll.id}/$")
        )

        # Vote on the poll
        page.click("text=Option 1")
        expect(page.locator("text=Your vote has been recorded.")).to_be_visible()

        # Verify that the vote is attributed to the selected option
        expect(page.locator(f"text=Option 1: 1 vote")).to_be_visible()

        # Close the browser
        browser.close()
