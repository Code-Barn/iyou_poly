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
App configuration for the `poller` app.
"""

from django.apps import AppConfig


class PollerConfig(AppConfig):
    """
    AppConfig for the `poller` app.

    This app provides decentralized polling functionality for the Poly project.
    """

    name = "apps.poller"
    verbose_name = "iyou_poly Poller"
    default_auto_field = "django.db.models.BigAutoField"

    def ready(self):
        """
        Perform initialization tasks when the app is ready.
        """
        # Import and register signals
        import apps.poller.signals  # noqa: F401
