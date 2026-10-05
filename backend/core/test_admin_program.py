"""Tests for admin program-structure endpoints (days, sessions, talk guards)."""

from datetime import date

from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from .conftest import api
from .models import Abstract, Conference, ConferenceDay, Participant, Session, Talk


def wsc_conference():
    return Conference.objects.get_or_create(slug="wsc2026-test")[0]


class AdminTestCase(TestCase):
    def setUp(self):
        admin = User.objects.create_user(username="admin", password="pw", is_staff=True)
        token = RefreshToken.for_user(admin)
        self.client = APIClient()
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token.access_token}")
        self.conference = wsc_conference()
        self.day = ConferenceDay.objects.create(
            conference=self.conference, date=date(2026, 9, 10)
        )

    def make_talk(self, **overrides):
        data = {
            "conference": self.conference,
            "title": "Some Talk",
            "talk_type": "talk",
            "is_scheduled": False,
        }
        data.update(overrides)
        return Talk.objects.create(**data)


class TestDayAdmin(AdminTestCase):
    def test_create_day(self):
        response = self.client.post(
            api("admin/days/create/"), {"date": "2026-09-11"}, format="json"
        )
        self.assertEqual(response.status_code, 201)
        self.assertTrue(ConferenceDay.objects.filter(date="2026-09-11").exists())

    def test_delete_day_cascades_sessions_talks_and_abstracts(self):
        session = Session.objects.create(conference=self.conference, day=self.day)
        participant = Participant.objects.create(conference=self.conference, name="P")
        abstract = Abstract.objects.create(
            conference=self.conference, title="A", participant=participant
        )
        Talk.objects.create(
            conference=self.conference,
            title="Nested",
            talk_type="talk",
            is_scheduled=True,
            day=self.day,
            session=session,
            participant=participant,
            abstract=abstract,
        )

        response = self.client.delete(api(f"admin/days/{self.day.id}/delete/"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(ConferenceDay.objects.count(), 0)
        self.assertEqual(Session.objects.count(), 0)
        self.assertEqual(Talk.objects.count(), 0)
        # Talk.abstract is a CASCADE FK from Talk to Abstract, so deleting
        # a day (and its talks) leaves the abstract behind. Deliberate:
        # the admin keeps orphaned abstracts (backend/AGENTS.md); do not
        # add a cascade here without an admin decision.
        self.assertEqual(Abstract.objects.count(), 1)
        self.assertEqual(Participant.objects.count(), 1)


class TestSessionAdmin(AdminTestCase):
    def test_create_session_requires_day(self):
        response = self.client.post(api("admin/sessions/create/"), {}, format="json")
        self.assertEqual(response.status_code, 400)

    def test_create_session(self):
        response = self.client.post(
            api("admin/sessions/create/"),
            {"day": self.day.id, "chair": "Prof. X"},
            format="json",
        )
        self.assertEqual(response.status_code, 201)

    def test_list_filters_by_day(self):
        other_day = ConferenceDay.objects.create(
            conference=self.conference, date=date(2026, 9, 11)
        )
        Session.objects.create(conference=self.conference, day=self.day, chair="A")
        Session.objects.create(conference=self.conference, day=other_day, chair="B")

        response = self.client.get(api(f"admin/sessions/?day={self.day.id}"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["chair"], "A")

    def test_update_time(self):
        session = Session.objects.create(conference=self.conference, day=self.day)
        response = self.client.patch(
            api(f"admin/sessions/{session.id}/update-time/"),
            {"start_time": "09:00", "end_time": "10:00"},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        session.refresh_from_db()
        self.assertEqual(str(session.start_time), "09:00:00")

    def test_update_session_chair(self):
        session = Session.objects.create(
            conference=self.conference, day=self.day, chair="Old"
        )

        response = self.client.patch(
            api(f"admin/sessions/{session.id}/"), {"chair": "New"}, format="json"
        )

        self.assertEqual(response.status_code, 200)
        session.refresh_from_db()
        self.assertEqual(session.chair, "New")

    def test_delete_session_detaches_talks(self):
        session = Session.objects.create(conference=self.conference, day=self.day)
        talk = self.make_talk(session=session, day=self.day, is_scheduled=True)

        response = self.client.delete(api(f"admin/sessions/{session.id}/delete/"))

        self.assertEqual(response.status_code, 204)
        self.assertEqual(Session.objects.count(), 0)
        talk.refresh_from_db()
        self.assertIsNone(talk.session)


class TestTalkAdminGuards(AdminTestCase):
    def test_unscheduled_list_contains_only_unscheduled_talks(self):
        self.make_talk(title="Waiting")
        self.make_talk(
            title="Placed",
            day=self.day,
            is_scheduled=True,
        )

        response = self.client.get(api("admin/talks/unscheduled/"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["title"], "Waiting")

    def test_delete_unscheduled_talk(self):
        talk = self.make_talk()
        response = self.client.delete(api(f"admin/talks/{talk.id}/delete/"))
        self.assertEqual(response.status_code, 204)
        self.assertEqual(Talk.objects.count(), 0)

    def test_delete_scheduled_talk_is_rejected(self):
        talk = self.make_talk(day=self.day, is_scheduled=True)
        response = self.client.delete(api(f"admin/talks/{talk.id}/delete/"))
        self.assertEqual(response.status_code, 400)
        self.assertEqual(Talk.objects.count(), 1)

    def test_delete_break_succeeds_even_when_scheduled(self):
        brk = self.make_talk(
            title="Break", talk_type="break", day=self.day, is_scheduled=True
        )
        response = self.client.delete(api(f"admin/talks/{brk.id}/delete/"))
        self.assertEqual(response.status_code, 204)
        self.assertEqual(Talk.objects.count(), 0)
