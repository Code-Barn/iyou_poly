from django.core.management.base import BaseCommand
from apps.poller.models import Vote
from apps.poller.utils.merkle import calculate_merkle_root

class Command(BaseCommand):
    help = 'Aggregates the last 100 votes and calculates a Merkle Root to anchor the ledger.'

    def handle(self, *args, **options):
        # Get last 100 votes
        votes = Vote.objects.all().order_by('-created_at')[:100]

        if not votes:
            self.stdout.write(self.style.WARNING('No votes found to anchor.'))
            return

        # Extract signatures
        signatures = [vote.signature for vote in votes if vote.signature]

        if not signatures:
            self.stdout.write(self.style.WARNING('No signed votes found to anchor.'))
            return

        # Calculate Merkle Root
        merkle_root = calculate_merkle_root(signatures)

        self.stdout.write(self.style.SUCCESS(f'--- Ledger Anchor Point ---'))
        self.stdout.write(self.style.SUCCESS(f'Votes aggregated: {len(signatures)}'))
        self.stdout.write(self.style.SUCCESS(f'Merkle Root: {merkle_root}'))
        self.stdout.write(self.style.SUCCESS(f'----------------------------'))
