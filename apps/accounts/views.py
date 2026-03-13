"""
Views for the `accounts` app.

This module defines views for user authentication, registration, and profile management
in the Polly project. It includes views for DID-based, OIDC, and federated authentication.
"""

import datetime
import json
import logging

import didkit
from django.contrib import messages
from django.contrib.auth import authenticate, get_user_model, login
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views import View

from apps.accounts.forms import UserCreationForm
from apps.accounts.utils.did_utils import generate_did, issue_vc

User = get_user_model()

# Create logger instance
logger = logging.getLogger(__name__)


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

            # Fetch the user's did_key for verification
            did_key = None
            try:
                user = User.objects.get(did=user_did)
                if user.did_key:
                    did_key = json.loads(user.did_key)
            except User.DoesNotExist:
                pass

            user = authenticate(
                request,
                did=user_did,
                vc=vc_json,
                vc_proof=json.dumps(vc_proof),
                did_key=did_key,
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
            # Generate a key pair for the user (in JWK format)
            key = json.loads(didkit.generateEd25519Key())
            user.did_key = json.dumps(key)

            # Construct the DID using didkit.keyToDID
            user.did = didkit.keyToDID("key", json.dumps(key))
            user.did_method = "key"
            user.save()  # Save the user before issuing the VC

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
            vc = issue_vc(credential, user.did, key)  # Use the key dict directly
            if vc:
                user.add_vc(json.loads(vc))
                user.save()  # Save the user after adding the VC
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
            return redirect(f"{reverse('login')}?next={request.path}")

        # Get the user's authentication VC
        auth_vc = request.user.get_authentication_vc()

        # Get other credentials (exclude authentication credential)
        other_vcs = request.user.get_other_vcs()

        return render(
            request,
            "accounts/vc_management.html",
            {
                "auth_vc": auth_vc,
                "vcs": other_vcs,
            },
        )


class GenerateDIDAndVCView(View):
    """
    View to generate a DID and VC for the current user.
    """

    def get(self, request):
        """Generate a DID and VC for the current user."""

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
        if user.did and user.did_key:
            logger.debug(f"User {user.username} already has a DID: {user.did}")
            logger.debug("Using existing did_key for VC generation")

        # Generate a DID for the user if they don't have one
        if not user.did:
            user.did = generate_did(method="key")
            user.did_method = "key"
            logger.debug(f"Generated DID for user {user.username}: {user.did}")

        # Use existing did_key if available, otherwise generate a new one
        if not user.did_key:
            key = json.loads(didkit.generateEd25519Key())
            user.did_key = json.dumps(key)
            user.save()
            logger.debug(f"Generated new did_key for user {user.username}")
        else:
            key = json.loads(user.did_key)
            logger.debug(f"Using existing did_key for user {user.username}")

        # Issue an authentication VC for the user
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
        vc = issue_vc(credential, user.did, key)
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


class GenerateCredentialView(View):
    """
    View to generate a new verifiable credential for the current user.
    """

    def get(self, request):
        """Show the generate credential form."""
        if not request.user.is_authenticated:
            return redirect("login")

        # Check if this is an HTMX request
        if request.headers.get("HX-Request"):
            return render(request, "accounts/partials/generate_credential_form.html")
        else:
            return redirect("vc_management")

    def post(self, request):
        """Generate a new verifiable credential for the current user with custom name and type."""
        logger = logging.getLogger(__name__)

        if not request.user.is_authenticated:
            logger.debug("User not authenticated, redirecting to login")
            return redirect("login")

        user = request.user
        credential_name = request.POST.get("credential_name", "").strip()
        credential_type = request.POST.get(
            "credential_type", "MembershipCredential"
        ).strip()

        # Ensure user has a DID
        if not user.did:
            logger.debug(f"User {user.username} doesn't have a DID, generating one")
            user.did = generate_did(method="key")
            user.did_method = "key"

        # Ensure user has a did_key
        if not user.did_key:
            logger.debug(f"User {user.username} doesn't have a did_key, generating one")
            key = json.loads(didkit.generateEd25519Key())
            user.did_key = json.dumps(key)
            user.save()
        else:
            key = json.loads(user.did_key)

        # Generate a credential with custom type
        credential = {
            "@context": "https://www.w3.org/2018/credentials/v1",
            "type": ["VerifiableCredential", credential_type],
            "issuer": user.did,
            "issuanceDate": datetime.datetime.now(datetime.timezone.utc).strftime(
                "%Y-%m-%dT%H:%M:%SZ"
            ),
            "credentialSubject": {
                "id": user.did,
                "name": user.username,
                "description": credential_name
                or f"{credential_type} for {user.username}",
            },
        }

        # Issue the VC using the user's key
        vc = issue_vc(credential, user.did, key)
        if vc:
            logger.debug(f"VC issued successfully: {vc}")
            vc_data = json.loads(vc)
            user.add_vc(vc_data, credential_name or credential_type)

            # Also create a CredentialIssuance record for scope tracking
            from apps.core.models import ScopeType, Scope, CredentialType

            scope_value = request.POST.get("scope_value", "").strip()

            if scope_value:
                # Get or create the scope
                try:
                    # Find matching credential type to get scope type
                    cred_type = CredentialType.objects.filter(
                        name=credential_type
                    ).first()
                    if cred_type:
                        scope_type = cred_type.scope_type
                        scope, _ = Scope.objects.get_or_create(
                            scope_type=scope_type,
                            value=scope_value,
                            defaults={"is_active": True},
                        )

                        # Create credential issuance record
                        CredentialIssuance.objects.create(
                            credential=vc_data,
                            holder_did=user.did,
                            issuer_did=user.did,
                            credential_type=cred_type,
                            scope=scope,
                            status="active",
                        )
                except Exception as e:
                    logger.warning(f"Could not create CredentialIssuance: {e}")

            messages.success(request, "Credential generated successfully!")
        else:
            logger.error("VC issuance failed")
            messages.error(request, "Failed to generate credential.")

        # Check if this is an HTMX request
        if request.headers.get("HX-Request"):
            return render(
                request,
                "accounts/partials/vc_container.html",
                {
                    "auth_vc": request.user.get_authentication_vc(),
                    "vcs": request.user.get_other_vcs(),
                },
            )
        else:
            return redirect("vc_management")


class ImportCredentialView(View):
    """
    View to import a verifiable credential for the current user.
    """

    def get(self, request):
        """Show the import credential form."""
        if not request.user.is_authenticated:
            return redirect("login")

        return render(request, "accounts/import_credential.html", {})

    def post(self, request):
        """Process the imported credential."""
        logger = logging.getLogger(__name__)

        if not request.user.is_authenticated:
            logger.debug("User not authenticated, redirecting to login")
            return redirect("login")

        vc_json = request.POST.get("vc_json", "").strip()
        vc_name = request.POST.get("vc_name", "").strip()

        if not vc_json:
            messages.error(request, "No credential data provided.")
            return redirect("import_credential")

        try:
            # Parse the VC JSON
            vc = json.loads(vc_json)

            # Validate basic VC structure
            if not isinstance(vc, dict):
                raise ValueError("Credential must be a JSON object")

            if "@context" not in vc:
                raise ValueError("Credential must have an @context field")

            if "type" not in vc or "VerifiableCredential" not in vc["type"]:
                raise ValueError(
                    "Credential must have a type field containing 'VerifiableCredential'"
                )

            if "credentialSubject" not in vc:
                raise ValueError("Credential must have a credentialSubject field")

            # Add the VC to the user's collection
            user = request.user
            # For imported credentials, use the provided name or generate a default
            vc_types = vc.get("type", [])
            name = vc_name if vc_name else "Imported Credential"
            if not vc_name and len(vc_types) > 1:
                name = vc_types[1]  # Use the second type as the name if available

            user.add_vc(vc, name)

            messages.success(request, "Credential imported successfully!")
            return redirect("vc_management")

        except json.JSONDecodeError:
            messages.error(request, "Invalid JSON format.")
        except ValueError as e:
            messages.error(request, f"Invalid credential: {str(e)}")
        except Exception as e:
            logger.error(f"Error importing credential: {str(e)}")
            messages.error(request, "An error occurred while importing the credential.")

        return redirect("import_credential")

        # The actual OIDC authentication is handled by social-auth-app-django
        # This view is for any additional processing needed after OIDC login

        # Check if user is already authenticated (OIDC flow completed)
        if request.user.is_authenticated:
            return redirect("poll_list")

        # If not authenticated, redirect to login page
        return redirect("login")


class DeleteCredentialView(View):
    """
    View to delete a verifiable credential.
    """

    def post(self, request):
        """Delete a verifiable credential."""
        if not request.user.is_authenticated:
            return JsonResponse(
                {"success": False, "error": "Authentication required"},
                status=403,
            )

        try:
            data = json.loads(request.body)
            vc_id = data.get("vc_id")

            if not vc_id:
                return JsonResponse(
                    {"success": False, "error": "VC ID is required"},
                    status=400,
                )

            # Find and delete the VC
            user = request.user
            vcs = user.vcs.copy()
            updated = False

            for i, vc_data in enumerate(vcs):
                vc = vc_data.get("credential", {})
                if vc.get("credentialSubject", {}).get("id") == vc_id:
                    # Remove the VC
                    vcs.pop(i)
                    updated = True
                    break

            if updated:
                user.vcs = vcs
                user.save()
                return JsonResponse({"success": True})
            else:
                return JsonResponse(
                    {"success": False, "error": "VC not found"},
                    status=404,
                )

        except json.JSONDecodeError:
            return JsonResponse(
                {"success": False, "error": "Invalid JSON data"},
                status=400,
            )
        except Exception as e:
            logger.error(f"Error deleting credential: {str(e)}")
            return JsonResponse(
                {
                    "success": False,
                    "error": "An error occurred while deleting the credential",
                },
                status=500,
            )


class UpdateVCNameView(View):
    """
    View to update the custom name of a verifiable credential.
    """

    def post(self, request):
        """Update the name of a verifiable credential."""
        logger = logging.getLogger(__name__)

        if not request.user.is_authenticated:
            return JsonResponse(
                {"success": False, "error": "Authentication required"},
                status=403,
            )

        try:
            data = json.loads(request.body)
            vc_id = data.get("vc_id")
            new_name = data.get("name", "").strip()

            if not vc_id:
                return JsonResponse(
                    {"success": False, "error": "VC ID is required"},
                    status=400,
                )

            if not new_name:
                return JsonResponse(
                    {"success": False, "error": "Name cannot be empty"},
                    status=400,
                )

            if len(new_name) > 100:
                return JsonResponse(
                    {
                        "success": False,
                        "error": "Name is too long (max 100 characters)",
                    },
                    status=400,
                )

            # Find and update the VC
            user = request.user
            vcs = user.vcs.copy()
            updated = False

            for i, vc_data in enumerate(vcs):
                vc = vc_data.get("credential", {})
                if vc.get("credentialSubject", {}).get("id") == vc_id:
                    vcs[i]["name"] = new_name
                    updated = True
                    break

            if updated:
                user.vcs = vcs
                user.save()
                return JsonResponse({"success": True})
            else:
                return JsonResponse(
                    {"success": False, "error": "VC not found"},
                    status=404,
                )

        except json.JSONDecodeError:
            return JsonResponse(
                {"success": False, "error": "Invalid JSON data"},
                status=400,
            )
        except Exception as e:
            logger.error(f"Error updating VC name: {str(e)}")
            return JsonResponse(
                {"success": False, "error": "An error occurred"},
                status=500,
            )
