"""Regression tests for the data migrations and their model defaults.

The 0018 and 0031 merges are exercised with fake model classes: the real
MigrationExecutor run is unreliable on pytest's in-memory shared-cache
SQLite (the executor's connection snapshot does not see rows seeded
outside its transaction), so the transformation rules are pinned at
unit level. The wiring is covered by makemigrations --check and the
deploy-time migration run.
"""

import importlib
from types import SimpleNamespace

from django.test import TestCase

from .models import Conference

merge_program_texts = importlib.import_module(
    "core.migrations.0018_merge_program_texts"
).merge_program_texts

merge_conference_config = importlib.import_module(
    "core.migrations.0031_remove_accommodationoption_info_and_more"
)
copy_conference_config = merge_conference_config.copy_conference_config
CONFERENCE_FIELDS = merge_conference_config.CONFERENCE_FIELDS


class FakeInfo:
    def __init__(self, local="", regular="", poster=""):
        self.program_local_registration_text = local
        self.program_regular_talks_text = regular
        self.program_poster_talks_text = poster
        self.program_text = ""
        self.saved_fields = []

    def save(self, update_fields=None):
        self.saved_fields.append(update_fields)


class FakeApps:
    def __init__(self, rows):
        self._rows = rows

    def get_model(self, _app_label, _model_name):
        rows = self._rows

        class FakeManager:
            def all(self):
                return list(rows)

        class FakeModel:
            objects = FakeManager()

        return FakeModel


class TestMergeProgramTexts(TestCase):
    def test_merges_sections_in_document_order(self):
        row = FakeInfo(
            local="Register at the desk.",
            regular="20 minutes per talk.",
            poster="",
        )

        merge_program_texts(FakeApps([row]), None)

        self.assertEqual(
            row.program_text,
            "## Registration for local participants\n\nRegister at the desk.\n\n"
            "## Regular talks\n\n20 minutes per talk.",
        )
        self.assertEqual(row.saved_fields, [["program_text"]])

    def test_all_blank_row_is_left_untouched(self):
        row = FakeInfo()

        merge_program_texts(FakeApps([row]), None)

        self.assertEqual(row.program_text, "")
        self.assertEqual(row.saved_fields, [])


class TestProgramTextDefault(TestCase):
    def test_program_text_defaults_to_empty(self):
        conference = Conference.objects.create(slug="blank-default")

        self.assertEqual(conference.program_text, "")


class FakeQuerySet:
    def __init__(self, updates, pk):
        self._updates = updates
        self._pk = pk

    def update(self, **fields):
        self._updates[self._pk] = fields


class FakeConferenceTable:
    def __init__(self):
        self.updates = {}

    def filter(self, pk):
        return FakeQuerySet(self.updates, pk)


class FakeOrderedRows:
    def __init__(self, rows):
        self._rows = rows

    def order_by(self, field):
        return sorted(self._rows, key=lambda row: getattr(row, field))


class FakeConfigModel:
    def __init__(self, objects):
        self.objects = objects


class FakeMergeApps:
    def __init__(self, conferences, info_rows, accommodation_rows):
        self._models = {
            "Conference": FakeConfigModel(conferences),
            "ConferenceInfo": FakeConfigModel(FakeOrderedRows(info_rows)),
            "AccommodationInfo": FakeConfigModel(FakeOrderedRows(accommodation_rows)),
        }

    def get_model(self, _app_label, model_name):
        return self._models[model_name]


def fake_info(pk, conference_id, **overrides):
    fields = {name: f"{name}-{pk}" for name in CONFERENCE_FIELDS}
    fields.update(overrides)
    return SimpleNamespace(pk=pk, conference_id=conference_id, **fields)


class TestMergeConferenceConfig(TestCase):
    def test_lowest_pk_info_row_wins(self):
        conferences = FakeConferenceTable()
        rows = [
            fake_info(pk=5, conference_id=9, title="Second"),
            fake_info(pk=2, conference_id=9, title="First"),
        ]

        copy_conference_config(FakeMergeApps(conferences, rows, []), None)

        self.assertEqual(list(conferences.updates), [9])
        self.assertEqual(conferences.updates[9]["title"], "First")
        self.assertEqual(set(conferences.updates[9]), set(CONFERENCE_FIELDS))

    def test_each_conference_gets_its_own_info_row(self):
        conferences = FakeConferenceTable()
        rows = [
            fake_info(pk=1, conference_id=1, title="One"),
            fake_info(pk=2, conference_id=2, title="Two"),
        ]

        copy_conference_config(FakeMergeApps(conferences, rows, []), None)

        self.assertEqual(conferences.updates[1]["title"], "One")
        self.assertEqual(conferences.updates[2]["title"], "Two")

    def test_accommodation_description_is_copied(self):
        conferences = FakeConferenceTable()
        rows = [SimpleNamespace(pk=3, conference_id=9, description="Hotel")]

        copy_conference_config(FakeMergeApps(conferences, [], rows), None)

        self.assertEqual(conferences.updates[9], {"accommodation_description": "Hotel"})

    def test_empty_tables_are_a_noop(self):
        conferences = FakeConferenceTable()

        copy_conference_config(FakeMergeApps(conferences, [], []), None)

        self.assertEqual(conferences.updates, {})
