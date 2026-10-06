"""Add ConferenceInfo.venue_photo (optional photo on the Venue page)."""

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0021_rename_conferenceinfo_photo_card_photo_add_hero_photo"),
    ]

    operations = [
        migrations.AddField(
            model_name="conferenceinfo",
            name="venue_photo",
            field=models.ImageField(blank=True, null=True, upload_to="conferences/"),
        ),
    ]
