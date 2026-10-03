"""Tests for admin content endpoints (info, accommodation, hiking, people)."""

from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from .models import (
    AccommodationInfo,
    AccommodationOption,
    ConferenceInfo,
    HikingRoute,
    HikingStop,
    Organizer,
)


class AdminTestCase(TestCase):
    def setUp(self):
        admin = User.objects.create_user(username="admin", password="pw", is_staff=True)
        token = RefreshToken.for_user(admin)
        self.token = token
        self.client = APIClient()
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token.access_token}")


class TestConferenceInfoAdmin(AdminTestCase):
    def test_patch_creates_top_center_text(self):
        response = self.client.patch(
            "/api/conference-info/edit/",
            {"grant_text": "New grant text"},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        info = ConferenceInfo.objects.get(id=1)
        self.assertEqual(info.grant_text, "New grant text")

    def test_patch_rejects_anonymous(self):
        self.client.credentials()
        response = self.client.patch(
            "/api/conference-info/edit/",
            {"grant_text": "Nope"},
            format="json",
        )
        self.assertEqual(response.status_code, 401)


class TestAccommodationAdmin(AdminTestCase):
    def test_patch_info_description(self):
        response = self.client.patch(
            "/api/admin/accommodation/",
            {"description": "Book early"},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        info = AccommodationInfo.objects.get(id=1)
        self.assertEqual(info.description, "Book early")

    def test_option_create_patch_delete_cycle(self):
        response = self.client.post(
            "/api/admin/accommodation/options/",
            {"name": "Hotel A", "order": 1},
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        option = AccommodationOption.objects.get(name="Hotel A")
        self.assertEqual(option.info.id, 1)

        response = self.client.patch(
            f"/api/admin/accommodation/options/{option.id}/",
            {"name": "Hotel B"},
            format="json",
        )
        self.assertEqual(response.status_code, 200)

        response = self.client.delete(f"/api/admin/accommodation/options/{option.id}/")
        self.assertEqual(response.status_code, 204)
        self.assertEqual(AccommodationOption.objects.count(), 0)

    def test_option_bad_pk_returns_500(self):
        # Deliberate: the views call objects.get(pk) unguarded and the
        # exception surfaces as a 500 instead of a friendly 404. The DRF
        # test client re-raises server exceptions by default, so ask for
        # the raw response.
        self.client.raise_request_exception = False
        response = self.client.patch(
            "/api/admin/accommodation/options/999/",
            {"name": "Ghost"},
            format="json",
        )
        self.assertEqual(response.status_code, 500)
        response = self.client.delete("/api/admin/accommodation/options/999/")
        self.assertEqual(response.status_code, 500)


class TestHikingAdmin(AdminTestCase):
    def setUp(self):
        super().setUp()
        self.route = HikingRoute.objects.create(name="Alpenweg")

    def test_route_create(self):
        response = self.client.post(
            "/api/hiking/admin/", {"name": "Besseggen"}, format="json"
        )
        self.assertEqual(response.status_code, 201)

    def test_route_patch_requires_id(self):
        response = self.client.patch(
            "/api/hiking/admin/", {"name": "No Id"}, format="json"
        )
        self.assertEqual(response.status_code, 400)

    def test_route_delete_cascades_stops(self):
        HikingStop.objects.create(route=self.route, name="Stop 1", order=1)
        HikingStop.objects.create(route=self.route, name="Stop 2", order=2)

        response = self.client.delete(
            "/api/hiking/admin/", {"id": self.route.id}, format="json"
        )

        self.assertEqual(response.status_code, 204)
        self.assertEqual(HikingRoute.objects.count(), 0)
        self.assertEqual(HikingStop.objects.count(), 0)

    def test_stop_create_patch_delete(self):
        response = self.client.post(
            "/api/hiking/stops/",
            {"route": self.route.id, "name": "S1", "order": 1},
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        stop = HikingStop.objects.get(name="S1")

        response = self.client.patch(
            f"/api/hiking/stops/{stop.id}/", {"order": 5}, format="json"
        )
        self.assertEqual(response.status_code, 200)

        response = self.client.delete(f"/api/hiking/stops/{stop.id}/")
        self.assertEqual(response.status_code, 204)

    def test_stop_bad_pk_returns_500(self):
        # Same unguarded objects.get(pk) pattern as accommodation options.
        self.client.raise_request_exception = False
        response = self.client.patch(
            "/api/hiking/stops/999/", {"order": 1}, format="json"
        )
        self.assertEqual(response.status_code, 500)
        response = self.client.delete("/api/hiking/stops/999/")
        self.assertEqual(response.status_code, 500)


class TestPeoplePermissions(AdminTestCase):
    def setUp(self):
        super().setUp()
        self.organizer = Organizer.objects.create(name="Org", email="o@x.cz")

    def test_organizer_list_get_is_public(self):
        self.client.credentials()
        response = self.client.get("/api/organizers/")
        self.assertEqual(response.status_code, 200)

    def test_organizer_list_post_requires_admin(self):
        self.client.credentials()
        response = self.client.post("/api/organizers/", {"name": "Anon"}, format="json")
        self.assertEqual(response.status_code, 401)

        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.token.access_token}")
        response = self.client.post(
            "/api/organizers/",
            {"name": "Staff Member", "email": "s@x.cz"},
            format="json",
        )
        self.assertEqual(response.status_code, 201)

    def test_organizer_detail_get_requires_admin(self):
        self.client.credentials()
        response = self.client.get(f"/api/organizers/{self.organizer.id}/")
        self.assertEqual(response.status_code, 401)

    def test_committee_list_get_is_public(self):
        self.client.credentials()
        response = self.client.get("/api/committees/")
        self.assertEqual(response.status_code, 200)
