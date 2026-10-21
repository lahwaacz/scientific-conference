import django.db.models.deletion
from django.db import migrations, models


def delete_orphan_abstracts(apps, schema_editor):
    Abstract = apps.get_model("core", "Abstract")
    Abstract.objects.filter(participant__isnull=True).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0036_backfill_poster_talks"),
    ]

    operations = [
        migrations.RunPython(delete_orphan_abstracts, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="abstract",
            name="participant",
            field=models.OneToOneField(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="abstract",
                to="core.participant",
            ),
        ),
    ]
