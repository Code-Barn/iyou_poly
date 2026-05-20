# Copyright (C) 2026 David Byers dba Byers Brands
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
