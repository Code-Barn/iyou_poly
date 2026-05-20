# Copyright (C) 2026 David Byers dba Byers Brands
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
App configuration for the `core` app.
"""

from django.apps import AppConfig


class CoreConfig(AppConfig):
    """
    AppConfig for the `core` app.

    This app provides the foundational models and logic for decentralized identity
    and federated data synchronization in the Poly project.
    """

    name = "apps.core"
    verbose_name = "Core"
    default_auto_field = "django.db.models.BigAutoField"

    def ready(self):
        """
        Perform initialization tasks when the app is ready.
        """
        # Import and register signals
        import apps.core.signals  # noqa: F401
