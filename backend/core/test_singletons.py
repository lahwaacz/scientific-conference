"""Per-conference singleton rows and the global (unscoped) endpoints.

Pins the get_or_create-per-conference contract for ConferenceInfo and
AccommodationInfo, the conference-info read payload (web + logistics +
derived year), the pinned write serializer, and the slug-independent
global routes (auth, list).
"""

from datetime import date

from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from .conftest import api
from .models import AccommodationInfo, Conference, ConferenceInfo

SLUG_A = "wsc2026-test"
SLUG_B = "wsc2027-test"

# id + 15 web fields + 8 logistics fields + derived year.
INFO_PAYLOAD_KEYS = frozenset(
    {
        "id",
        "description",
        "registration_instructions",
        "registration_opening",
        "registration_deadline",
        "registration_fee_note",
        "grant_text",
        "venue_text",
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

    def staff_client(self):
        user = User.objects.create_user(
            username="admin-info", password="pw", is_staff=True
        )
        token = RefreshToken.for_user(user)
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {token.access_token}")
        return client


class TestConferenceInfoSingleton(InfoTestCase):
    def test_get_autocreates_exactly_one_row_for_that_conference(self):
        self.assertFalse(ConferenceInfo.objects.filter(conference=self.conf_a).exists())

        response = self.client.get(api("conference-info/"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            ConferenceInfo.objects.filter(conference=self.conf_a).count(), 1
        )
        self.assertEqual(
            ConferenceInfo.objects.get(conference=self.conf_a).conference, self.conf_a
        )

        # Repeat GET reuses the row instead of growing the table.
        response = self.client.get(api("conference-info/"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            ConferenceInfo.objects.filter(conference=self.conf_a).count(), 1
        )

    def test_other_conference_has_no_row_until_its_own_get(self):
        self.client.get(api("conference-info/"))
        self.assertFalse(ConferenceInfo.objects.filter(conference=self.conf_b).exists())

        response = self.client.get(api("conference-info/", slug=SLUG_B))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            ConferenceInfo.objects.get(conference=self.conf_b).conference, self.conf_b
        )

    def test_payload_has_exactly_the_25_payload_keys(self):
        for slug in (SLUG_A, SLUG_B):
            with self.subTest(slug=slug):
                response = self.client.get(api("conference-info/", slug=slug))
                self.assertEqual(response.status_code, 200)
                self.assertEqual(frozenset(response.json().keys()), INFO_PAYLOAD_KEYS)

    def test_patch_on_a_does_not_leak_to_b(self):
        staff = self.staff_client()
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

    def test_write_serializer_persists_logistics_but_ignores_year_and_conference(self):
        staff = self.staff_client()
        response = staff.patch(
            api("conference-info/edit/"),
            {
                "title": "Renamed Alpha",
                "year": 9999,
                "date_start": "2030-01-01",
                "conference": self.conf_b.pk,
            },
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        info = ConferenceInfo.objects.get(conference=self.conf_a)
        self.assertEqual(info.title, "Renamed Alpha")
        self.assertEqual(info.date_start, date(2030, 1, 1))
        # year is derived (never stored): the sent 9999 must not stick.
        self.assertEqual(info.year, 2030)
        # The conference FK is not reassignable via this endpoint.
        self.assertEqual(info.conference, self.conf_a)
        payload = response.json()
        self.assertEqual(payload["title"], "Renamed Alpha")
        self.assertEqual(payload["date_start"], "2030-01-01")
        self.assertEqual(payload["year"], 2030)


class TestAccommodationInfoSingleton(InfoTestCase):
    def test_get_autocreates_per_conference(self):
        self.assertEqual(AccommodationInfo.objects.count(), 0)

        self.assertEqual(self.client.get(api("accommodation/")).status_code, 200)
        self.assertEqual(AccommodationInfo.objects.count(), 1)
        self.assertEqual(AccommodationInfo.objects.get().conference, self.conf_a)

        self.assertEqual(
            self.client.get(api("accommodation/", slug=SLUG_B)).status_code, 200
        )
        self.assertEqual(AccommodationInfo.objects.count(), 2)
        self.assertEqual(
            AccommodationInfo.objects.get(conference=self.conf_b).conference,
            self.conf_b,
        )

    def test_patch_description_on_a_does_not_leak_to_b(self):
        staff = self.staff_client()
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
        self.assertIn("access", response.json())
        refresh = response.json()["refresh"]

        response = self.client.post(
            "/api/auth/refresh/", {"refresh": refresh}, format="json"
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("access", response.json())

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
