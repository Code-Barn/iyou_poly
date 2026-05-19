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
Forms for the `accounts` app.

This module defines forms for user registration, authentication, and profile management
in the Poly project. It includes forms for DID-based and federated authentication.
"""

from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm as BaseUserCreationForm

User = get_user_model()


class UserCreationForm(BaseUserCreationForm):
    """
    Custom user creation form for the Poly project.

    This form extends Django's built-in `UserCreationForm` to support the custom `User` model.
    """

    class Meta:
        model = User
        fields = ("username", "email")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Remove help texts and error messages for cleaner UI
        self.fields["username"].help_text = None
        self.fields["password1"].help_text = None
        self.fields["password2"].help_text = None
        self.fields["username"].error_messages = {
            "unique": "This username is already taken.",
        }
        self.fields["password2"].error_messages = {
            "password_mismatch": "The two password fields didn’t match.",
        }
