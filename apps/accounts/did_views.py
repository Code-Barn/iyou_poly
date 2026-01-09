"""
DID-based authentication views for the accounts app.

This module implements views for DID-based login and credential management
in the federated authentication system.
"""

import json
import logging
import re

import didkit
from django.conf import settings
from django.contrib.auth import login
from django.shortcuts import redirect, render
from django.views import View

from apps.accounts.models import User
from apps.accounts.utils.did_utils import verify_federated_vc

logger = logging.getLogger(__name__)


def parse_vc_input(vc_input: str) -> dict:
    """
    Parse VC input that could be either JSON or Python dict format.

    Args:
        vc_input: The VC input string (could be JSON or Python dict format)

    Returns:
        The parsed VC as a dictionary

    Raises:
        ValueError: If the input cannot be parsed as either format
    """
    # First try to parse as JSON
    try:
        return json.loads(vc_input)
    except json.JSONDecodeError:
        pass

    # If JSON parsing fails, try to convert Python dict format to JSON format
    try:
        # Handle HTML-escaped content (from UI copy/paste)
        json_format = vc_input.replace("&#x27;", "'")
        # Convert single quotes to double quotes for JSON compatibility
        json_format = re.sub(r"'", '"', json_format)
        # Handle Python-specific syntax like True/False/None
        json_format = re.sub(r"\bTrue\b", "true", json_format)
        json_format = re.sub(r"\bFalse\b", "false", json_format)
        json_format = re.sub(r"\bNone\b", "null", json_format)
        return json.loads(json_format)
    except Exception:
        raise ValueError(
            "Invalid VC format. Please provide valid JSON or Python dict format."
        )


class DIDLoginView(View):
    """
    View for DID-based login using Verifiable Credentials.

    This view handles the login process where users authenticate by presenting
    a Verifiable Credential issued by a trusted federated server.
    """

    def get(self, request):
        """Render the DID login form."""
        return render(
            request, "accounts/did_login.html", {"next": request.GET.get("next", "/")}
        )

    def post(self, request):
        """Process DID login with Verifiable Credential."""
        vc_json = request.POST.get("vc", "").strip()
        vc_proof = request.POST.get("vc_proof", "").strip()
        next_url = request.POST.get("next", request.GET.get("next", "/"))

        logger.debug(f"DID login attempt for VC: {vc_json[:100]}...")

        # Validate input
        if not vc_json:
            return render(
                request,
                "accounts/did_login.html",
                {
                    "error": "Please provide a Verifiable Credential",
                    "vc": vc_json,
                    "next": next_url,
                },
            )

        try:
            logger.debug(f"Raw VC input (first 200 chars): {vc_json[:200]}")
            vc_data = parse_vc_input(vc_json)
            issuer_did = vc_data.get("issuer", "")
            credential_subject = vc_data.get("credentialSubject", {})
            user_did = credential_subject.get("id", "")

            logger.debug(f"VC issuer: {issuer_did}, subject DID: {user_did}")

            # Verify the VC (convert back to JSON string for verification)
            vc_json_string = json.dumps(vc_data)
            if not verify_federated_vc(vc_json_string, issuer_did):
                logger.warning(f"VC verification failed for issuer: {issuer_did}")
                return render(
                    request,
                    "accounts/did_login.html",
                    {
                        "error": "Invalid or untrusted Verifiable Credential",
                        "vc": vc_json,
                        "next": next_url,
                    },
                )

            # Find or create the user
            try:
                user = User.objects.get(did=user_did)
                logger.info(f"Found existing user with DID: {user_did}")
            except User.DoesNotExist:
                if getattr(settings, "AUTO_PROVISION_DID_USERS", True):
                    # Auto-provision new user from VC data
                    user = self._create_user_from_vc(vc_data, user_did)
                    logger.info(f"Auto-provisioned new user with DID: {user_did}")
                else:
                    logger.warning(
                        f"User auto-provisioning disabled. DID not found: {user_did}"
                    )
                    return render(
                        request,
                        "accounts/did_login.html",
                        {
                            "error": "User not found. Please register first.",
                            "vc": vc_json,
                            "next": next_url,
                        },
                    )

            # Log the user in
            login(request, user)
            logger.info(f"User {user.username} logged in successfully via DID")

            return redirect(next_url)

        except ValueError as e:
            logger.error(f"Invalid VC format: {e}")
            return render(
                request,
                "accounts/did_login.html",
                {
                    "error": str(e),
                    "vc": vc_json,
                    "next": next_url,
                },
            )
        except Exception as e:
            logger.error(f"DID login error: {e}")
            return render(
                request,
                "accounts/did_login.html",
                {
                    "error": "An error occurred. Please try again.",
                    "vc": vc_json,
                    "next": next_url,
                },
            )

    def _create_user_from_vc(self, vc_data, user_did):
        """Create a new user from VC data during auto-provisioning."""
        credential_subject = vc_data.get("credentialSubject", {})
        username = credential_subject.get("name", f"user_{User.objects.count() + 1}")
        email = credential_subject.get("email", "")

        # Ensure unique username
        original_username = username
        counter = 1
        while User.objects.filter(username=username).exists():
            username = f"{original_username}_{counter}"
            counter += 1

        user = User.objects.create_user(
            username=username,
            email=email,
            did=user_did,
            did_method="key",  # Default to key method
        )

        # Set unusable password for DID-only users
        user.set_unusable_password()
        user.save()

        # Add the VC to user's credentials
        user.add_vc(vc_data)

        logger.info(f"Created new user: {username} with DID: {user_did}")

        return user


class DIDLoginPartialView(View):
    """
    Partial view for DID login form (used with HTMX).
    """

    def get(self, request):
        """Render the partial DID login form."""
        return render(
            request,
            "accounts/partials/did_login_partial.html",
            {"next": request.GET.get("next", "/")},
        )

    def post(self, request):
        """Process DID login and return partial response."""
        # Reuse the main login logic
        response = DIDLoginView().post(request)

        if response.status_code == 302:
            # Return success partial on redirect
            return render(
                request,
                "accounts/partials/login_success.html",
                {"redirect_url": response.url},
            )
        else:
            # Return the form with errors
            return render(
                request,
                "accounts/partials/did_login_partial.html",
                {
                    "error": response.context_data.get("error", ""),
                    "vc": response.context_data.get("vc", ""),
                    "next": response.context_data.get("next", "/"),
                },
            )
