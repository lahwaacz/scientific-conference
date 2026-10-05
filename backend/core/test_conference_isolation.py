"""Cross-conference isolation tests for the whole scoped API.

Two conferences (A / B) carry fully distinct data sets, each tagged with a
unique marker token. Every assertion reduces to "under A's slug only A's
marker is visible" so any scoping regression fails loudly.
"""

import shutil
import subprocess
from datetime import date, time
from types import SimpleNamespace

import pytest
from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from . import urls as core_urls
from .conftest import api
from .models import (
    Abstract,
    AccommodationInfo,
    AccommodationOption,
    Conference,
    ConferenceDay,
    ConferenceInfo,
    HikingRoute,
    HikingStop,
    Organizer,
    OrganizingCommittee,
    Participant,
    ParticipantSubmission,
    Session,
    Talk,
)

SLUG_A = "wsc2026-test"
SLUG_B = "wsc2027-test"
MARK_A = "MarkAlphaUq"
MARK_B = "MarkBetaUq"
UNKNOWN = "zz-no-such-conference"


def alpha_conference():
    conference = Conference.objects.get_or_create(slug=SLUG_A)[0]
    ConferenceInfo.objects.get_or_create(
        conference=conference,
        defaults={
            "title": f"Alpha {MARK_A} Conference",
            "date_start": date(2026, 9, 1),
            "date_end": date(2026, 9, 3),
            "location": f"City {MARK_A}",
        },
    )
    return conference


def beta_conference():
    conference = Conference.objects.get_or_create(slug=SLUG_B)[0]
    ConferenceInfo.objects.get_or_create(
        conference=conference,
        defaults={
            "title": f"Beta {MARK_B} Conference",
            "date_start": date(2027, 3, 1),
            "date_end": date(2027, 3, 3),
            "location": f"City {MARK_B}",
        },
    )
    return conference


def make_conference_data(conference, mark):
    """A full distinct data set for one conference, tagged with `mark`."""
    day = ConferenceDay.objects.create(conference=conference, date=date(2026, 9, 10))
    extra_day = ConferenceDay.objects.create(
        conference=conference, date=date(2026, 9, 11)
    )
    session = Session.objects.create(
        conference=conference, day=day, chair=f"Chair {mark}"
    )
    participant = Participant.objects.create(
        conference=conference,
        name=f"Speaker {mark}",
        affiliation=f"Affil {mark}",
        email=f"speaker.{mark.lower()}@example.com",
    )
    abstract = Abstract.objects.create(
        conference=conference,
        title=f"Abstract {mark}",
        text=f"Text {mark}",
        authors=f"Speaker {mark}",
        participant=participant,
    )
    talk = Talk.objects.create(
        conference=conference,
        title=f"Talk {mark}",
        talk_type="talk",
        participant=participant,
        abstract=abstract,
        day=day,
        session=session,
        start_time=time(10, 0),
        end_time=time(10, 20),
        is_scheduled=True,
    )
    unscheduled_talk = Talk.objects.create(
        conference=conference,
        title=f"Pending {mark}",
        talk_type="talk",
        is_scheduled=False,
    )
    organizer = Organizer.objects.create(conference=conference, name=f"Org {mark}")
    committee = OrganizingCommittee.objects.create(
        conference=conference, name=f"Committee {mark}"
    )
    acco_info = AccommodationInfo.objects.create(
        conference=conference, description=f"Stay {mark}"
    )
    acco_option = AccommodationOption.objects.create(
        conference=conference, info=acco_info, name=f"Hotel {mark}", order=1
    )
    route = HikingRoute.objects.create(conference=conference, name=f"Route {mark}")
    stop = HikingStop.objects.create(
        conference=conference, route=route, name=f"Stop {mark}", order=1
    )
    submission = ParticipantSubmission.objects.create(
        conference=conference,
        name=f"Speaker {mark}",
        email=f"speaker.{mark.lower()}@example.com",
        affiliation=f"Affil {mark}",
        abstract_title=f"Abstract {mark}",
        abstract_text=f"Text {mark}",
        arrival_date=date(2026, 9, 9),
        departure_date=date(2026, 9, 12),
        status="approved",
    )
    return SimpleNamespace(
        day=day,
        extra_day=extra_day,
        session=session,
        participant=participant,
        abstract=abstract,
        talk=talk,
        unscheduled_talk=unscheduled_talk,
        organizer=organizer,
        committee=committee,
        acco_info=acco_info,
        acco_option=acco_option,
        route=route,
        stop=stop,
        submission=submission,
    )


def staff_client(username="admin"):
    user = User.objects.create_user(username=username, password="pw", is_staff=True)
    token = RefreshToken.for_user(user)
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {token.access_token}")
    return client


# Route-table lock: every tail routed through the slug include in
# backend/urls.py. Adding/renaming a route in core/urls.py without touching
# this suite fails loudly here instead of shipping an untested endpoint.
EXPECTED_ROUTE_TAILS = frozenset(
    {
        "program/",
        "participants/",
        "participants/<int:pk>/",
        "abstracts/",
        "abstracts/<int:pk>/",
        "talks/",
        "talks/<int:pk>/",
        "organizers/",
        "organizers/<int:pk>/",
        "committees/",
        "committees/<int:pk>/",
        "accommodation/",
        "admin/accommodation/",
        "admin/accommodation/options/",
        "admin/accommodation/options/<int:pk>/",
        "conference-info/",
        "conference-info/edit/",
        "submit/",
        "admin-panel/",
        "admin/submissions/",
        "admin/submissions/<int:pk>/",
        "admin/submissions/<int:pk>/publish/",
        "hiking/",
        "hiking/admin/",
        "hiking/stops/",
        "hiking/stops/<int:pk>/",
        "admin/talks/unscheduled/",
        "admin/talks/<int:pk>/schedule/",
        "admin/talks/<int:pk>/delete/",
        "admin/talks/create-break/",
        "admin/sessions/create/",
        "admin/sessions/",
        "admin/sessions/<int:pk>/",
        "admin/sessions/<int:pk>/delete/",
        "admin/sessions/<int:pk>/update-time/",
        "admin/days/create/",
        "admin/days/<int:pk>/delete/",
        "admin/badges/download/",
        "admin/program/download/",
    }
)


class TestRouteTableLock(TestCase):
    def test_core_url_table_matches_pinned_tails(self):
        routed = frozenset(str(pattern.pattern) for pattern in core_urls.urlpatterns)
        self.assertEqual(routed, EXPECTED_ROUTE_TAILS)


class ConferencePairTestCase(TestCase):
    def setUp(self):
        self.client = staff_client()
        self.conf_a = alpha_conference()
        self.conf_b = beta_conference()
        self.a = make_conference_data(self.conf_a, MARK_A)
        self.b = make_conference_data(self.conf_b, MARK_B)


class TestGetRouteMatrix(ConferencePairTestCase):
    def json_routes_for(self, data):
        return [
            "program/",
            "participants/",
            f"participants/{data.participant.pk}/",
            "abstracts/",
            f"abstracts/{data.abstract.pk}/",
            "talks/",
            f"talks/{data.talk.pk}/",
            "organizers/",
            f"organizers/{data.organizer.pk}/",
            "committees/",
            f"committees/{data.committee.pk}/",
            "accommodation/",
            "conference-info/",
            "hiking/",
            "admin/submissions/",
            "admin/talks/unscheduled/",
            "admin/sessions/",
        ]

    def test_json_gets_return_only_own_conference_data(self):
        for slug, data, own, foreign in (
            (SLUG_A, self.a, MARK_A, MARK_B),
            (SLUG_B, self.b, MARK_B, MARK_A),
        ):
            for tail in self.json_routes_for(data):
                with self.subTest(slug=slug, route=tail):
                    response = self.client.get(api(tail, slug=slug))
                    self.assertEqual(response.status_code, 200)
                    body = response.content.decode()
                    self.assertIn(own, body)
                    self.assertNotIn(foreign, body)

    def test_admin_panel_200_both_conferences(self):
        for slug in (SLUG_A, SLUG_B):
            with self.subTest(slug=slug):
                response = self.client.get(api("admin-panel/", slug=slug))
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.json()["message"], "Welcome to admin panel")

    def test_pdf_downloads_200_with_other_conference_data_present(self):
        # Both conferences hold approved submissions/days: the scoped filters
        # must keep generation clean (no 500, correct content type) per slug.
        for slug in (SLUG_A, SLUG_B):
            for tail in ("admin/badges/download/", "admin/program/download/"):
                with self.subTest(slug=slug, route=tail):
                    response = self.client.get(api(tail, slug=slug))
                    self.assertEqual(response.status_code, 200)
                    self.assertEqual(
                        response.headers["Content-Type"], "application/pdf"
                    )
                    self.assertTrue(response.content.startswith(b"%PDF"))


# method, tail (pk = 1 placeholder), JSON body
UNKNOWN_SLUG_MATRIX = [
    ("get", "program/", None),
    ("get", "participants/", None),
    ("post", "participants/", {"name": "X"}),
    ("get", "participants/1/", None),
    ("get", "abstracts/", None),
    ("post", "abstracts/", {"title": "X", "authors_string": "Y"}),
    ("get", "abstracts/1/", None),
    ("get", "talks/", None),
    ("get", "talks/1/", None),
    ("get", "organizers/", None),
    ("post", "organizers/", {"name": "X"}),
    ("get", "organizers/1/", None),
    ("patch", "organizers/1/", {"name": "X"}),
    ("delete", "organizers/1/", None),
    ("get", "committees/", None),
    ("post", "committees/", {"name": "X"}),
    ("get", "committees/1/", None),
    ("patch", "committees/1/", {"name": "X"}),
    ("delete", "committees/1/", None),
    ("get", "accommodation/", None),
    ("patch", "admin/accommodation/", {"description": "x"}),
    ("post", "admin/accommodation/options/", {"name": "x", "order": 1}),
    ("patch", "admin/accommodation/options/1/", {"name": "x"}),
    ("delete", "admin/accommodation/options/1/", None),
    ("get", "conference-info/", None),
    ("patch", "conference-info/edit/", {"grant_text": "x"}),
    (
        "post",
        "submit/",
        {
            "name": "X",
            "email": "x@example.com",
            "affiliation": "Y",
            "arrival_date": "2026-09-10",
            "departure_date": "2026-09-11",
        },
    ),
    ("get", "admin-panel/", None),
    ("get", "admin/submissions/", None),
    ("get", "admin/submissions/1/", None),
    ("patch", "admin/submissions/1/", {"name": "X"}),
    ("delete", "admin/submissions/1/", None),
    ("post", "admin/submissions/1/publish/", None),
    ("get", "hiking/", None),
    ("post", "hiking/admin/", {"name": "X"}),
    ("patch", "hiking/admin/", {"id": 1}),
    ("delete", "hiking/admin/", {"id": 1}),
    ("post", "hiking/stops/", {"route": 1, "name": "X"}),
    ("patch", "hiking/stops/1/", {"name": "X"}),
    ("delete", "hiking/stops/1/", None),
    ("get", "admin/talks/unscheduled/", None),
    ("patch", "admin/talks/1/schedule/", {"title": "X"}),
    ("delete", "admin/talks/1/delete/", None),
    (
        "post",
        "admin/talks/create-break/",
        {"day": 1, "start_time": "10:00", "end_time": "10:15"},
    ),
    ("post", "admin/sessions/create/", {"day": 1, "chair": "X"}),
    ("get", "admin/sessions/", None),
    ("patch", "admin/sessions/1/", {"chair": "X"}),
    ("delete", "admin/sessions/1/delete/", None),
    ("patch", "admin/sessions/1/update-time/", {"start_time": "10:00"}),
    ("post", "admin/days/create/", {"date": "2026-09-10"}),
    ("delete", "admin/days/1/delete/", None),
    ("get", "admin/badges/download/", None),
    ("get", "admin/program/download/", None),
]


class TestUnknownSlug(TestCase):
    def setUp(self):
        self.client = staff_client()

    def test_every_scoped_route_404s_for_unknown_slug(self):
        for method, tail, body in UNKNOWN_SLUG_MATRIX:
            with self.subTest(method=method, route=tail):
                request = getattr(self.client, method)
                kwargs = {"format": "json"} if body is not None else {}
                response = request(api(tail, slug=UNKNOWN), body, **kwargs)
                self.assertEqual(response.status_code, 404)


class TestCrossConferencePkAccess(ConferencePairTestCase):
    def test_public_detail_pks_under_wrong_slug_404(self):
        pairs = [
            f"participants/{self.a.participant.pk}/",
            f"abstracts/{self.a.abstract.pk}/",
            f"talks/{self.a.talk.pk}/",
        ]
        for tail in pairs:
            with self.subTest(route=tail):
                self.assertEqual(
                    self.client.get(api(tail, slug=SLUG_B)).status_code, 404
                )

    def test_people_detail_pks_under_wrong_slug_404(self):
        for tail in (
            f"organizers/{self.a.organizer.pk}/",
            f"committees/{self.a.committee.pk}/",
        ):
            with self.subTest(route=tail):
                self.assertEqual(
                    self.client.get(api(tail, slug=SLUG_B)).status_code, 404
                )

    def test_submission_detail_and_publish_under_wrong_slug_404(self):
        sub_pk = self.a.submission.pk
        self.assertEqual(
            self.client.get(
                api(f"admin/submissions/{sub_pk}/", slug=SLUG_B)
            ).status_code,
            404,
        )
        response = self.client.post(
            api(f"admin/submissions/{sub_pk}/publish/", slug=SLUG_B)
        )
        self.assertEqual(response.status_code, 404)
        self.a.submission.refresh_from_db()
        self.assertEqual(self.a.submission.status, "approved")

    def test_moved_session_routes_under_wrong_slug_404(self):
        pk = self.a.session.pk
        response = self.client.patch(
            api(f"admin/sessions/{pk}/", slug=SLUG_B),
            {"chair": "Hijack"},
            format="json",
        )
        self.assertEqual(response.status_code, 404)
        response = self.client.delete(api(f"admin/sessions/{pk}/delete/", slug=SLUG_B))
        self.assertEqual(response.status_code, 404)
        self.a.session.refresh_from_db()
        self.assertEqual(self.a.session.chair, f"Chair {MARK_A}")

    def test_session_update_time_under_wrong_slug_404(self):
        response = self.client.patch(
            api(f"admin/sessions/{self.a.session.pk}/update-time/", slug=SLUG_B),
            {"start_time": "11:00"},
            format="json",
        )
        self.assertEqual(response.status_code, 404)

    def test_talk_schedule_and_delete_under_wrong_slug_404(self):
        pk = self.a.talk.pk
        response = self.client.patch(
            api(f"admin/talks/{pk}/schedule/", slug=SLUG_B),
            {"title": "Hijack"},
            format="json",
        )
        self.assertEqual(response.status_code, 404)
        response = self.client.delete(api(f"admin/talks/{pk}/delete/", slug=SLUG_B))
        self.assertEqual(response.status_code, 404)

    def test_day_delete_under_wrong_slug_404(self):
        day_pk = self.a.day.pk
        response = self.client.delete(api(f"admin/days/{day_pk}/delete/", slug=SLUG_B))
        self.assertEqual(response.status_code, 404)
        self.assertTrue(ConferenceDay.objects.filter(pk=day_pk).exists())

    def test_hiking_route_edit_under_wrong_slug_404(self):
        route_id = self.a.route.pk
        response = self.client.patch(
            api("hiking/admin/", slug=SLUG_B), {"id": route_id}, format="json"
        )
        self.assertEqual(response.status_code, 404)
        response = self.client.delete(
            api("hiking/admin/", slug=SLUG_B), {"id": route_id}, format="json"
        )
        self.assertEqual(response.status_code, 404)

    def test_accommodation_option_cross_pk_returns_pinned_500(self):
        # Deliberate: unguarded objects.get(pk) raises -> 500 (backend
        # AGENTS.md anti-pattern). Cross-conference pks behave like unknowns.
        self.client.raise_request_exception = False
        option_pk = self.a.acco_option.pk
        response = self.client.patch(
            api(f"admin/accommodation/options/{option_pk}/", slug=SLUG_B),
            {"name": "Hijack"},
            format="json",
        )
        self.assertEqual(response.status_code, 500)
        response = self.client.delete(
            api(f"admin/accommodation/options/{option_pk}/", slug=SLUG_B)
        )
        self.assertEqual(response.status_code, 500)

    def test_hiking_stop_cross_pk_returns_pinned_500(self):
        self.client.raise_request_exception = False
        stop_pk = self.a.stop.pk
        response = self.client.patch(
            api(f"hiking/stops/{stop_pk}/", slug=SLUG_B),
            {"name": "Hijack"},
            format="json",
        )
        self.assertEqual(response.status_code, 500)
        response = self.client.delete(api(f"hiking/stops/{stop_pk}/", slug=SLUG_B))
        self.assertEqual(response.status_code, 500)


class TestCrossConferenceBodies(ConferencePairTestCase):
    def test_talk_schedule_rejects_other_conference_session(self):
        response = self.client.patch(
            api(f"admin/talks/{self.a.talk.pk}/schedule/", slug=SLUG_A),
            {"session": self.b.session.pk},
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("session", response.json())
        self.a.talk.refresh_from_db()
        self.assertEqual(self.a.talk.session, self.a.session)

    def test_talk_schedule_rejects_other_conference_day(self):
        response = self.client.patch(
            api(f"admin/talks/{self.a.talk.pk}/schedule/", slug=SLUG_A),
            {"day": self.b.day.pk},
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("day", response.json())
        self.a.talk.refresh_from_db()
        self.assertEqual(self.a.talk.day, self.a.day)

    def test_talk_schedule_accepts_own_conference_session(self):
        response = self.client.patch(
            api(f"admin/talks/{self.a.talk.pk}/schedule/", slug=SLUG_A),
            {"session": self.a.session.pk},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.a.talk.refresh_from_db()
        self.assertEqual(self.a.talk.session, self.a.session)

    def test_session_create_rejects_other_conference_day(self):
        response = self.client.post(
            api("admin/sessions/create/", slug=SLUG_A),
            {"day": self.b.day.pk, "chair": "Hijack"},
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(Session.objects.count(), 2)

    def test_session_create_accepts_own_conference_day(self):
        response = self.client.post(
            api("admin/sessions/create/", slug=SLUG_A),
            {"day": self.a.extra_day.pk, "chair": "New Chair"},
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        session = Session.objects.get(chair="New Chair")
        self.assertEqual(session.conference, self.conf_a)

    def test_break_create_rejects_other_conference_day(self):
        response = self.client.post(
            api("admin/talks/create-break/", slug=SLUG_A),
            {
                "day": self.b.day.pk,
                "start_time": "12:00",
                "end_time": "12:30",
                "title": "Hijack Break",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertFalse(Talk.objects.filter(title="Hijack Break").exists())

    def test_break_create_accepts_own_conference_day(self):
        response = self.client.post(
            api("admin/talks/create-break/", slug=SLUG_A),
            {"day": self.a.day.pk, "start_time": "12:00", "end_time": "12:30"},
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        breakout = Talk.objects.get(talk_type="break")
        self.assertEqual(breakout.conference, self.conf_a)
        self.assertEqual(breakout.day, self.a.day)

    def test_hiking_stop_create_rejects_other_conference_route(self):
        response = self.client.post(
            api("hiking/stops/", slug=SLUG_A),
            {"route": self.b.route.pk, "name": "Hijack Stop", "order": 1},
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("route", response.json())
        self.assertFalse(
            HikingStop.objects.filter(name="Hijack Stop").exists(),
        )

    def test_hiking_stop_create_accepts_own_conference_route(self):
        response = self.client.post(
            api("hiking/stops/", slug=SLUG_A),
            {"route": self.a.route.pk, "name": "Own Stop", "order": 1},
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        stop = HikingStop.objects.get(name="Own Stop")
        self.assertEqual(stop.conference, self.conf_a)
        self.assertEqual(stop.route, self.a.route)


class TestSessionDayNarrowing(ConferencePairTestCase):
    # Leak fix: SessionSerializer.day used to accept ANY ConferenceDay pk,
    # silently relinking a session across conferences via update-time.

    def test_update_time_rejects_other_conference_day(self):
        response = self.client.patch(
            api(f"admin/sessions/{self.a.session.pk}/update-time/", slug=SLUG_A),
            {"day": self.b.day.pk},
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("day", response.json())
        self.a.session.refresh_from_db()
        self.assertEqual(self.a.session.day, self.a.day)

    def test_update_time_accepts_own_conference_day(self):
        response = self.client.patch(
            api(f"admin/sessions/{self.a.session.pk}/update-time/", slug=SLUG_A),
            {"day": self.a.extra_day.pk},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.a.session.refresh_from_db()
        self.assertEqual(self.a.session.day, self.a.extra_day)

    def test_update_time_still_patches_times(self):
        response = self.client.patch(
            api(f"admin/sessions/{self.a.session.pk}/update-time/", slug=SLUG_A),
            {"start_time": "09:00", "end_time": "12:00"},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.a.session.refresh_from_db()
        self.assertEqual(self.a.session.start_time, time(9, 0))
        self.assertEqual(self.a.session.end_time, time(12, 0))


def pdf_text(content):
    proc = subprocess.run(
        ["pdftotext", "-", "-"],
        input=content,
        capture_output=True,
        check=True,
    )
    return proc.stdout.decode()


@pytest.mark.skipif(shutil.which("pdftotext") is None, reason="pdftotext missing")
class TestPdfContentIsolation(ConferencePairTestCase):
    def test_badges_pdf_contains_only_own_conference(self):
        response = self.client.get(api("admin/badges/download/", slug=SLUG_A))
        self.assertEqual(response.status_code, 200)
        text = pdf_text(response.content)
        self.assertIn(MARK_A, text)
        self.assertNotIn(MARK_B, text)

    def test_program_pdf_contains_only_own_conference(self):
        response = self.client.get(api("admin/program/download/", slug=SLUG_A))
        self.assertEqual(response.status_code, 200)
        text = pdf_text(response.content)
        self.assertIn(MARK_A, text)
        self.assertNotIn(MARK_B, text)
