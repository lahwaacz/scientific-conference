"""Tests for the submission publish workflow and admin edit/delete flows."""

import shutil
import tempfile
from datetime import date

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from .conftest import api
from .models import (
    Abstract,
    Conference,
    Participant,
    ParticipantSubmission,
    Talk,
)

SUBMISSION_URL = api("admin/submissions/{}/")
OTHER_SUBMISSION_URL = api("admin/submissions/{}/", slug="wsc2027-test")


def wsc_conference():
    return Conference.objects.get_or_create(slug="wsc2026-test")[0]


def other_conference():
    return Conference.objects.get_or_create(slug="wsc2027-test")[0]


def make_submission(**overrides):
    data = {
        "name": "Jane Doe",
        "email": "jane@example.com",
        "affiliation": "CTU",
        "abstract_title": "Numerical Methods",
        "abstract_text": "Some abstract text",
        "arrival_date": date(2026, 9, 10),
        "departure_date": date(2026, 9, 12),
    }
    data.update(overrides)
    data.setdefault("conference", wsc_conference())
    return ParticipantSubmission.objects.create(**data)


class TestPublishBranches(TestCase):
    def test_no_abstract_creates_participant_only(self):
        submission = make_submission(abstract_title="", abstract_text="")

        participant, abstract, talk = submission.publish()

        self.assertIsNone(abstract)
        self.assertIsNone(talk)
        submission.refresh_from_db()
        self.assertEqual(submission.status, "approved")
        self.assertIsNotNone(submission.reviewed_at)
        self.assertEqual(submission.published_participant, participant)
        self.assertIsNone(submission.published_abstract)

    def test_default_title_fallback_when_title_blank(self):
        submission = make_submission(abstract_title="")

        _, abstract, talk = submission.publish()

        assert abstract is not None
        assert talk is not None
        self.assertEqual(abstract.title, "Presentation by Jane Doe")
        self.assertEqual(talk.title, abstract.title)
        self.assertEqual(talk.talk_type, "talk")
        self.assertFalse(talk.is_scheduled)

    def test_matches_existing_participant_by_email(self):
        existing = Participant.objects.create(
            conference=wsc_conference(),
            name="Old Name",
            email="jane@example.com",
            affiliation="Old Affil",
        )
        submission = make_submission()

        participant, _, _ = submission.publish()

        self.assertEqual(participant, existing)
        self.assertEqual(Participant.objects.count(), 1)
        existing.refresh_from_db()
        self.assertEqual(existing.name, "Jane Doe")
        self.assertEqual(existing.affiliation, "CTU")

    def test_duplicate_email_participants_creates_new_one(self):
        conference = wsc_conference()
        Participant.objects.create(
            conference=conference, name="A", email="jane@example.com"
        )
        Participant.objects.create(
            conference=conference, name="B", email="jane@example.com"
        )
        submission = make_submission()

        participant, _, _ = submission.publish()

        self.assertEqual(Participant.objects.count(), 3)
        self.assertEqual(participant.name, "Jane Doe")

    def test_blank_email_always_creates_new_participant(self):
        Participant.objects.create(conference=wsc_conference(), name="Same", email="")
        submission = make_submission(email="")

        participant, _, _ = submission.publish()

        self.assertEqual(Participant.objects.count(), 2)
        self.assertEqual(participant.email, "")

    def test_additional_authors_and_affiliations_concatenated(self):
        submission = make_submission(
            additional_authors="John Roe",
            additional_affiliations="MIT",
        )

        _, abstract, _ = submission.publish()

        assert abstract is not None
        self.assertEqual(abstract.authors, "Jane Doe, John Roe")
        self.assertEqual(abstract.department, "CTU\nMIT")

    def test_republish_reuses_objects_and_updates_abstract_and_talk(self):
        submission = make_submission()
        participant, abstract, talk = submission.publish()

        submission.refresh_from_db()
        submission.abstract_title = "Better Title"
        submission.save()
        participant2, abstract2, talk2 = submission.publish()

        self.assertEqual(participant2, participant)
        self.assertEqual(abstract2, abstract)
        self.assertEqual(talk2, talk)
        self.assertEqual(Participant.objects.count(), 1)
        self.assertEqual(Abstract.objects.count(), 1)
        self.assertEqual(Talk.objects.count(), 1)
        assert abstract2 is not None
        assert talk2 is not None
        self.assertEqual(abstract2.title, "Better Title")
        self.assertEqual(talk2.title, "Better Title")


class TestPublishConferenceIsolation(TestCase):
    def test_same_email_two_conferences_creates_two_participants(self):
        sub_a = make_submission(conference=wsc_conference())
        sub_b = make_submission(conference=other_conference())

        participant_a, abstract_a, talk_a = sub_a.publish()
        participant_b, abstract_b, talk_b = sub_b.publish()

        self.assertEqual(Participant.objects.count(), 2)
        self.assertNotEqual(participant_a, participant_b)
        self.assertEqual(participant_a.conference, wsc_conference())
        self.assertEqual(participant_b.conference, other_conference())
        assert abstract_a is not None
        assert abstract_b is not None
        self.assertEqual(abstract_a.conference, wsc_conference())
        self.assertEqual(abstract_b.conference, other_conference())
        self.assertEqual(abstract_a.participant, participant_a)
        self.assertEqual(abstract_b.participant, participant_b)
        assert talk_a is not None
        assert talk_b is not None
        self.assertEqual(talk_a.conference, wsc_conference())
        self.assertEqual(talk_b.conference, other_conference())
        self.assertEqual(talk_a.abstract, abstract_a)
        self.assertEqual(talk_b.abstract, abstract_b)

    def test_existing_participant_in_other_conference_does_not_match(self):
        existing = Participant.objects.create(
            conference=wsc_conference(),
            name="Old Name",
            email="jane@example.com",
            affiliation="Old Affil",
        )
        submission = make_submission(conference=other_conference())

        participant, _, _ = submission.publish()

        self.assertNotEqual(participant, existing)
        self.assertEqual(Participant.objects.count(), 2)
        self.assertEqual(participant.conference, other_conference())
        existing.refresh_from_db()
        self.assertEqual(existing.name, "Old Name")
        self.assertEqual(existing.affiliation, "Old Affil")


class TestSubmissionDelete(TestCase):
    def test_delete_approved_cascades_published_records(self):
        submission = make_submission()
        submission.publish()

        submission.delete()

        self.assertEqual(ParticipantSubmission.objects.count(), 0)
        self.assertEqual(Participant.objects.count(), 0)
        self.assertEqual(Abstract.objects.count(), 0)
        self.assertEqual(Talk.objects.count(), 0)

    def test_delete_pending_keeps_nothing_but_submission(self):
        Participant.objects.create(conference=wsc_conference(), name="Someone Else")
        submission = make_submission()

        submission.delete()

        self.assertEqual(ParticipantSubmission.objects.count(), 0)
        self.assertEqual(Participant.objects.count(), 1)


_TEMP_MEDIA = tempfile.mkdtemp()


@override_settings(MEDIA_ROOT=_TEMP_MEDIA)
class TestSubmissionAdminAPI(TestCase):
    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(_TEMP_MEDIA, ignore_errors=True)

    def setUp(self):
        admin = User.objects.create_user(username="admin", password="pw", is_staff=True)
        token = RefreshToken.for_user(admin)
        self.client = APIClient()
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token.access_token}")

    def payload(self, **overrides):
        data = {
            "name": "Jane Doe",
            "email": "jane@example.com",
            "affiliation": "CTU",
            "abstract_title": "Numerical Methods",
            "abstract_text": "Some abstract text",
            "additional_authors": "",
            "additional_affiliations": "",
            "arrival_date": "2026-09-10",
            "departure_date": "2026-09-12",
            "info": "",
            "is_student": False,
            "status": "approved",
        }
        data.update(overrides)
        return data

    def test_put_approved_submission_syncs_published_records(self):
        submission = make_submission()
        submission.publish()

        response = self.client.put(
            SUBMISSION_URL.format(submission.id),
            self.payload(name="Jane Changed", abstract_title="New Title"),
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        participant = submission.published_participant
        assert participant is not None
        participant.refresh_from_db()
        abstract = submission.published_abstract
        assert abstract is not None
        abstract.refresh_from_db()
        talk = Talk.objects.get(abstract=abstract)
        self.assertEqual(participant.name, "Jane Changed")
        self.assertEqual(abstract.title, "New Title")
        self.assertEqual(talk.title, "New Title")

    def test_patch_with_cleared_abstract_fields_keeps_records(self):
        submission = make_submission()
        submission.publish()

        response = self.client.patch(
            SUBMISSION_URL.format(submission.id),
            {"abstract_title": "", "abstract_text": ""},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(Abstract.objects.count(), 1)
        self.assertEqual(Talk.objects.count(), 1)

    def test_patch_photo_null_removes_photo_from_submission_and_participant(self):
        photo = SimpleUploadedFile("p.jpg", b"fake", content_type="image/jpeg")
        submission = make_submission(photo=photo)
        submission.publish()
        self.assertTrue(submission.photo)
        participant = submission.published_participant
        participant.refresh_from_db()
        self.assertTrue(participant.photo)

        response = self.client.patch(
            SUBMISSION_URL.format(submission.id),
            {"photo": None},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        submission.refresh_from_db()
        participant.refresh_from_db()
        self.assertFalse(submission.photo)
        self.assertFalse(participant.photo)

    def test_patch_leaves_other_conference_rows_untouched(self):
        sub_a = make_submission(conference=wsc_conference())
        sub_a.publish()
        sub_b = make_submission(conference=other_conference())
        sub_b.publish()

        response = self.client.patch(
            OTHER_SUBMISSION_URL.format(sub_b.id),
            {"name": "Jane Renamed", "abstract_title": "B New Title"},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        participant_a = sub_a.published_participant
        assert participant_a is not None
        participant_a.refresh_from_db()
        abstract_a = sub_a.published_abstract
        assert abstract_a is not None
        abstract_a.refresh_from_db()
        talk_a = Talk.objects.get(abstract=abstract_a)
        self.assertEqual(participant_a.name, "Jane Doe")
        self.assertEqual(abstract_a.title, "Numerical Methods")
        self.assertEqual(talk_a.title, "Numerical Methods")
        sub_b.refresh_from_db()
        abstract_b = sub_b.published_abstract
        assert abstract_b is not None
        abstract_b.refresh_from_db()
        self.assertEqual(abstract_b.title, "B New Title")

    def test_patch_adding_abstract_creates_rows_in_own_conference(self):
        sub_b = make_submission(
            conference=other_conference(), abstract_title="", abstract_text=""
        )
        sub_b.publish()
        self.assertIsNone(sub_b.published_abstract)

        response = self.client.patch(
            OTHER_SUBMISSION_URL.format(sub_b.id),
            {"abstract_title": "Late Abstract", "abstract_text": "Late text"},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        sub_b.refresh_from_db()
        abstract = sub_b.published_abstract
        self.assertIsNotNone(abstract)
        assert abstract is not None
        self.assertEqual(abstract.conference, other_conference())
        talk = Talk.objects.get(abstract=abstract)
        self.assertEqual(talk.conference, other_conference())

    def test_delete_approved_via_api_cascades(self):
        submission = make_submission()
        submission.publish()

        response = self.client.delete(SUBMISSION_URL.format(submission.id))

        self.assertEqual(response.status_code, 204)
        self.assertEqual(ParticipantSubmission.objects.count(), 0)
        self.assertEqual(Participant.objects.count(), 0)
        self.assertEqual(Abstract.objects.count(), 0)
        self.assertEqual(Talk.objects.count(), 0)
