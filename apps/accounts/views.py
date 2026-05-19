# Copyright (C) 2026 Byers Brands, LLC
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <https://www.gnu.org/licenses/>.

"""
Views for the `accounts` app.

Manages Verifiable Credentials (VCs) for the polling app.
Authentication is handled exclusively via OIDC (see MyOIDCAuthenticationBackend).
"""

import datetime
import json
import logging

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views import View

User = get_user_model()

logger = logging.getLogger(__name__)


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
    Legacy view — auth VCs are now issued by the OIDC IdP.
    Redirects to the IdP login flow.
    """

    def get(self, request):
        return redirect("oidc_authentication_init")


class GenerateCredentialView(View):
    """
    Generates an unsigned credential JSON for bridge signing.
    POST returns the unsigned credential; frontend sends it to
    the Tauri bridge at :9001 via signCredentialViaBridge(), then
    POSTs the signed result to StoreSignedCredentialView.
    """

    def get(self, request):
        if not request.user.is_authenticated:
            return redirect("login")
        if request.headers.get("HX-Request"):
            return render(request, "accounts/partials/generate_credential_form.html")
        return redirect("vc_management")

    def post(self, request):
        if not request.user.is_authenticated:
            return redirect("login")

        user = request.user
        credential_name = request.POST.get("credential_name", "").strip()
        credential_type = request.POST.get("credential_type", "MembershipCredential").strip()
        scope_value = request.POST.get("scope_value", "").strip()
        subject_did = request.POST.get("subject_did", "").strip() or user.username

        issuer_did = user.username  # username IS the DID from OIDC

        unsigned_credential = {
            "@context": ["https://www.w3.org/2018/credentials/v1"],
            "type": ["VerifiableCredential", credential_type],
            "issuer": issuer_did,
            "issuanceDate": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "credentialSubject": {
                "id": subject_did,
                "name": subject_did if subject_did != issuer_did else user.username,
                "description": credential_name or f"{credential_type} for {user.username}",
            },
        }

        return JsonResponse({
            "unsigned_credential": unsigned_credential,
            "credential_name": credential_name or credential_type,
            "credential_type": credential_type,
            "scope_value": scope_value,
            "subject_did": subject_did,
        })


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


class StoreSignedCredentialView(View):
    """
    Receives a credential signed by the Tauri bridge and stores it in user.vcs.
    """

    def post(self, request):
        if not request.user.is_authenticated:
            return JsonResponse({"success": False, "error": "Authentication required"}, status=403)

        try:
            data = json.loads(request.body)
            signed_vc = data.get("signed_credential")
            credential_name = data.get("credential_name", "Signed Credential")
            credential_type = data.get("credential_type", "")
            scope_value = data.get("scope_value", "")

            if not signed_vc:
                return JsonResponse({"success": False, "error": "No signed credential provided"}, status=400)

            user = request.user
            user.add_vc(signed_vc, credential_name)

            if scope_value:
                from apps.core.models import CredentialType, Scope, ScopeType, CredentialIssuance
                cred_type = CredentialType.objects.filter(name=credential_type).first()
                if cred_type:
                    scope_type = cred_type.scope_type
                    scope, _ = Scope.objects.get_or_create(
                        scope_type=scope_type,
                        value=scope_value,
                        defaults={"is_active": True},
                    )
                    CredentialIssuance.objects.create(
                        credential=signed_vc,
                        holder_did=user.username,
                        issuer_did=user.username,
                        credential_type=cred_type,
                        scope=scope,
                        status="active",
                    )

            return JsonResponse({"success": True})
        except Exception as e:
            logger.error(f"Error storing signed credential: {e}")
            return JsonResponse({"success": False, "error": str(e)}, status=500)


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
