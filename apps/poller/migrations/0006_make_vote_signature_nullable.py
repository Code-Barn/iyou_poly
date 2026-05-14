from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("poller", "0005_vote_merkle_root"),
    ]

    operations = [
        migrations.AlterField(
            model_name="vote",
            name="signature",
            field=models.TextField(
                blank=True,
                help_text="Cryptographic signature from voter's DID key.",
                null=True,
            ),
        ),
        migrations.RunSQL(
            sql='UPDATE poller_vote SET signature = NULL WHERE signature = \'\';',
            reverse_sql='UPDATE poller_vote SET signature = \'\' WHERE signature IS NULL;',
        ),
    ]
