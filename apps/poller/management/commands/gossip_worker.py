import time

from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Gossip heartbeat worker for K3s sidecar"

    def handle(self, *args, **options):
        self.stdout.write("[gossip_worker] starting heartbeat loop")
        while True:
            self.stdout.write("[gossip_worker] heartbeat — mesh active")
            time.sleep(60)
