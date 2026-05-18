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
    verbose_name = "Poller"
    default_auto_field = "django.db.models.BigAutoField"

    def ready(self):
        """
        Perform initialization tasks when the app is ready.
        """
        # Import and register signals
        import apps.poller.signals  # noqa: F401
