"""Add ParticipantSubmission tracking identity (token + linked user).

Hand-written (not makemigrations): tracking_token must reach its final
unique state through a nullable intermediate with NO default. On SQLite,
an AddField with a non-None effective default triggers ``_remake_table``,
which backfills EVERY existing row with ONE shared invocation of the
callable default (``effective_default`` -> a single literal in the
table-copy SELECT). All rows would receive the same token, breaking both
the per-row backfill below and the final UNIQUE rebuild. The four-step
shape is therefore: add nullable token without a default, add the
nullable linked_user FK, backfill a distinct random token per row, then
alter the token to the model's final field definition.
"""

import secrets

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models

import core.models


def backfill_tracking_tokens(apps, schema_editor):
    """Give every existing submission a distinct non-empty token.

    Idempotent: rows that already carry a token are skipped, so a re-run
    is a no-op (and a database with no submissions is untouched).
    """
    ParticipantSubmission = apps.get_model("core", "ParticipantSubmission")
    pending = ParticipantSubmission.objects.filter(
        models.Q(tracking_token__isnull=True) | models.Q(tracking_token="")
    )
    for submission in pending:
        token = secrets.token_urlsafe(24)
        while (
            ParticipantSubmission.objects.filter(tracking_token=token)
            .exclude(pk=submission.pk)
            .exists()
        ):
            token = secrets.token_urlsafe(24)
        submission.tracking_token = token
        submission.save(update_fields=["tracking_token"])


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0022_add_conferenceinfo_venue_photo"),
    ]

    operations = [
        migrations.AddField(
            model_name="participantsubmission",
            name="tracking_token",
            field=models.CharField(blank=True, db_index=True, max_length=64, null=True),
        ),
        migrations.AddField(
            model_name="participantsubmission",
            name="linked_user",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="linked_submissions",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.RunPython(backfill_tracking_tokens, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="participantsubmission",
            name="tracking_token",
            field=models.CharField(
                db_index=True,
                default=core.models.generate_tracking_token,
                editable=False,
                max_length=64,
                unique=True,
            ),
        ),
    ]
