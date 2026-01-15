"""
Forms for the `accounts` app.

This module defines forms for user registration, authentication, and profile management
in the Polly project. It includes forms for DID-based and federated authentication.
"""

from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm as BaseUserCreationForm

User = get_user_model()


class UserCreationForm(BaseUserCreationForm):
    """
    Custom user creation form for the Polly project.

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
