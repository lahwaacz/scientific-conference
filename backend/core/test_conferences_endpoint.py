"""Tests for the global /api/conferences/ endpoint and admin policies."""

from datetime import date
from unittest.mock import patch

from django.contrib import admin as django_admin
from django.contrib.auth.models import User
from django.core.exceptions import PermissionDenied
from django.test import RequestFactory, TestCase
from django.urls import resolve, reverse
from rest_framework.test import APIClient

from .admin import ConferenceAdmin
from .models import Conference, Participant, Role
from .views import ConferenceListView

TODAY = date(2026, 10, 4)


def make_conference(slug, **info_fields):
    return Conference.objects.create(slug=slug, **info_fields)


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
        self.superuser = User.objects.create_superuser(
            username="conference-admin", password="pw", email="admin@example.com"
        )
        self.request = RequestFactory().get("/")
        self.request.user = self.superuser

    def model_admin(self):
        return ConferenceAdmin(Conference, django_admin.site)

    def test_delete_permission_is_allowed_without_references(self):
        conference = Conference.objects.create(slug="unreferenced-conference")

        self.assertTrue(
            self.model_admin().has_delete_permission(self.request, conference)
        )

    def test_delete_permission_is_denied_with_a_reference(self):
        conference = Conference.objects.create(slug="referenced-conference")
        Participant.objects.create(conference=conference, name="Participant")

        self.assertFalse(
            self.model_admin().has_delete_permission(self.request, conference)
        )

    def test_bulk_actions_are_disabled(self):
        self.assertIsNone(self.model_admin().actions)

    def test_change_form_exposes_the_merged_conference_config(self):
        conference = Conference.objects.create(slug="config-form")
        self.client.force_login(self.superuser)

        response = self.client.get(
            reverse("admin:core_conference_change", args=[conference.pk])
        )

        self.assertEqual(response.status_code, 200)
        for field in (
            "title",
            "date_start",
            "registration_deadline",
            "program_text",
            "accommodation_description",
        ):
            self.assertContains(response, f'name="{field}"')

    def test_admin_fieldsets_cover_every_editable_conference_field(self):
        fieldsets = self.model_admin().fieldsets or ()
        fields = [
            field for _section, options in fieldsets for field in options["fields"]
        ]
        editable = [
            field.name
            for field in Conference._meta.fields
            if field.editable and not field.auto_created
        ]

        self.assertEqual(set(fields), set(editable))
        self.assertEqual(len(fields), len(set(fields)))

    def test_delete_view_deletes_an_unreferenced_conference(self):
        conference = Conference.objects.create(slug="deletable-conference")
        self.client.force_login(self.superuser)

        response = self.client.post(
            reverse("admin:core_conference_delete", args=[conference.pk]),
            {"post": "yes"},
        )

        self.assertEqual(response.status_code, 302)
        self.assertFalse(Conference.objects.filter(pk=conference.pk).exists())

    def test_delete_view_redirects_a_referenced_conference_with_a_message(self):
        conference = Conference.objects.create(slug="protected-conference")
        Participant.objects.create(conference=conference, name="Participant")
        self.client.force_login(self.superuser)
        url = reverse("admin:core_conference_delete", args=[conference.pk])

        self.assertRedirects(
            self.client.get(url),
            reverse("admin:core_conference_change", args=[conference.pk]),
        )

        response = self.client.post(url, {"post": "yes"}, follow=True)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "still has related objects")
        self.assertTrue(Conference.objects.filter(pk=conference.pk).exists())

    def test_delete_model_refuses_a_conference_that_gained_a_reference(self):
        conference = Conference.objects.create(slug="race-conference")
        Participant.objects.create(conference=conference, name="Participant")

        with self.assertRaises(PermissionDenied):
            self.model_admin().delete_model(self.request, conference)

        self.assertTrue(Conference.objects.filter(pk=conference.pk).exists())

    def test_delete_queryset_refuses_a_referenced_conference(self):
        conference = Conference.objects.create(slug="bulk-conference")
        Participant.objects.create(conference=conference, name="Participant")
        queryset = Conference.objects.filter(pk=conference.pk)

        with self.assertRaises(PermissionDenied):
            self.model_admin().delete_queryset(self.request, queryset)

        self.assertTrue(Conference.objects.filter(pk=conference.pk).exists())

    def test_delete_queryset_refuses_when_only_one_conference_is_referenced(self):
        referenced = Conference.objects.create(slug="bulk-referenced")
        Participant.objects.create(conference=referenced, name="Participant")
        clean = Conference.objects.create(slug="bulk-clean")
        queryset = Conference.objects.filter(pk__in=[referenced.pk, clean.pk])

        with self.assertRaises(PermissionDenied):
            self.model_admin().delete_queryset(self.request, queryset)

        self.assertTrue(Conference.objects.filter(pk=referenced.pk).exists())
        self.assertTrue(Conference.objects.filter(pk=clean.pk).exists())

    def test_delete_permission_without_an_object_checks_the_permission_only(self):
        self.assertTrue(self.model_admin().has_delete_permission(self.request))

    def test_change_form_hides_the_delete_link_for_a_referenced_conference(self):
        conference = Conference.objects.create(slug="no-delete-link")
        Participant.objects.create(conference=conference, name="Participant")
        self.client.force_login(self.superuser)

        response = self.client.get(
            reverse("admin:core_conference_change", args=[conference.pk])
        )

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(
            response,
            reverse("admin:core_conference_delete", args=[conference.pk]),
        )

    def test_change_form_shows_the_delete_link_for_an_unreferenced_conference(self):
        conference = Conference.objects.create(slug="delete-link")
        self.client.force_login(self.superuser)

        response = self.client.get(
            reverse("admin:core_conference_change", args=[conference.pk])
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response,
            reverse("admin:core_conference_delete", args=[conference.pk]),
        )

    def test_every_other_core_admin_shows_conference_column_and_filter(self):
        registered = django_admin.site._registry

        # Role is conference-free reference data (like auth tables), so
        # it is exempt alongside Conference itself.
        core_admins = {
            model._meta.object_name: admin_instance
            for model, admin_instance in registered.items()
            if model._meta.app_label == "core" and model not in (Conference, Role)
        }

        self.assertEqual(len(core_admins), 9)
        for object_name, admin_instance in core_admins.items():
            self.assertIn("conference", admin_instance.list_display, msg=object_name)
            self.assertIn("conference", admin_instance.list_filter, msg=object_name)
