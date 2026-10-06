"""Tests for the global /api/conferences/ endpoint and admin policies."""

from datetime import date
from unittest.mock import patch

from django.contrib import admin as django_admin
from django.test import RequestFactory, TestCase
from django.urls import resolve
from rest_framework.test import APIClient

from .admin import ConferenceAdmin
from .models import Conference, ConferenceInfo
from .views import ConferenceListView

TODAY = date(2026, 10, 4)


def make_conference(slug, **info_fields):
    conference = Conference.objects.create(slug=slug)
    ConferenceInfo.objects.create(conference=conference, **info_fields)
    return conference


class ConferencesEndpointMixin(TestCase):
    def setUp(self):
        # The 0014 seed inserts "wsc2026" during migrations; drop it so
        # each test controls the full conference set.
        Conference.objects.all().delete()
        self.client = APIClient()


class TestConferenceListCards(ConferencesEndpointMixin):
    def test_get_returns_200_without_authentication(self):
        response = self.client.get("/api/conferences/")

        self.assertEqual(response.status_code, 200)
        self.assertIsInstance(response.data, list)

    def test_card_payload_has_exactly_the_nine_card_keys(self):
        make_conference(
            "wsc2027",
            title="Winter Workshop 2027",
            date_start=date(2027, 1, 27),
            date_end=date(2027, 1, 29),
            location="Praha",
            short_description="A workshop.",
        )

        response = self.client.get("/api/conferences/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        card = response.data[0]
        self.assertEqual(
            set(card.keys()),
            {
                "slug",
                "title",
                "date_start",
                "date_end",
                "year",
                "location",
                "card_photo",
                "short_description",
                "status",
            },
        )
        self.assertEqual(card["slug"], "wsc2027")
        self.assertEqual(card["title"], "Winter Workshop 2027")
        self.assertEqual(card["date_start"], "2027-01-27")
        self.assertEqual(card["date_end"], "2027-01-29")
        self.assertEqual(card["year"], 2027)
        self.assertEqual(card["location"], "Praha")
        self.assertIsNone(card["card_photo"])
        self.assertEqual(card["short_description"], "A workshop.")
        self.assertEqual(card["status"], "future")


class TestConferenceListOrdering(ConferencesEndpointMixin):
    def test_order_is_running_then_future_then_past(self):
        make_conference(
            "run-a",
            title="A",
            date_start=date(2026, 10, 3),
            date_end=date(2026, 10, 5),
        )
        make_conference(
            "run-b",
            title="B",
            date_start=date(2026, 10, 4),
            date_end=date(2026, 10, 6),
        )
        make_conference(
            "fut-b",
            title="C",
            date_start=date(2027, 3, 1),
            date_end=date(2027, 3, 3),
        )
        make_conference(
            "fut-a",
            title="D",
            date_start=date(2026, 11, 1),
            date_end=date(2026, 11, 2),
        )
        make_conference("fut-undated", title="E")
        make_conference(
            "past-a",
            title="F",
            date_start=date(2026, 5, 1),
            date_end=date(2026, 5, 2),
        )
        make_conference(
            "past-b",
            title="G",
            date_start=date(2026, 1, 10),
            date_end=date(2026, 1, 15),
        )

        with patch("django.utils.timezone.localdate", return_value=TODAY):
            response = self.client.get("/api/conferences/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            [card["slug"] for card in response.data],
            ["run-a", "run-b", "fut-a", "fut-b", "fut-undated", "past-a", "past-b"],
        )
        statuses = {card["slug"]: card["status"] for card in response.data}
        self.assertEqual(statuses["run-a"], "running")
        self.assertEqual(statuses["run-b"], "running")
        self.assertEqual(statuses["fut-a"], "future")
        self.assertEqual(statuses["fut-b"], "future")
        self.assertEqual(statuses["fut-undated"], "future")
        self.assertEqual(statuses["past-a"], "past")
        self.assertEqual(statuses["past-b"], "past")


class TestConferenceListRouting(ConferencesEndpointMixin):
    def test_url_resolves_to_conference_list_view(self):
        match = resolve("/api/conferences/")

        self.assertIs(match.func.view_class, ConferenceListView)
        self.assertEqual(match.url_name, "conference-list")

    def test_registered_before_slug_include_even_with_shadow_slug(self):
        # A DB row bypassing full_clean with the reserved slug would
        # shadow the endpoint if the slug include came first.
        Conference.objects.create(slug="conferences")

        response = self.client.get("/api/conferences/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual([card["slug"] for card in response.data], ["conferences"])


class TestConferenceAdminPolicy(TestCase):
    def setUp(self):
        self.request = RequestFactory().get("/")

    def test_delete_permission_is_denied(self):
        model_admin = ConferenceAdmin(Conference, django_admin.site)

        self.assertIs(model_admin.has_delete_permission(self.request), False)

    def test_bulk_actions_are_disabled(self):
        model_admin = ConferenceAdmin(Conference, django_admin.site)

        self.assertIsNone(model_admin.actions)

    def test_every_other_core_admin_shows_conference_column_and_filter(self):
        registered = django_admin.site._registry

        core_admins = {
            model._meta.object_name: admin_instance
            for model, admin_instance in registered.items()
            if model._meta.app_label == "core" and model is not Conference
        }

        self.assertEqual(len(core_admins), 12)
        for object_name, admin_instance in core_admins.items():
            self.assertIn("conference", admin_instance.list_display, msg=object_name)
            self.assertIn("conference", admin_instance.list_filter, msg=object_name)
