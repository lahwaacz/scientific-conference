"""Tests for public read endpoints and the two PDF downloads."""

import shutil
import subprocess
from datetime import date, time

import pytest
from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from .models import (
    Abstract,
    ConferenceDay,
    ConferenceInfo,
    HikingRoute,
    HikingStop,
    Participant,
    ParticipantSubmission,
    Session,
    Talk,
)


def pdf_text(content):
    proc = subprocess.run(
        ["pdftotext", "-", "-"],
        input=content,
        capture_output=True,
        check=True,
    )
    return proc.stdout.decode()


class TestPublicLists(TestCase):
    def setUp(self):
        self.client = APIClient()

    def _day_with_content(self):
        day = ConferenceDay.objects.create(date=date(2026, 9, 10))
        session = Session.objects.create(day=day, chair="Chair")
        participant = Participant.objects.create(name="Bea Speaker")
        Talk.objects.create(
            title="Zeta Talk",
            talk_type="talk",
            is_scheduled=True,
            day=day,
            session=session,
            participant=participant,
            start_time=time(10, 0),
            end_time=time(10, 20),
        )
        return day

    def test_program_returns_days_with_timeline(self):
        day = self._day_with_content()

        response = self.client.get("/api/program/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["id"], day.id)
        timeline = response.data[0]["timeline"]
        self.assertEqual(len(timeline), 1)
        self.assertEqual(timeline[0]["type"], "session")

    def test_program_days_are_date_ordered(self):
        ConferenceDay.objects.create(date=date(2026, 9, 12))
        ConferenceDay.objects.create(date=date(2026, 9, 10))

        response = self.client.get("/api/program/")

        self.assertEqual(response.status_code, 200)
        dates = [d["date"] for d in response.data]
        self.assertEqual(dates, sorted(dates))

    def test_participants_list_and_public_post(self):
        Participant.objects.create(name="Zed")
        Participant.objects.create(name="Ann")

        response = self.client.get("/api/participants/")

        self.assertEqual(response.status_code, 200)
        names = [p["name"] for p in response.data]
        self.assertEqual(names, ["Ann", "Zed"])

        # Public writes are deliberate (backend/AGENTS.md); may be
        # revisited for security later, but do not restrict without a
        # fresh admin decision.
        response = self.client.post(
            "/api/participants/", {"name": "Newcomer"}, format="json"
        )
        self.assertEqual(response.status_code, 201)

    def test_abstracts_list_and_public_post(self):
        participant = Participant.objects.create(name="Author")
        Abstract.objects.create(title="Beta", participant=participant)

        response = self.client.get("/api/abstracts/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)

        # Deliberate public write path, same as /api/participants/.
        response = self.client.post(
            "/api/abstracts/",
            {"title": "Gamma", "authors_string": "A. Uthor"},
            format="json",
        )
        self.assertEqual(response.status_code, 201)

    def test_conference_info_autocreates_single_row(self):
        self.assertEqual(ConferenceInfo.objects.count(), 0)

        response = self.client.get("/api/conference-info/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(ConferenceInfo.objects.count(), 1)

    def test_hiking_lists_routes_with_ordered_stops(self):
        route = HikingRoute.objects.create(name="Path")
        HikingStop.objects.create(route=route, name="Second", order=2)
        HikingStop.objects.create(route=route, name="First", order=1)

        response = self.client.get("/api/hiking/")

        self.assertEqual(response.status_code, 200)
        stops = response.data[0]["stops"]
        self.assertEqual([s["name"] for s in stops], ["First", "Second"])

    def test_bad_pk_returns_404(self):
        response = self.client.get("/api/participants/999/")
        self.assertEqual(response.status_code, 404)
        response = self.client.get("/api/abstracts/999/")
        self.assertEqual(response.status_code, 404)
        response = self.client.get("/api/talks/999/")
        self.assertEqual(response.status_code, 404)


class TestPdfDownloads(TestCase):
    def _client(self, is_staff):
        user = User.objects.create_user(
            username=f"u-{is_staff}", password="pw", is_staff=is_staff
        )
        token = RefreshToken.for_user(user)
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {token.access_token}")
        return client

    def test_program_pdf_gates(self):
        self.assertEqual(
            APIClient().get("/api/admin/program/download/").status_code, 403
        )
        self.assertEqual(
            self._client(is_staff=False)
            .get("/api/admin/program/download/")
            .status_code,
            403,
        )
        staff = self._client(is_staff=True).get("/api/admin/program/download/")
        self.assertEqual(staff.status_code, 200)
        self.assertEqual(staff.headers["Content-Type"], "application/pdf")
        self.assertTrue(staff.content.startswith(b"%PDF"))

    def test_badges_pdf_gates(self):
        self.assertEqual(
            APIClient().get("/api/admin/badges/download/").status_code, 403
        )
        self.assertEqual(
            self._client(is_staff=False).get("/api/admin/badges/download/").status_code,
            403,
        )
        staff = self._client(is_staff=True).get("/api/admin/badges/download/")
        self.assertEqual(staff.status_code, 200)
        self.assertEqual(staff.headers["Content-Type"], "application/pdf")
        self.assertTrue(staff.content.startswith(b"%PDF"))

    @pytest.mark.skipif(
        shutil.which("pdftotext") is None, reason="pdftotext not available"
    )
    def test_badges_pdf_contains_only_approved_submissions(self):
        ParticipantSubmission.objects.create(
            name="Approved Person",
            email="a@x.cz",
            affiliation="CTU",
            status="approved",
            arrival_date=date(2026, 9, 10),
            departure_date=date(2026, 9, 11),
        )
        ParticipantSubmission.objects.create(
            name="Pending Person",
            email="p@x.cz",
            affiliation="CTU",
            status="pending",
            arrival_date=date(2026, 9, 10),
            departure_date=date(2026, 9, 11),
        )

        response = self._client(is_staff=True).get("/api/admin/badges/download/")

        text = pdf_text(response.content)
        self.assertIn("Approved Person", text)
        self.assertNotIn("Pending Person", text)
