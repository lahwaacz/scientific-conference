from datetime import date

from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from .conftest import api
from .models import (
    Abstract,
    Conference,
    Participant,
    ParticipantSubmission,
    Talk,
)
from .serializers import ParticipantSubmissionSerializer


def wsc_conference():
    return Conference.objects.get_or_create(slug="wsc2026-test")[0]


class TestParticipantSubmissionModel(TestCase):
    def test_publish_creates_participant_abstract_and_unscheduled_talk(self):
        submission = ParticipantSubmission.objects.create(
            conference=wsc_conference(),
            name="Alice Smith",
            email="alice@example.com",
            affiliation="CTU",
            abstract_title="Numerical Methods",
            abstract_text="Study of numerical methods",
            arrival_date=date(2026, 9, 10),
            departure_date=date(2026, 9, 12),
        )

        participant, abstract, talk = submission.publish()
        submission.refresh_from_db()

        self.assertEqual(submission.status, "approved")
        self.assertIsNotNone(submission.published_participant)
        self.assertIsNotNone(submission.published_abstract)
        assert abstract is not None
        assert talk is not None

        self.assertEqual(Participant.objects.count(), 1)
        self.assertEqual(Abstract.objects.count(), 1)
        self.assertEqual(Talk.objects.count(), 1)

        self.assertEqual(participant.name, "Alice Smith")
        self.assertEqual(abstract.title, "Numerical Methods")
        self.assertEqual(talk.abstract, abstract)
        self.assertEqual(talk.participant, participant)
        self.assertFalse(talk.is_scheduled)
        self.assertEqual(talk.talk_type, "talk")

    def test_stay_duration_property(self):
        submission = ParticipantSubmission(
            name="Bob Brown",
            email="bob@example.com",
            affiliation="CTU",
            arrival_date=date(2026, 9, 10),
            departure_date=date(2026, 9, 13),
        )
        self.assertEqual(submission.stay_duration, 3)


class TestParticipantSubmissionSerializer(TestCase):
    def test_departure_date_must_be_after_arrival_date(self):
        data = {
            "name": "Carol White",
            "email": "carol@example.com",
            "affiliation": "CTU",
            "arrival_date": "2026-09-12",
            "departure_date": "2026-09-12",
            "abstract_title": "",
            "abstract_text": "",
            "additional_authors": "",
            "additional_affiliations": "",
            "info": "",
            "is_student": False,
        }

        serializer = ParticipantSubmissionSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn("departure_date", serializer.errors)

    def test_valid_submission_data_is_accepted(self):
        data = {
            "name": "Carol White",
            "email": "carol@example.com",
            "affiliation": "CTU",
            "arrival_date": "2026-09-12",
            "departure_date": "2026-09-14",
            "abstract_title": "Finite Elements",
            "abstract_text": "Short abstract",
            "additional_authors": "",
            "additional_affiliations": "",
            "info": "",
            "is_student": True,
        }

        serializer = ParticipantSubmissionSerializer(data=data)
        self.assertTrue(serializer.is_valid(), serializer.errors)


class TestSubmissionAPI(APITestCase):
    def test_create_submission(self):
        wsc_conference()
        url = api("submit/")
        data = {
            "name": "David Green",
            "email": "david@example.com",
            "affiliation": "CTU",
            "abstract_title": "Scientific Computing",
            "abstract_text": "A short abstract",
            "additional_authors": "",
            "additional_affiliations": "",
            "arrival_date": "2026-09-10",
            "departure_date": "2026-09-12",
            "info": "Vegetarian meal",
            "is_student": True,
        }

        response = self.client.post(url, data, format="json")

        self.assertEqual(response.status_code, 201)
        self.assertEqual(ParticipantSubmission.objects.count(), 1)
        created = ParticipantSubmission.objects.first()
        assert created is not None
        self.assertEqual(created.status, "pending")


class TestPublishSubmissionAPI(APITestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            username="admin",
            password="adminpass",
            is_staff=True,
        )
        refresh = RefreshToken.for_user(self.admin)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")

        self.submission = ParticipantSubmission.objects.create(
            conference=wsc_conference(),
            name="Eva Brown",
            email="eva@example.com",
            affiliation="CTU",
            abstract_title="Model Reduction",
            abstract_text="Abstract text",
            arrival_date=date(2026, 9, 10),
            departure_date=date(2026, 9, 12),
        )

    def test_publish_submission_endpoint(self):
        url = api(f"admin/submissions/{self.submission.id}/publish/")
        response = self.client.post(url)

        self.assertEqual(response.status_code, 200)
        self.submission.refresh_from_db()
        self.assertEqual(self.submission.status, "approved")
        self.assertIsNotNone(self.submission.published_participant)
        self.assertIsNotNone(self.submission.published_abstract)
        self.assertEqual(Talk.objects.count(), 1)

    def test_publish_endpoint_rejects_non_staff(self):
        self.client.credentials()
        url = api(f"admin/submissions/{self.submission.id}/publish/")
        response = self.client.post(url)

        self.assertIn(response.status_code, [401, 403])
