"""Tests for the Conference/ConferenceInfo models and the 0014 seed."""

import importlib
from datetime import date
from types import SimpleNamespace
from unittest.mock import patch

from django.core.exceptions import ValidationError
from django.test import TestCase

from .models import Conference, ConferenceInfo


def make_conference(slug="wsc2026"):
    return Conference(slug=slug)


def make_info(**overrides):
    fields = {
        "title": "Workshop on Scientific Computing",
        "date_start": None,
        "date_end": None,
        "location": "Děčín",
    }
    fields.update(overrides)
    return ConferenceInfo(**fields)


class TestReservedSlugs(TestCase):
    def test_reserved_slug_auth_rejected(self):
        conference = make_conference(slug="auth")
        with self.assertRaises(ValidationError) as ctx:
            conference.full_clean()
        self.assertIn("slug", ctx.exception.message_dict)
        self.assertIn("auth", "".join(ctx.exception.message_dict["slug"]))

    def test_reserved_slug_conferences_rejected(self):
        conference = make_conference(slug="conferences")
        with self.assertRaises(ValidationError) as ctx:
            conference.full_clean()
        self.assertIn("slug", ctx.exception.message_dict)

    def test_reserved_slug_check_is_case_insensitive(self):
        conference = make_conference(slug="Admin")
        with self.assertRaises(ValidationError) as ctx:
            conference.full_clean()
        self.assertIn("slug", ctx.exception.message_dict)

    def test_normal_slug_accepted(self):
        # The 0014 migration seed already created "wsc2026" in the test
        # DB, so exercise full_clean with a slug that cannot collide.
        make_conference(slug="wsc2027").full_clean()


class TestYearProperty(TestCase):
    def test_year_derived_from_date_start(self):
        info = make_info(date_start=date(2027, 5, 20), date_end=date(2027, 5, 22))
        self.assertEqual(info.year, 2027)

    def test_year_is_none_when_date_start_missing(self):
        self.assertIsNone(make_info().year)


class TestStatusProperty(TestCase):
    def status_on(self, today, **overrides):
        info = make_info(**overrides)
        with patch("django.utils.timezone.localdate", return_value=today):
            return info.status

    def test_missing_dates_default_to_future(self):
        self.assertEqual(self.status_on(date(2026, 10, 4)), "future")

    def test_missing_end_date_is_future(self):
        self.assertEqual(
            self.status_on(date(2026, 10, 4), date_start=date(2026, 10, 4)),
            "future",
        )

    def test_before_start_is_future(self):
        self.assertEqual(
            self.status_on(
                date(2026, 1, 1),
                date_start=date(2026, 5, 1),
                date_end=date(2026, 5, 2),
            ),
            "future",
        )

    def test_after_end_is_past(self):
        self.assertEqual(
            self.status_on(
                date(2026, 5, 3),
                date_start=date(2026, 5, 1),
                date_end=date(2026, 5, 2),
            ),
            "past",
        )

    def test_first_day_is_running(self):
        self.assertEqual(
            self.status_on(
                date(2026, 5, 1),
                date_start=date(2026, 5, 1),
                date_end=date(2026, 5, 2),
            ),
            "running",
        )

    def test_last_day_is_running(self):
        self.assertEqual(
            self.status_on(
                date(2026, 5, 2),
                date_start=date(2026, 5, 1),
                date_end=date(2026, 5, 2),
            ),
            "running",
        )


class TestStr(TestCase):
    def test_str_returns_slug(self):
        self.assertEqual(str(make_conference(slug="wsc2026")), "wsc2026")


class _FakeConferenceTable:
    """In-memory stand-in for the historical Conference model — the
    queryset surface the 0014 seed functions use (get_or_create,
    filter(...).first()), with stable row identities so the info seed
    can attach to the very same conference object."""

    def __init__(self):
        self.rows = []

    @property
    def objects(self):
        return self

    def get_or_create(self, **kwargs):
        for row in self.rows:
            if all(getattr(row, key) == value for key, value in kwargs.items()):
                return row, False
        row = SimpleNamespace(**kwargs)
        self.rows.append(row)
        return row, True

    def filter(self, **kwargs):
        matching = [
            row
            for row in self.rows
            if all(getattr(row, key) == value for key, value in kwargs.items())
        ]
        return SimpleNamespace(first=lambda: matching[0] if matching else None)


class _FakeConferenceInfoTable:
    """In-memory get_or_create for the historical ConferenceInfo seed."""

    def __init__(self):
        self.rows = []

    @property
    def objects(self):
        return self

    def get_or_create(self, conference, defaults):
        for row in self.rows:
            if row.conference == conference:
                return row, False
        row = SimpleNamespace(conference=conference, **defaults)
        self.rows.append(row)
        return row, True


class _MigrationApps:
    """`apps` registry stand-in for the 0014 seed functions: in-memory
    fakes for the historical Conference and ConferenceInfo models."""

    def __init__(self):
        self._conference = _FakeConferenceTable()
        self._conference_info = _FakeConferenceInfoTable()

    def get_model(self, app_label, model_name):
        if model_name == "Conference":
            return self._conference
        if model_name == "ConferenceInfo":
            return self._conference_info
        raise LookupError(f"{app_label}.{model_name}")


def seed_migration():
    return importlib.import_module("core.migrations.0014_conference")


class TestSeedConference(TestCase):
    def test_seed_creates_wsc2026(self):
        apps = _MigrationApps()

        seed_migration().seed_conference(apps, None)

        self.assertEqual([row.slug for row in apps._conference.rows], ["wsc2026"])

    def test_seed_is_idempotent(self):
        apps = _MigrationApps()
        seed = seed_migration().seed_conference

        seed(apps, None)
        seed(apps, None)

        self.assertEqual(len(apps._conference.rows), 1)


class TestSeedConferenceInfo(TestCase):
    def test_no_op_without_wsc2026_conference(self):
        apps = _MigrationApps()

        seed_migration().seed_conference_info(apps, None)

        self.assertEqual(apps._conference_info.rows, [])

    def test_creates_fallback_row(self):
        apps = _MigrationApps()
        seed_migration().seed_conference(apps, None)

        seed_migration().seed_conference_info(apps, None)

        self.assertEqual(len(apps._conference_info.rows), 1)
        row = apps._conference_info.rows[0]
        self.assertEqual(row.conference.slug, "wsc2026")
        self.assertEqual(row.title, "Workshop on Scientific Computing")
        self.assertEqual(row.location, "Děčín")
        self.assertEqual(row.badge_title, "WSC 2026")

    def test_preserves_existing_row(self):
        # The upgrade path: an existing ConferenceInfo already points at
        # wsc2026 (conference FK backfill) — the fallback defaults must
        # not overwrite it.
        apps = _MigrationApps()
        seed_migration().seed_conference(apps, None)
        apps._conference_info.rows.append(
            SimpleNamespace(
                conference=apps._conference.rows[0],
                title="Winter Workshop",
                location="Praha",
                badge_title="WW 2024",
            )
        )

        seed_migration().seed_conference_info(apps, None)

        self.assertEqual(len(apps._conference_info.rows), 1)
        row = apps._conference_info.rows[0]
        self.assertEqual(row.title, "Winter Workshop")
        self.assertEqual(row.location, "Praha")
        self.assertEqual(row.badge_title, "WW 2024")

    def test_is_idempotent(self):
        apps = _MigrationApps()
        seed_migration().seed_conference(apps, None)
        seed = seed_migration().seed_conference_info

        seed(apps, None)
        seed(apps, None)

        self.assertEqual(len(apps._conference_info.rows), 1)
