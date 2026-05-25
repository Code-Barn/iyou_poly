import asyncio
import json
import logging

from django.conf import settings
from django.core.management.base import BaseCommand

from apps.poller import nostr

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Nostr subscription worker — listens for inbound poll/vote events from relays"

    def handle(self, *args, **options):
        if not settings.NOSTR_ENABLED:
            self.stdout.write(self.style.WARNING(
                "Nostr is disabled (NOSTR_PRIVATE_KEY not set). "
                "Set NOSTR_PRIVATE_KEY in your environment to enable mesh participation."
            ))
            return

        relays = settings.NOSTR_RELAYS
        self.stdout.write(f"[gossip_worker] subscribing to {len(relays)} relay(s): {relays}")
        self.stdout.write("[gossip_worker] listening for kind:30023 (poll) and kind:1111 (vote) events")

        async def _run():
            tasks = [
                nostr.subscribe_loop(
                    relay,
                    kinds=[30023, 1111],
                    on_event=self._handle_event,
                    sub_id=f"iyou_poly_{relay.replace('://', '_').replace('/', '_')}",
                )
                for relay in relays
            ]
            await asyncio.gather(*tasks)

        asyncio.run(_run())

    def _handle_event(self, event: dict):
        kind = event.get("kind")
        content = event.get("content", "")
        tags = event.get("tags", [])

        if kind == 30023:
            self.stdout.write(f"[gossip_worker] received poll event: {event.get('id', '')[:16]}...")
            # Future: upsert poll from event data
            try:
                data = json.loads(content)
                self.stdout.write(f"  poll: {data.get('title', 'untitled')}")
            except json.JSONDecodeError:
                pass

        elif kind == 1111:
            self.stdout.write(f"[gossip_worker] received vote event: {event.get('id', '')[:16]}...")
            # Future: idempotent vote ingestion from event data
            try:
                data = json.loads(content)
                self.stdout.write(f"  vote: poll={data.get('poll_id')}, voter={data.get('voter_did', '')[:16]}...")
            except json.JSONDecodeError:
                pass
