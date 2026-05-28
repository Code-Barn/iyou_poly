import asyncio
import logging

from django.conf import settings
from django.core.management.base import BaseCommand

from apps.poller import nostr
from apps.poller.nostr_ingest import ingest_poll_event, ingest_vote_event

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
        self.stdout.write("[gossip_worker] listening for kind:30023 (poll) and kind:1111/1112 (vote) events")

        async def _run():
            tasks = [
                nostr.subscribe_loop(
                    relay,
                    kinds=[30023, 1111, 1112],
                    on_event=self._handle_event,
                    sub_id=f"iyou_poly_{relay.replace('://', '_').replace('/', '_')}",
                )
                for relay in relays
            ]
            await asyncio.gather(*tasks)

        asyncio.run(_run())

    def _handle_event(self, event: dict):
        kind = event.get("kind")
        event_id = event.get("id", "")[:16]

        if kind == 30023:
            self.stdout.write(f"[gossip_worker] received poll event: {event_id}...")
            poll = ingest_poll_event(event)
            if poll:
                self.stdout.write(f"  → poll #{poll.id}: {poll.title}")
            else:
                self.stdout.write(f"  → skipped (invalid/duplicate)")

        elif kind in (1111, 1112):
            self.stdout.write(f"[gossip_worker] received vote event: {event_id}...")
            vote = ingest_vote_event(event)
            if vote:
                self.stdout.write(f"  → vote #{vote.id} for poll #{vote.poll_id}")
            else:
                self.stdout.write(f"  → skipped (invalid/duplicate)")
