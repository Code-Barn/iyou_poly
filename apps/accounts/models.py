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

import datetime

from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """
    Custom User model with support for Decentralized Identifiers (DIDs).
    """

    # Deprecated: Identity is now strictly username (the OIDC sub claim / DID).
    # These fields remain for backward compatibility with existing poll/vote data.
    did = models.CharField(
        max_length=255,
        unique=True,
        null=True,
        blank=True,
        help_text="[DEPRECATED] Identity now sourced from username (OIDC sub).",
    )
    vcs = models.JSONField(
        default=list,
        help_text="List of verifiable credentials with metadata associated with the user. Can contain both old format (direct VC) and new format (VC with metadata).",
    )

    def ensure_vcs_migrated(self):
        """
        Ensure all VCs are migrated to the new format with metadata.
        This method should be called before any VC operations.
        """
        vcs = self.vcs.copy()
        updated = False

        for i, vc_data in enumerate(vcs):
            # Check if this is old format (direct VC without metadata)
            if "credential" not in vc_data and isinstance(vc_data, dict):
                # Convert to new format
                vcs[i] = {
                    "credential": vc_data,
                    "added_date": datetime.datetime.now(
                        datetime.timezone.utc
                    ).isoformat(),
                    "name": self._generate_vc_name(vc_data),
                }
                updated = True

        if updated:
            self.vcs = vcs
            self.save()

    # Deprecated: legacy field no longer actively used.
    did_method = models.CharField(
        max_length=50,
        default="key",
        help_text="[DEPRECATED] DID method from legacy self-sovereign keygen.",
    )
    # Deprecated: signing now happens via the Tauri bridge (:9001), not server-side.
    did_key = models.TextField(
        blank=True,
        help_text="[DEPRECATED] Private key from legacy self-sovereign keygen.",
    )

    def __str__(self):
        return self.username

    def add_vc(self, vc: dict, name: str = None) -> None:
        """
        Add a verifiable credential to the user's list of VCs.

        Args:
            vc: The verifiable credential to add (as a dictionary).
            name: Optional custom name for the credential.
        """
        # Ensure VCs are migrated before adding new ones
        self.ensure_vcs_migrated()

        vcs = self.vcs.copy()
        vc_id = vc.get("credentialSubject", {}).get("id")

        # Check if this VC already exists
        existing_vc_found = False
        if vc_id:
            for existing_vc in vcs:
                # Get existing VC ID
                if "credential" in existing_vc:
                    existing_vc_id = (
                        existing_vc["credential"].get("credentialSubject", {}).get("id")
                    )
                else:
                    existing_vc_id = existing_vc.get("credentialSubject", {}).get("id")

                if existing_vc_id == vc_id:
                    existing_vc_found = True
                    # Check if this is the authentication credential - NEVER replace it
                    existing_vc_types = existing_vc.get("credential", {}).get(
                        "type", []
                    )
                    if "AuthenticationCredential" in existing_vc_types:
                        # This is the authentication credential, don't replace it
                        # Add the new VC as a separate credential
                        vcs.append(
                            {
                                "credential": vc,
                                "name": name or self._generate_vc_name(vc),
                                "added_date": datetime.datetime.now(
                                    datetime.timezone.utc
                                ).isoformat(),
                            }
                        )
                        break

                    # For non-authentication credentials, update the existing one
                    if "credential" in existing_vc:
                        existing_vc["credential"] = vc
                        existing_vc["name"] = (
                            name
                            or existing_vc.get("name")
                            or self._generate_vc_name(vc)
                        )
                    else:
                        # Convert old format to new format
                        existing_vc = {
                            "credential": vc,
                            "name": name or self._generate_vc_name(vc),
                            "added_date": existing_vc.get("added_date")
                            or datetime.datetime.now(datetime.timezone.utc).isoformat(),
                        }
                        vcs[vcs.index(existing_vc)] = existing_vc
                    break

        # If no existing VC was found, add the new one
        if not existing_vc_found:
            vcs.append(
                {
                    "credential": vc,
                    "name": name or self._generate_vc_name(vc),
                    "added_date": datetime.datetime.now(
                        datetime.timezone.utc
                    ).isoformat(),
                }
            )

        self.vcs = vcs
        self.save()

    def _generate_vc_name(self, vc: dict) -> str:
        """
        Generate a default name for a VC based on its type.

        Args:
            vc: The verifiable credential.

        Returns:
            A generated name for the VC.
        """
        vc_types = vc.get("type", [])
        if not vc_types:
            return "Verifiable Credential"

        # Filter out generic types
        specific_types = [t for t in vc_types if t not in ["VerifiableCredential"]]

        if specific_types:
            return specific_types[0]
        else:
            return vc_types[0]

    def get_vcs_by_type(self, vc_type: str) -> list:
        """
        Get all VCs of a specific type for this user.

        Args:
            vc_type: The type of VC to filter by (e.g., "VerifiableCredential").

        Returns:
            List of VCs matching the type.
        """
        # Ensure VCs are migrated before accessing them
        self.ensure_vcs_migrated()

        vcs = []
        for vc_data in self.vcs:
            # Handle both old format (direct VC) and new format (VC with metadata)
            if "credential" in vc_data:
                vc = vc_data["credential"]
            else:
                vc = vc_data

            if vc.get("type") and vc_type in vc.get("type"):
                vcs.append(vc)
        return vcs

    def get_other_vcs(self) -> list:
        """
        Get all VCs that are not authentication credentials.

        Returns:
            List of VCs with metadata that are not authentication credentials.
        """
        # Ensure VCs are migrated before accessing them
        self.ensure_vcs_migrated()

        other_vcs = []
        for vc_data in self.vcs:
            # Handle both old and new format
            if "credential" in vc_data:
                vc = vc_data["credential"]
            else:
                vc = vc_data

            vc_types = vc.get("type", [])
            if "AuthenticationCredential" not in vc_types:
                other_vcs.append(vc_data)
        return other_vcs

    def get_vc_metadata(self, vc_id: str) -> dict:
        """
        Get metadata for a specific VC.

        Args:
            vc_id: The ID of the credentialSubject.

        Returns:
            Metadata for the VC or None if not found.
        """
        # Ensure VCs are migrated before accessing them
        self.ensure_vcs_migrated()

        for vc_data in self.vcs:
            vc = vc_data["credential"]
            if vc.get("credentialSubject", {}).get("id") == vc_id:
                return vc_data
        return None

    def get_authentication_vc(self) -> dict:
        """
        Get the authentication VC for this user.

        Returns:
            The authentication VC, or None if not found.
        """
        # Ensure VCs are migrated before accessing them
        self.ensure_vcs_migrated()

        auth_vcs = self.get_vcs_by_type("AuthenticationCredential")
        return auth_vcs[0] if auth_vcs else None


class FederatedIdentity(models.Model):
    """
    Model to store federated identities linked to a user.
    """

    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="federated_identities"
    )
    provider = models.CharField(
        max_length=50,
        help_text="Name of the identity provider (e.g., 'google', 'adfs').",
    )
    external_id = models.CharField(
        max_length=255, help_text="Unique identifier from the external provider."
    )
    is_active = models.BooleanField(
        default=True, help_text="Whether this federated identity is active."
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("provider", "external_id")

    def __str__(self):
        return f"{self.provider}:{self.external_id}"
