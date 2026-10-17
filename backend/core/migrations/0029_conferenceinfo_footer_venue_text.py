"""Add ConferenceInfo.footer_venue_text (independent, plain-text footer venue).

Backfills existing rows from venue_text so live footers keep showing what they
showed before the split; new rows get the model default.
"""

from django.db import migrations, models
from django.db.models import F


def copy_venue_text_to_footer(apps, schema_editor):
    conference_info = apps.get_model("core", "ConferenceInfo")
    conference_info.objects.update(footer_venue_text=F("venue_text"))


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0028_rename_person_department_affiliation"),
    ]

    operations = [
        migrations.AddField(
            model_name="conferenceinfo",
            name="footer_venue_text",
            field=models.TextField(
                blank=True,
                default="Faculty of Nuclear Sciences and Physical Engineering, Trojanova 13, 120 00, Prague",
            ),
        ),
        migrations.RunPython(copy_venue_text_to_footer, migrations.RunPython.noop),
    ]
