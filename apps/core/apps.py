"""
App configuration for the `core` app.
"""

from django.apps import AppConfig


class CoreConfig(AppConfig):
    """
    AppConfig for the `core` app.

    This app provides the foundational models and logic for decentralized identity
    and federated data synchronization in the Polly project.
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
