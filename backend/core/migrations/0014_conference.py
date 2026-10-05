"""Add the Conference model and per-conference scoping (squashed).

Hand-written (not makemigrations): the data seed must run after the
Conference table exists but before the conference FKs backfill existing
rows, and the fallback ConferenceInfo row must be created only after its
conference FK exists.

This squashes the three uncommitted multi-conference migrations
(0014 conference + logistics split, 0015 conference FKs, 0016 logistics
re-unification) into their net effect on the schema:

- Conference is slug-only; logistics stay on ConferenceInfo
- every model gets a required conference FK backfilled to wsc2026 (pk 1)
- ConferenceInfo drops `year` (now derived from date_start) and gains
  photo/short_description/badge_title; title/location lose their
  single-conference defaults

No deployed database ever applied the original three files, so no
`replaces` marker is needed.
"""

import django.db.models.deletion
from django.db import migrations, models


def seed_conference(apps, schema_editor):
    """Create the wsc2026 Conference before the FK backfills reference it."""
    Conference = apps.get_model("core", "Conference")
    Conference.objects.get_or_create(slug="wsc2026")


def seed_conference_info(apps, schema_editor):
    """Give the wsc2026 Conference a fallback ConferenceInfo row.

    On databases upgraded from the single-conference schema the existing
    ConferenceInfo row already points at wsc2026 (FK backfill), so the
    get_or_create finds it and the defaults never apply — existing data
    is preserved untouched.
    """
    Conference = apps.get_model("core", "Conference")
    ConferenceInfo = apps.get_model("core", "ConferenceInfo")
    conference = Conference.objects.filter(slug="wsc2026").first()
    if conference is None:
        return
    ConferenceInfo.objects.get_or_create(
        conference=conference,
        defaults={
            "title": "Workshop on Scientific Computing",
            "location": "Děčín",
            "badge_title": "WSC 2026",
        },
    )


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0013_delete_react"),
    ]

    operations = [
        migrations.CreateModel(
            name="Conference",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("slug", models.SlugField(max_length=64, unique=True)),
            ],
        ),
        migrations.RunPython(seed_conference, migrations.RunPython.noop),
        migrations.AddField(
            model_name="conferenceinfo",
            name="conference",
            field=models.ForeignKey(
                default=1,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="conference_infos",
                to="core.conference",
            ),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="conferenceday",
            name="conference",
            field=models.ForeignKey(
                default=1,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="days",
                to="core.conference",
            ),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="session",
            name="conference",
            field=models.ForeignKey(
                default=1,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="sessions",
                to="core.conference",
            ),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="participant",
            name="conference",
            field=models.ForeignKey(
                default=1,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="participants",
                to="core.conference",
            ),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="abstract",
            name="conference",
            field=models.ForeignKey(
                default=1,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="abstracts",
                to="core.conference",
            ),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="talk",
            name="conference",
            field=models.ForeignKey(
                default=1,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="talks",
                to="core.conference",
            ),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="organizer",
            name="conference",
            field=models.ForeignKey(
                default=1,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="organizers",
                to="core.conference",
            ),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="organizingcommittee",
            name="conference",
            field=models.ForeignKey(
                default=1,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="committee_members",
                to="core.conference",
            ),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="accommodationinfo",
            name="conference",
            field=models.ForeignKey(
                default=1,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="accommodation_infos",
                to="core.conference",
            ),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="accommodationoption",
            name="conference",
            field=models.ForeignKey(
                default=1,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="accommodation_options",
                to="core.conference",
            ),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="participantsubmission",
            name="conference",
            field=models.ForeignKey(
                default=1,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="submissions",
                to="core.conference",
            ),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="hikingroute",
            name="conference",
            field=models.ForeignKey(
                default=1,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="hiking_routes",
                to="core.conference",
            ),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="hikingstop",
            name="conference",
            field=models.ForeignKey(
                default=1,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="hiking_stops",
                to="core.conference",
            ),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name="conferenceinfo",
            name="title",
            field=models.CharField(blank=True, default="", max_length=200),
        ),
        migrations.AlterField(
            model_name="conferenceinfo",
            name="location",
            field=models.CharField(blank=True, default="", max_length=200),
        ),
        migrations.AddField(
            model_name="conferenceinfo",
            name="photo",
            field=models.ImageField(blank=True, null=True, upload_to="conferences/"),
        ),
        migrations.AddField(
            model_name="conferenceinfo",
            name="short_description",
            field=models.CharField(blank=True, default="", max_length=300),
        ),
        migrations.AddField(
            model_name="conferenceinfo",
            name="badge_title",
            field=models.CharField(blank=True, default="", max_length=100),
        ),
        migrations.RemoveField(
            model_name="conferenceinfo",
            name="year",
        ),
        migrations.RunPython(seed_conference_info, migrations.RunPython.noop),
    ]
