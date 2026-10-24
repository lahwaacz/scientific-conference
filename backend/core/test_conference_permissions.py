"""Conference-level authorization: manager grants, the route matrix, and the
Django-admin lock.

The route matrix is classified against the pinned tail table in
test_conference_isolation so a new scoped route cannot ship without an
authorization assertion.
"""

from datetime import date

from django.contrib import admin as django_admin
from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from .conftest import api
from .models import (
    AccommodationOption,
    Conference,
    ConferenceDay,
    ConferenceManagers,
    HikingRoute,
    HikingStop,
    ParticipantSubmission,
    Person,
    Session,
    Talk,
)
from .test_conference_isolation import EXPECTED_ROUTE_TAILS

User = get_user_model()

WSC = "wsc2026-test"
OTHER = "wsc2027-test"

PUBLIC_TAIL_PATTERNS = {
    "program/",
    "participants/",
    "participants/<int:pk>/",
    "abstracts/",
    "abstracts/<int:pk>/",
    "talks/",
    "talks/<int:pk>/",
    "people/",
    "accommodation/",
    "conference-info/",
    "submit/",
    "track/<str:tracking_token>/",
    "hiking/",
}

# (method, tail pattern, body, fixture attribute used for <int:pk>)
ADMIN_ROUTES = [
    ("get", "admin-panel/", None, None),
    ("get", "admin/submissions/", None, None),
    ("get", "admin/submissions/<int:pk>/", None, "submission"),
    ("post", "admin/submissions/<int:pk>/publish/", {}, "submission"),
    ("post", "admin/submissions/<int:pk>/unpublish/", {}, "submission"),
    ("post", "admin/submissions/<int:pk>/reject/", {}, "submission"),
    ("post", "admin/submissions/<int:pk>/restore/", {}, "submission"),
    ("get", "admin/talks/unscheduled/", None, None),
    ("patch", "admin/talks/<int:pk>/schedule/", {}, "talk"),
    ("delete", "admin/talks/<int:pk>/delete/", None, "talk"),
    ("post", "admin/talks/create-break/", {}, None),
    ("post", "admin/sessions/create/", {}, None),
    ("get", "admin/sessions/", None, None),
    ("patch", "admin/sessions/<int:pk>/", {}, "session"),
    ("patch", "admin/sessions/<int:pk>/update-time/", {}, "session"),
    ("delete", "admin/sessions/<int:pk>/delete/", None, "session"),
    ("post", "admin/days/create/", {}, None),
    ("delete", "admin/days/<int:pk>/delete/", None, "day"),
    ("get", "admin/badges/download/", None, None),
    ("get", "admin/program/download/", None, None),
    ("patch", "admin/accommodation/", {}, None),
    ("post", "admin/accommodation/options/", {}, None),
    ("patch", "admin/accommodation/options/<int:pk>/", {}, "option"),
    ("patch", "conference-info/edit/", {}, None),
    ("post", "hiking/admin/", {}, None),
    ("post", "hiking/stops/", {}, None),
    ("patch", "hiking/stops/<int:pk>/", {}, "stop"),
    ("post", "people/", {}, None),
    ("get", "people/<int:pk>/", None, "person"),
]


class ConferencePermissionTestCase(TestCase):
    def setUp(self):
        self.wsc = Conference.objects.create(slug=WSC)
        self.other = Conference.objects.create(slug=OTHER)

        self.superuser = User.objects.create_superuser(
            username="perm-super", email="super@example.com", password="pw"
        )
        self.member = User.objects.create_user(username="perm-member", password="pw")
        self.outsider = User.objects.create_user(
            username="perm-outsider", password="pw"
        )
        self.staff = User.objects.create_user(
            username="perm-staff", password="pw", is_staff=True
        )
        ConferenceManagers.objects.create(conference=self.wsc, user=self.member)
        ConferenceManagers.objects.create(conference=self.other, user=self.outsider)

        self.day = ConferenceDay.objects.create(
            conference=self.wsc, date=date(2026, 5, 1)
        )
        self.session = Session.objects.create(conference=self.wsc, day=self.day)
        self.talk = Talk.objects.create(conference=self.wsc, title="Unscheduled")
        self.submission = ParticipantSubmission.objects.create(
            conference=self.wsc,
            name="Submitter",
            email="submitter@example.com",
            affiliation="CTU",
            arrival_date=date(2026, 5, 1),
            departure_date=date(2026, 5, 2),
        )
        self.option = AccommodationOption.objects.create(
            conference=self.wsc, name="Hotel"
        )
        self.route = HikingRoute.objects.create(conference=self.wsc, name="Route")
        self.stop = HikingStop.objects.create(
            conference=self.wsc, route=self.route, name="Stop"
        )
        self.person = Person.objects.create(conference=self.wsc, name="Person")

        self.client = APIClient()

    def auth_client(self, user, slug=WSC):
        client = APIClient()
        token = RefreshToken.for_user(user)
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {token.access_token}")
        return client

    def concrete_tail(self, pattern, attribute):
        if attribute is None:
            return pattern
        return pattern.replace("<int:pk>", str(getattr(self, attribute).pk))

    def send(self, client, method, tail, body):
        url = api(tail)
        if method == "get":
            return client.get(url)
        return getattr(client, method)(url, body, format="json")

    def test_route_matrix_covers_the_pinned_tail_table(self):
        self.assertEqual(
            PUBLIC_TAIL_PATTERNS | {pattern for _, pattern, _, _ in ADMIN_ROUTES},
            set(EXPECTED_ROUTE_TAILS),
        )

    def test_non_members_are_forbidden_on_every_admin_route(self):
        for user in (self.outsider, self.staff):
            client = self.auth_client(user)
            for method, pattern, body, attribute in ADMIN_ROUTES:
                tail = self.concrete_tail(pattern, attribute)
                with self.subTest(user=user.username, route=tail, method=method):
                    response = self.send(client, method, tail, body)
                    self.assertEqual(response.status_code, 403)

    def test_member_is_forbidden_on_another_conference(self):
        client = self.auth_client(self.member)
        response = client.get(api("admin-panel/", slug=OTHER))
        self.assertEqual(response.status_code, 403)

    def test_member_is_not_forbidden_on_own_conference(self):
        client = self.auth_client(self.member)
        for method, pattern, body, attribute in ADMIN_ROUTES:
            tail = self.concrete_tail(pattern, attribute)
            with self.subTest(route=tail, method=method):
                response = self.send(client, method, tail, body)
                if method == "get":
                    self.assertEqual(response.status_code, 200)
                else:
                    self.assertNotEqual(response.status_code, 403)
                    self.assertLess(response.status_code, 500)

    def test_anonymous_is_rejected_on_admin_routes(self):
        for method, pattern, body, attribute in ADMIN_ROUTES:
            tail = self.concrete_tail(pattern, attribute)
            with self.subTest(route=tail, method=method):
                response = self.send(self.client, method, tail, body)
                self.assertIn(response.status_code, (401, 403))

    def test_superuser_bypasses_grants_on_every_conference(self):
        client = self.auth_client(self.superuser)
        for slug in (WSC, OTHER):
            with self.subTest(slug=slug):
                self.assertEqual(
                    client.get(api("admin-panel/", slug=slug)).status_code, 200
                )

    def test_revocation_is_immediate(self):
        client = self.auth_client(self.member)
        self.assertEqual(client.get(api("admin-panel/")).status_code, 200)

        ConferenceManagers.objects.filter(
            conference=self.wsc, user=self.member
        ).delete()

        self.assertEqual(client.get(api("admin-panel/")).status_code, 403)

    def test_public_reads_stay_public(self):
        for tail in (
            "program/",
            "participants/",
            "abstracts/",
            "talks/",
            "people/",
            "accommodation/",
            "conference-info/",
            "hiking/",
        ):
            with self.subTest(tail=tail):
                self.assertEqual(self.client.get(api(tail)).status_code, 200)

    def test_people_post_is_a_write_gate(self):
        self.assertEqual(
            self.client.post(api("people/"), {"name": "X"}, format="json").status_code,
            401,
        )
        self.assertEqual(
            self.auth_client(self.staff)
            .post(api("people/"), {"name": "X"}, format="json")
            .status_code,
            403,
        )
        self.assertNotEqual(
            self.auth_client(self.member)
            .post(api("people/"), {"name": "X"}, format="json")
            .status_code,
            403,
        )


class ConferenceManagersModelTests(TestCase):
    def setUp(self):
        self.conference = Conference.objects.create(slug="manager-model")
        self.user = User.objects.create_user(username="manager-user", password="pw")

    def test_pair_is_unique(self):
        ConferenceManagers.objects.create(conference=self.conference, user=self.user)
        with self.assertRaises(IntegrityError), transaction.atomic():
            ConferenceManagers.objects.create(
                conference=self.conference, user=self.user
            )

    def test_deleting_user_revokes_grant(self):
        ConferenceManagers.objects.create(conference=self.conference, user=self.user)
        self.user.delete()
        self.assertFalse(
            ConferenceManagers.objects.filter(conference=self.conference).exists()
        )


class AuthUserPayloadTests(ConferencePermissionTestCase):
    def test_member_payload_lists_managed_conferences(self):
        response = self.auth_client(self.member).get("/api/auth/user/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["managed_conferences"], [WSC])
        self.assertFalse(response.data["is_superuser"])

    def test_superuser_payload_has_no_managed_list(self):
        response = self.auth_client(self.superuser).get("/api/auth/user/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["managed_conferences"], [])
        self.assertTrue(response.data["is_superuser"])


class DjangoAdminLockTests(ConferencePermissionTestCase):
    def test_staff_without_superuser_cannot_reach_conference_admin(self):
        self.client.force_login(self.staff)
        for url in (
            reverse("admin:core_conference_changelist"),
            reverse("admin:core_conference_add"),
            reverse("admin:core_participantsubmission_changelist"),
            reverse("admin:core_participantsubmission_add"),
            reverse("admin:core_participantsubmission_import"),
        ):
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 403)

    def test_staff_without_superuser_cannot_reach_any_core_admin(self):
        self.client.force_login(self.staff)
        for model in django_admin.site._registry:
            if model._meta.app_label != "core":
                continue
            url = reverse(
                f"admin:{model._meta.app_label}_{model._meta.model_name}_changelist"
            )
            with self.subTest(model=model._meta.object_name):
                self.assertEqual(self.client.get(url).status_code, 403)

    def test_superuser_reaches_conference_admin(self):
        self.client.force_login(self.superuser)
        for url in (
            reverse("admin:core_conference_changelist"),
            reverse("admin:core_conference_add"),
            reverse("admin:core_participantsubmission_changelist"),
            reverse("admin:core_participantsubmission_add"),
            reverse("admin:core_participantsubmission_import"),
        ):
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 200)
