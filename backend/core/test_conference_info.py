"""Conference config endpoints and the global (unscoped) routes.

Pins the conference-info read payload (web + logistics + derived year),
the write serializer, the accommodation projection, the no-writes-on-GET
contract, and the slug-independent global routes (auth, list).
"""

from datetime import date

from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from .conftest import api
from .models import AccommodationOption, Conference

SLUG_A = "wsc2026-test"
SLUG_B = "wsc2027-test"

# id + 17 web fields + 8 logistics fields + derived year.
INFO_PAYLOAD_KEYS = frozenset(
    {
        "id",
        "description",
        "registration_instructions",
        "registration_opening",
        "registration_deadline",
        "submission_edit_deadline",
        "registration_allow_talk",
        "registration_allow_poster",
        "registration_allow_attend",
        "registration_fee_note",
        "grant_text",
        "venue_text",
        "footer_venue_text",
        "venue_photo",
        "conference_office_text",
        "website_url",
        "poster_url",
        "info_desk_email",
        "venue_map_embed_url",
        "copyright_text",
        "program_text",
        "title",
        "date_start",
        "date_end",
        "location",
        "card_photo",
        "hero_photo",
        "short_description",
        "badge_title",
        "year",
    }
)


def alpha_conference():
    return Conference.objects.get_or_create(slug=SLUG_A)[0]


def beta_conference():
    return Conference.objects.get_or_create(slug=SLUG_B)[0]


class InfoTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.conf_a = alpha_conference()
        self.conf_b = beta_conference()

    def superuser_client(self):
        user = User.objects.create_user(
            username="admin-info", password="pw", is_staff=True, is_superuser=True
        )
        token = RefreshToken.for_user(user)
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {token.access_token}")
        return client


class TestConferenceInfoEndpoint(InfoTestCase):
    def test_get_does_not_create_rows(self):
        before = Conference.objects.count()

        response = self.client.get(api("conference-info/"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(Conference.objects.count(), before)
        self.assertEqual(response.json()["id"], self.conf_a.pk)

        self.client.get(api("conference-info/", slug=SLUG_B))
        self.assertEqual(Conference.objects.count(), before)

    def test_payload_has_exactly_the_30_payload_keys(self):
        for slug in (SLUG_A, SLUG_B):
            with self.subTest(slug=slug):
                response = self.client.get(api("conference-info/", slug=slug))
                self.assertEqual(response.status_code, 200)
                self.assertEqual(frozenset(response.json().keys()), INFO_PAYLOAD_KEYS)

    def test_patch_on_a_does_not_leak_to_b(self):
        staff = self.superuser_client()
        response = staff.patch(
            api("conference-info/edit/"),
            {"grant_text": "Only A grant"},
            format="json",
        )
        self.assertEqual(response.status_code, 200)

        payload_a = self.client.get(api("conference-info/")).json()
        self.assertEqual(payload_a["grant_text"], "Only A grant")
        payload_b = self.client.get(api("conference-info/", slug=SLUG_B)).json()
        self.assertNotEqual(payload_b["grant_text"], "Only A grant")

    def test_footer_venue_text_is_independent_of_venue_text(self):
        staff = self.superuser_client()
        response = staff.patch(
            api("conference-info/edit/"),
            {"footer_venue_text": "Footer-only venue blurb"},
            format="json",
        )
        self.assertEqual(response.status_code, 200)

        payload = self.client.get(api("conference-info/")).json()
        self.assertEqual(payload["footer_venue_text"], "Footer-only venue blurb")
        self.assertNotEqual(payload["footer_venue_text"], payload["venue_text"])

        # Editing the venue page text must not touch the footer text.
        response = staff.patch(
            api("conference-info/edit/"),
            {"venue_text": "Venue-page-only text"},
            format="json",
        )
        self.assertEqual(response.status_code, 200)

        payload = self.client.get(api("conference-info/")).json()
        self.assertEqual(payload["venue_text"], "Venue-page-only text")
        self.assertEqual(payload["footer_venue_text"], "Footer-only venue blurb")

    def test_write_serializer_persists_logistics_but_ignores_year(self):
        staff = self.superuser_client()
        response = staff.patch(
            api("conference-info/edit/"),
            {
                "title": "Renamed Alpha",
                "year": 9999,
                "date_start": "2030-01-01",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.conf_a.refresh_from_db()
        self.assertEqual(self.conf_a.title, "Renamed Alpha")
        self.assertEqual(self.conf_a.date_start, date(2030, 1, 1))
        # year is derived (never stored): the sent 9999 must not stick.
        self.assertEqual(self.conf_a.year, 2030)
        payload = response.json()
        self.assertEqual(payload["id"], self.conf_a.pk)
        self.assertEqual(payload["title"], "Renamed Alpha")
        self.assertEqual(payload["date_start"], "2030-01-01")
        self.assertEqual(payload["year"], 2030)


class TestConferenceInfoEditValidation(InfoTestCase):
    def test_contribution_flags_persist(self):
        staff = self.superuser_client()
        response = staff.patch(
            api("conference-info/edit/"),
            {
                "registration_allow_talk": False,
                "registration_allow_poster": True,
                "registration_allow_attend": False,
            },
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.conf_a.refresh_from_db()
        self.assertFalse(self.conf_a.registration_allow_talk)
        self.assertTrue(self.conf_a.registration_allow_poster)
        self.assertFalse(self.conf_a.registration_allow_attend)
        self.assertEqual(self.conf_a.allowed_contribution_types, ("poster",))

    def test_disabling_every_contribution_type_is_rejected(self):
        staff = self.superuser_client()
        response = staff.patch(
            api("conference-info/edit/"),
            {
                "registration_allow_talk": False,
                "registration_allow_poster": False,
                "registration_allow_attend": False,
            },
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("registration_allow_talk", response.json())

    def test_deadline_before_registration_deadline_rejected(self):
        staff = self.superuser_client()
        response = staff.patch(
            api("conference-info/edit/"),
            {
                "registration_deadline": "2026-06-30",
                "submission_edit_deadline": "2026-06-01",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("submission_edit_deadline", response.json())

    def test_deadline_after_conference_end_rejected(self):
        staff = self.superuser_client()
        response = staff.patch(
            api("conference-info/edit/"),
            {
                "date_end": "2026-05-31",
                "submission_edit_deadline": "2026-06-30",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("submission_edit_deadline", response.json())

    def test_in_range_deadline_accepted_and_persisted(self):
        staff = self.superuser_client()
        response = staff.patch(
            api("conference-info/edit/"),
            {
                "registration_deadline": "2026-05-01",
                "date_end": "2026-06-30",
                "submission_edit_deadline": "2026-06-15",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.conf_a.refresh_from_db()
        self.assertEqual(self.conf_a.submission_edit_deadline, date(2026, 6, 15))

    def test_unpatched_registration_deadline_still_bounds_the_deadline(self):
        # Partial PATCH: the instance supplies the unpatched bound.
        self.conf_a.registration_deadline = date(2026, 6, 30)
        self.conf_a.save()
        staff = self.superuser_client()
        response = staff.patch(
            api("conference-info/edit/"),
            {"submission_edit_deadline": "2026-06-01"},
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("submission_edit_deadline", response.json())


class TestAccommodationEndpoint(InfoTestCase):
    def test_get_reads_the_conference_without_creating_rows(self):
        before = Conference.objects.count()

        response = self.client.get(api("accommodation/"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(Conference.objects.count(), before)
        self.assertEqual(response.json()["id"], self.conf_a.pk)

    def test_options_are_nested_under_their_conference(self):
        AccommodationOption.objects.create(
            conference=self.conf_a, name="Hotel A", order=1
        )
        AccommodationOption.objects.create(
            conference=self.conf_b, name="Hotel B", order=1
        )

        payload = self.client.get(api("accommodation/")).json()

        self.assertEqual([option["name"] for option in payload["options"]], ["Hotel A"])

    def test_patch_description_on_a_does_not_leak_to_b(self):
        staff = self.superuser_client()
        response = staff.patch(
            api("admin/accommodation/"),
            {"description": "Only A hotels"},
            format="json",
        )
        self.assertEqual(response.status_code, 200)

        payload_a = self.client.get(api("accommodation/")).json()
        self.assertEqual(payload_a["description"], "Only A hotels")
        payload_b = self.client.get(api("accommodation/", slug=SLUG_B)).json()
        self.assertEqual(payload_b["description"], "")


class TestGlobalEndpoints(TestCase):
    def setUp(self):
        self.client = APIClient()
        User.objects.create_user(username="admin-global", password="pw", is_staff=True)

    def test_login_empty_body_400_not_404(self):
        response = self.client.post("/api/auth/login/", {}, format="json")
        self.assertEqual(response.status_code, 400)

    def test_login_and_refresh_happy_path_without_slug(self):
        response = self.client.post(
            "/api/auth/login/",
            {"username": "admin-global", "password": "pw"},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertNotIn("access", body)
        self.assertNotIn("refresh", body)
        self.assertTrue(response.cookies["conference-jwt-access"]["httponly"])

        response = self.client.post("/api/auth/refresh/", {}, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("access", response.json())
        self.assertIn("conference-jwt-access", response.cookies)

    def test_slug_prefix_does_not_shadow_auth(self):
        alpha_conference()
        response = self.client.post(
            api("auth/login/"),
            {"username": "admin-global", "password": "pw"},
            format="json",
        )
        self.assertEqual(response.status_code, 404)

    def test_conferences_list_smoke(self):
        # Payload shape and ordering are pinned in test_conferences_endpoint.
        response = self.client.get("/api/conferences/")
        self.assertEqual(response.status_code, 200)
        self.assertIsInstance(response.json(), list)
