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

from apps.accounts.models import FederatedIdentity


def save_federated_identity(backend, user, response, *args, **kwargs):
    """
    Save federated identity information after successful OIDC authentication.

    This function is part of the social auth pipeline and is called after
    a user is authenticated with an OIDC provider.

    Args:
        backend: The authentication backend used
        user: The user object
        response: The response from the OIDC provider
        *args, **kwargs: Additional pipeline arguments
    """
    # Extract provider name from backend
    provider = backend.name

    # Get the unique identifier from the provider
    external_id = response.get("id") or response.get("sub") or response.get("login")

    if not external_id:
        return None

    # Create or update the federated identity
    federated_identity, created = FederatedIdentity.objects.get_or_create(
        user=user,
        provider=provider,
        defaults={"external_id": external_id, "is_active": True},
    )

    if not created:
        # Update existing federated identity
        federated_identity.external_id = external_id
        federated_identity.is_active = True
        federated_identity.save()

    return {"user": user, "federated_identity": federated_identity, "is_new": created}
