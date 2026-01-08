import json

import didkit
from django.contrib.auth import get_user_model
from django.core.management import BaseCommand

from apps.accounts.utils.did_utils import generate_did, issue_vc


class Command(BaseCommand):
    help = "Backfill DIDs and VCs for existing users."

    def handle(self, *args, **options):
        User = get_user_model()
        users = User.objects.filter(did__isnull=True)

        if not users.exists():
            self.stdout.write(self.style.SUCCESS("No users without DIDs found."))
            return

        self.stdout.write(
            self.style.WARNING(
                f"Found {users.count()} users without DIDs. Generating DIDs and VCs..."
            )
        )

        for user in users:
            # Generate a DID for the user
            user.did = generate_did(method="key")
            user.did_method = "key"

            # Generate a key pair for the user (in JWK format)
            key = json.loads(didkit.generateEd25519Key())
            user.did_key = json.dumps(key)
            user.save()

            # Issue an authentication VC for the user
            credential = {
                "@context": ["https://www.w3.org/2018/credentials/v1"],
                "type": ["VerifiableCredential", "AuthenticationCredential"],
                "issuer": user.did,
                "issuanceDate": "2023-01-01T00:00:00Z",
                "credentialSubject": {
                    "id": user.did,
                    "name": user.username,
                },
            }
            vc = issue_vc(credential, user.did, user.did_key)
            if vc:
                user.add_vc(json.loads(vc))

            self.stdout.write(
                self.style.SUCCESS(f"Generated DID and VC for user: {user.username}")
            )

        self.stdout.write(self.style.SUCCESS("Successfully backfilled DIDs and VCs."))
