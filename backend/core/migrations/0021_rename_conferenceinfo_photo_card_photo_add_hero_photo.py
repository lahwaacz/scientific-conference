"""Rename ConferenceInfo.photo to card_photo and add hero_photo.

Hand-written as RenameField + AddField: a plain makemigrations run would
produce RenameField anyway (the field definition is unchanged), but pinning
the rename explicitly keeps the column and its files intact — no
RemoveField/AddField pair.
"""

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0020_alter_conferenceinfo_program_text"),
    ]

    operations = [
        migrations.RenameField(
            model_name="conferenceinfo",
            old_name="photo",
            new_name="card_photo",
        ),
        migrations.AddField(
            model_name="conferenceinfo",
            name="hero_photo",
            field=models.ImageField(blank=True, null=True, upload_to="conferences/"),
        ),
    ]
