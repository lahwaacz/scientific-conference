from django.db import migrations


def backfill_poster_talks(apps, schema_editor):
    ParticipantSubmission = apps.get_model("core", "ParticipantSubmission")
    Talk = apps.get_model("core", "Talk")

    submissions = ParticipantSubmission.objects.filter(
        status="approved",
        contribution_type="poster",
        published_abstract__isnull=False,
    ).select_related("published_abstract")

    for submission in submissions:
        abstract = submission.published_abstract
        if abstract is None:
            continue
        Talk.objects.get_or_create(
            abstract_id=abstract.id,
            defaults={
                "conference_id": submission.conference_id,
                "title": abstract.title,
                "participant_id": submission.published_participant_id,
                "talk_type": "poster",
                "is_scheduled": False,
            },
        )


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0035_session_kind"),
    ]

    operations = [
        migrations.RunPython(backfill_poster_talks, migrations.RunPython.noop),
    ]
