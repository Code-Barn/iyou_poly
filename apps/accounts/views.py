"""
Views for the `accounts` app.

This module defines views for user authentication, registration, and profile management
in the Polly project. It includes views for DID-based and federated authentication.
"""

import json

import didkit
from django.contrib.auth import get_user_model, login
from django.shortcuts import redirect, render
from django.views import View

from apps.accounts.forms import UserCreationForm
from apps.accounts.utils.did_utils import generate_did, issue_vc

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
        did = request.POST.get("did")
        vc = request.POST.get("vc")
        vc_proof = request.POST.get("vc_proof")

        user = authenticate(request, did=did, vc=vc, vc_proof=vc_proof)
        if user is not None:
            login(request, user)
            return redirect("poll_list")
        else:
            return render(
                request,
                "registration/did_login.html",
                {"error": "Invalid DID or Verifiable Credential."},
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

            # Issue an authentication VC for the new user
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
