"""Regression tests for the program_text field and its data migration.

The 0018 merge is exercised with fake model classes: the real
MigrationExecutor run is unreliable on pytest's in-memory shared-cache
SQLite (the executor's connection snapshot does not see rows seeded
outside its transaction), so the transformation rules are pinned at
unit level. The wiring is covered by makemigrations --check and the
deploy-time migration run.
"""

import importlib

from django.test import TestCase

from .models import Conference, ConferenceInfo

merge_program_texts = importlib.import_module(
    "core.migrations.0018_merge_program_texts"
).merge_program_texts


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
        info, _ = ConferenceInfo.objects.get_or_create(
            conference=Conference.objects.create(slug="blank-default")
        )

        self.assertEqual(info.program_text, "")
