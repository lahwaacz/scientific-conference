"""Tests for the program timeline serialization."""

from datetime import date, time

from django.test import TestCase

from .models import ConferenceDay, Session, Talk
from .serializers import ConferenceDaySerializer


class TestTimelineSerializer(TestCase):
    def setUp(self):
        self.day = ConferenceDay.objects.create(date=date(2026, 9, 10))

    def timeline(self):
        return ConferenceDaySerializer(self.day).data["timeline"]

    def test_session_bounds_derived_from_first_and_last_talk(self):
        session = Session.objects.create(day=self.day, chair="Chair")
        Talk.objects.create(
            title="T1",
            talk_type="talk",
            is_scheduled=True,
            day=self.day,
            session=session,
            start_time=time(10, 0),
            end_time=time(10, 20),
        )
        Talk.objects.create(
            title="T2",
            talk_type="talk",
            is_scheduled=True,
            day=self.day,
            session=session,
            start_time=time(10, 20),
            end_time=time(10, 40),
        )

        items = self.timeline()

        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["type"], "session")
        self.assertEqual(items[0]["start_time"], time(10, 0))
        self.assertEqual(items[0]["end_time"], time(10, 40))

    def test_standalone_talk_and_session_sorted_by_start_time(self):
        Talk.objects.create(
            title="Early Talk",
            talk_type="talk",
            is_scheduled=True,
            day=self.day,
            start_time=time(9, 0),
            end_time=time(9, 30),
        )
        session = Session.objects.create(
            day=self.day, start_time=time(10, 0), end_time=time(11, 0)
        )

        items = self.timeline()

        self.assertEqual(
            [(i["type"], i["start_time"]) for i in items],
            [("talk", time(9, 0)), ("session", time(10, 0))],
        )

    def test_session_without_talks_and_times_is_skipped(self):
        Session.objects.create(day=self.day, chair="Nobody")

        self.assertEqual(self.timeline(), [])

    def test_untimed_standalone_talk_sorts_last_instead_of_crashing(self):
        Talk.objects.create(
            title="Timed",
            talk_type="talk",
            is_scheduled=True,
            day=self.day,
            start_time=time(9, 0),
            end_time=time(9, 30),
        )
        Talk.objects.create(
            title="Untimed",
            talk_type="talk",
            day=self.day,
        )

        items = self.timeline()

        self.assertEqual(len(items), 2)
        self.assertEqual(items[0]["data"]["title"], "Timed")
        self.assertEqual(items[1]["data"]["title"], "Untimed")
        self.assertIsNone(items[1]["start_time"])
