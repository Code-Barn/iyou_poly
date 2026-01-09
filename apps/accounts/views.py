"""
Views for the `accounts` app.

This module defines views for user authentication, registration, and profile management
in the Polly project. It includes views for DID-based and federated authentication.
"""

import json
import logging

import didkit
from django.conf import settings
from django.contrib.auth import authenticate, get_user_model, login
from django.shortcuts import redirect, render
from django.views import View

from apps.accounts.forms import UserCreationForm
from apps.accounts.utils.did_utils import generate_did, issue_vc, verify_vc

User = get_user_model()


class DIDLoginView(View):
    """
    View for DID-based login.

    This view handles the login of users using their DID and Verifiable Credential (VC).
    """

    def get(self, request):
        """Render the DID login form."""
        return render(request, "registration/did_login.html")

    def post(self, request):
        """Process the DID login form submission."""
        vc_json = request.POST.get("vc")

        try:
            vc_data = json.loads(vc_json)
            user_did = vc_data["credentialSubject"]["id"]
            vc_proof = vc_data.get("proof", {})

            user = authenticate(
                request, did=user_did, vc=vc_json, vc_proof=json.dumps(vc_proof)
            )
            if user is not None:
                login(request, user)
                return redirect("poll_list")
            else:
                return render(
                    request,
                    "registration/did_login.html",
                    {"error": "Invalid DID or Verifiable Credential."},
                )
        except json.JSONDecodeError:
            return render(
                request,
                "registration/did_login.html",
                {"error": "Invalid JSON format for Verifiable Credential."},
            )
        except KeyError:
            return render(
                request,
                "registration/did_login.html",
                {"error": "Missing required fields in Verifiable Credential."},
            )


class RegisterView(View):
    """
    View for user registration.

    This view handles the registration of new users by rendering a registration form
    and processing the form submission.
    """

    def get(self, request):
        """Render the registration form."""
        form = UserCreationForm()
        return render(request, "registration/register.html", {"form": form})

    def post(self, request):
        """Process the registration form submission."""
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            # Generate a DID for the new user
            user.did = generate_did(method="key")
            user.did_method = "key"
            # Generate a key pair for the user (in JWK format)
            key = json.loads(didkit.generateEd25519Key())
            user.did_key = json.dumps(key)
            user.save()

            # Issue an authentication VC for the user
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
            # Issue the VC using the user's key
            vc = issue_vc(credential, user.did, user.did_key)
            if vc:
                user.add_vc(json.loads(vc))
            else:
                import logging

                logger = logging.getLogger(__name__)
                logger.error("VC issuance failed")

            # Set the backend for the user to avoid multiple backend errors
            user.backend = "django.contrib.auth.backends.ModelBackend"
            login(request, user)
            return redirect("poll_list")
        return render(request, "registration/register.html", {"form": form})


class VCManagementView(View):
    """
    View for managing Verifiable Credentials (VCs).

    This view allows users to view and manage their VCs.
    """

    def get(self, request):
        """Render the VC management page."""
        if not request.user.is_authenticated:
            return redirect("login")

        # Get the user's authentication VC
        auth_vc = request.user.get_authentication_vc()
        return render(
            request,
            "accounts/vc_management.html",
            {
                "auth_vc": auth_vc,
                "vcs": request.user.vcs,
            },
        )


class GenerateDIDAndVCView(View):
    """
    View to generate a DID and VC for the current user.
    """

    def get(self, request):
        """Generate a DID and VC for the current user."""
        import logging

        logger = logging.getLogger(__name__)
        logger.debug("GenerateDIDAndVCView called")
        logger.debug(f"User authenticated: {request.user.is_authenticated}")
        logger.debug(f"User: {request.user}")
        logger.debug(f"Request headers: {request.headers}")
        logger.debug(f"Request method: {request.method}")
        if not request.user.is_authenticated:
            logger.debug("User not authenticated, redirecting to login")
            return redirect("login")

        user = request.user

        # Skip if the user already has a DID
        if user.did:
            logger.debug(f"User {user.username} already has a DID: {user.did}")
            # Force VC generation for debugging
            logger.debug("Forcing VC generation for debugging")

        # Generate a DID for the user
        user.did = generate_did(method="key")
        user.did_method = "key"
        logger.debug(f"Generated DID for user {user.username}: {user.did}")

        # Generate a key pair for the user (in JWK format)
        key = json.loads(didkit.generateEd25519Key())
        user.did_key = json.dumps(key)
        user.save()

        # Issue an authentication VC for the user
        import logging

        logger = logging.getLogger(__name__)
        credential = {
            "@context": "https://www.w3.org/2018/credentials/v1",
            "type": ["VerifiableCredential", "AuthenticationCredential"],
            "issuer": user.did,
            "issuanceDate": "2023-01-01T00:00:00Z",
            "credentialSubject": {
                "id": user.did,
                "name": user.username,
            },
        }
        # Issue the VC using the user's key
        vc = issue_vc(credential, user.did, user.did_key)
        if vc:
            logger.debug(f"VC issued successfully: {vc}")
            user.add_vc(json.loads(vc))
        else:
            logger.error("VC issuance failed")

        logger.debug("Rendering vc_container.html")
        return render(
            request,
            "accounts/partials/vc_container.html",
            {
                "auth_vc": user.get_authentication_vc(),
                "vcs": user.vcs,
            },
        )
