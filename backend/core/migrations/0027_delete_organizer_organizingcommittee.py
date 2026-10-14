from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0026_people_merge_roles"),
    ]

    operations = [
        migrations.DeleteModel(
            name="Organizer",
        ),
        migrations.DeleteModel(
            name="OrganizingCommittee",
        ),
    ]
