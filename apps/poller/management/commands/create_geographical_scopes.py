"""
Management command to create initial geographical scopes.
"""

from django.core.management.base import BaseCommand

from apps.poller.models import GeographicalScope


class Command(BaseCommand):
    help = "Create initial geographical scopes (local, state, national, global)."

    def handle(self, *args, **options):
        scopes = [
            {"name": "local", "description": "Local scope (e.g., city, town)."},
            {"name": "state", "description": "State or regional scope."},
            {"name": "national", "description": "National scope."},
            {"name": "global", "description": "Global scope."},
        ]

        for scope in scopes:
            GeographicalScope.objects.get_or_create(
                name=scope["name"],
                defaults={"description": scope["description"]},
            )

        self.stdout.write(
            self.style.SUCCESS("Successfully created geographical scopes.")
        )
