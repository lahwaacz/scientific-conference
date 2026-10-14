from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0027_delete_organizer_organizingcommittee"),
    ]

    operations = [
        # RenameField (not Remove+Add) so existing Person rows keep their
        # value. Abstract.department is a different model and stays as-is.
        migrations.RenameField(
            model_name="person",
            old_name="department",
            new_name="affiliation",
        ),
    ]
