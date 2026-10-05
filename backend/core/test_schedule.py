"""Tests for the admin talk scheduling endpoints."""

from datetime import date, time

from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from .conftest import api
from .models import Conference, ConferenceDay, Talk

SCHEDULE_URL = api("admin/talks/{}/schedule/")
BREAK_URL = api("admin/talks/create-break/")


def wsc_conference():
    return Conference.objects.get_or_create(slug="wsc2026-test")[0]


class TestTalkScheduleEndpoint(TestCase):
    def setUp(self):
        admin = User.objects.create_user(username="admin", password="pw", is_staff=True)
        token = RefreshToken.for_user(admin)
        self.client = APIClient()
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token.access_token}")
        conference = wsc_conference()
        self.day = ConferenceDay.objects.create(
            conference=conference, date=date(2026, 9, 10)
        )
        self.talk = Talk.objects.create(
            conference=conference,
            title="Test Talk",
            talk_type="talk",
            is_scheduled=False,
        )

    def patch(self, talk, **fields):
        return self.client.patch(SCHEDULE_URL.format(talk.id), fields, format="json")

    def test_full_schedule_marks_talk_scheduled(self):
        response = self.patch(
            self.talk,
            day=self.day.id,
            start_time="10:00",
            end_time="10:20",
        )
        self.assertEqual(response.status_code, 200)
        self.talk.refresh_from_db()
        self.assertTrue(self.talk.is_scheduled)
        self.assertEqual(self.talk.day, self.day)

    def test_missing_time_marks_talk_unscheduled(self):
        response = self.patch(self.talk, day=self.day.id, start_time="10:00")
        self.assertEqual(response.status_code, 200)
        self.talk.refresh_from_db()
        self.assertFalse(self.talk.is_scheduled)

    def test_missing_day_marks_talk_unscheduled(self):
        response = self.patch(self.talk, start_time="10:00", end_time="10:20")
        self.assertEqual(response.status_code, 200)
        self.talk.refresh_from_db()
        self.assertFalse(self.talk.is_scheduled)

    def test_partial_fields_merge_with_saved_state(self):
        self.talk.start_time = time(10, 0)
        self.talk.end_time = time(10, 20)
        self.talk.save()

        response = self.patch(self.talk, day=self.day.id)
        self.assertEqual(response.status_code, 200)
        self.talk.refresh_from_db()
        self.assertTrue(self.talk.is_scheduled)

    def test_invalid_payload_returns_400(self):
        response = self.patch(self.talk, day="not-a-number")
        self.assertEqual(response.status_code, 400)

    def test_anonymous_rejected(self):
        self.client.credentials()
        response = self.patch(
            self.talk,
            day=self.day.id,
            start_time="10:00",
            end_time="10:20",
        )
        self.assertEqual(response.status_code, 401)


class TestBreakCreateEndpoint(TestCase):
    def setUp(self):
        admin = User.objects.create_user(username="admin", password="pw", is_staff=True)
        token = RefreshToken.for_user(admin)
        self.client = APIClient()
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token.access_token}")
        self.day = ConferenceDay.objects.create(
            conference=wsc_conference(), date=date(2026, 9, 10)
        )

    def test_create_break_marks_it_scheduled(self):
        response = self.client.post(
            BREAK_URL,
            {
                "day": self.day.id,
                "start_time": "12:00",
                "end_time": "13:00",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        brk = Talk.objects.get(talk_type="break")
        self.assertTrue(brk.is_scheduled)
        self.assertEqual(brk.day, self.day)

    def test_missing_day_returns_400(self):
        response = self.client.post(
            BREAK_URL,
            {"start_time": "12:00", "end_time": "13:00"},
            format="json",
        )
        self.assertEqual(response.status_code, 400)

    def test_missing_times_returns_400(self):
        response = self.client.post(BREAK_URL, {"day": self.day.id}, format="json")
        self.assertEqual(response.status_code, 400)

    def test_anonymous_rejected(self):
        self.client.credentials()
        response = self.client.post(BREAK_URL, {}, format="json")
        self.assertEqual(response.status_code, 401)
