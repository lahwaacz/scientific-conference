"""Fold Organizer/OrganizingCommittee rows into Person rows with roles.

Runs after Role/Person exist (0025) and before the old models are
dropped (0027). A person present in both old tables ends up as ONE
Person holding both roles; matching is case-insensitive on email when
the email is non-empty, else exact name. Photo paths are copied
verbatim (stored string only, files are not moved).
"""

from django.db import migrations


def find_person(Person, conference, name, email):
    if email:
        return Person.objects.filter(conference=conference, email__iexact=email).first()
    return Person.objects.filter(conference=conference, name=name).first()


def fill_empty_fields(person, source):
    # Merge duplicates preferring non-empty values (e.g. keep a photo).
    for field in ("name", "department", "email"):
        value = getattr(source, field)
        if value and not getattr(person, field):
            setattr(person, field, value)
    if source.photo and not person.photo:
        # FieldFile assignment copies the stored path string only.
        person.photo = source.photo
    person.save()


def migrate_people_forward(apps, schema_editor):
    Role = apps.get_model("core", "Role")
    Person = apps.get_model("core", "Person")
    Organizer = apps.get_model("core", "Organizer")
    OrganizingCommittee = apps.get_model("core", "OrganizingCommittee")

    # Fixed creation order keeps the pks stable for fixture references.
    organizer_role, _ = Role.objects.get_or_create(
        name="organizer", defaults={"label": "Organiser"}
    )
    committee_role, _ = Role.objects.get_or_create(
        name="committee", defaults={"label": "Organising Committee"}
    )

    def copy_row(source, role):
        person = find_person(Person, source.conference, source.name, source.email)
        if person is None:
            person = Person.objects.create(
                conference=source.conference,
                name=source.name,
                department=source.department,
                email=source.email,
                photo=source.photo,
            )
        else:
            fill_empty_fields(person, source)
        person.roles.add(role)

    for organizer in Organizer.objects.all():
        copy_row(organizer, organizer_role)
    for member in OrganizingCommittee.objects.all():
        copy_row(member, committee_role)


def migrate_people_backward(apps, schema_editor):
    # Best-effort reverse: recreate one old-table row per role a Person
    # holds, then drop the migrated Persons (0027's reverse has already
    # recreated the old tables by the time this runs).
    Role = apps.get_model("core", "Role")
    Person = apps.get_model("core", "Person")
    Organizer = apps.get_model("core", "Organizer")
    OrganizingCommittee = apps.get_model("core", "OrganizingCommittee")

    organizer_role = Role.objects.filter(name="organizer").first()
    committee_role = Role.objects.filter(name="committee").first()

    migrated = []
    for person in Person.objects.all():
        role_names = set(person.roles.values_list("name", flat=True))
        if organizer_role is not None and "organizer" in role_names:
            Organizer.objects.create(
                conference=person.conference,
                name=person.name,
                department=person.department,
                email=person.email,
                photo=person.photo,
            )
        if committee_role is not None and "committee" in role_names:
            OrganizingCommittee.objects.create(
                conference=person.conference,
                name=person.name,
                department=person.department,
                email=person.email,
                photo=person.photo,
            )
        if role_names & {"organizer", "committee"}:
            migrated.append(person.pk)
    Person.objects.filter(pk__in=migrated).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0025_role_person"),
    ]

    operations = [
        migrations.RunPython(migrate_people_forward, migrate_people_backward),
    ]
