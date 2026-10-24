"""Tests for the submission publish workflow and admin edit/delete flows."""

import shutil
import tempfile
from datetime import date, time
from unittest.mock import patch

from django.contrib import admin as django_admin
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import RequestFactory, TestCase, override_settings
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from .admin import ParticipantAdmin, ParticipantSubmissionAdmin
from .conftest import api
from .models import (
    Abstract,
    Conference,
    ConferenceDay,
    Participant,
    ParticipantSubmission,
    Session,
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
    def test_attend_creates_participant_only(self):
        submission = make_submission(
            contribution_type="attend", abstract_title="", abstract_text=""
        )

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

    def test_poster_creates_abstract_and_poster_talk(self):
        submission = make_submission(contribution_type="poster")

        participant, abstract, talk = submission.publish()

        self.assertIsNotNone(abstract)
        assert talk is not None
        participant.refresh_from_db()
        talk.refresh_from_db()
        self.assertEqual(participant.contribution_type, "poster")
        self.assertEqual(talk.talk_type, "poster")
        self.assertEqual(Talk.objects.count(), 1)

    def test_scheduled_poster_to_talk_detaches_session_and_times(self):
        submission = make_submission(contribution_type="poster")
        _, _, talk = submission.publish()
        assert talk is not None
        day = ConferenceDay.objects.create(
            conference=wsc_conference(), date=date(2026, 9, 10)
        )
        session = Session.objects.create(
            conference=wsc_conference(),
            day=day,
            kind="poster",
            start_time=time(14, 0),
            end_time=time(15, 0),
        )
        talk.session = session
        talk.day = day
        talk.is_scheduled = True
        talk.save()

        submission.refresh_from_db()
        submission.contribution_type = "talk"
        submission.save()
        _, _, updated_talk = submission.publish()

        assert updated_talk is not None
        updated_talk.refresh_from_db()
        self.assertEqual(updated_talk.talk_type, "talk")
        self.assertIsNone(updated_talk.session)
        self.assertIsNone(updated_talk.day)
        self.assertFalse(updated_talk.is_scheduled)
        self.assertIsNone(updated_talk.start_time)
        self.assertIsNone(updated_talk.end_time)

    def test_talk_to_poster_keeps_unscheduled_talk_and_changes_type(self):
        submission = make_submission()
        _, abstract, talk = submission.publish()
        assert abstract is not None
        assert talk is not None

        submission.refresh_from_db()
        submission.contribution_type = "poster"
        submission.save()
        _, abstract2, talk2 = submission.publish()

        self.assertEqual(abstract2, abstract)
        self.assertEqual(talk2, talk)
        talk.refresh_from_db()
        self.assertEqual(talk.talk_type, "poster")
        self.assertTrue(Talk.objects.filter(pk=talk.pk).exists())

    def test_talk_to_attend_removes_abstract_and_talk(self):
        submission = make_submission()
        _, abstract, talk = submission.publish()
        assert abstract is not None
        assert talk is not None

        submission.refresh_from_db()
        submission.contribution_type = "attend"
        submission.save()
        participant, abstract2, talk2 = submission.publish()

        self.assertIsNone(abstract2)
        self.assertIsNone(talk2)
        self.assertEqual(Abstract.objects.count(), 0)
        self.assertEqual(Talk.objects.count(), 0)
        participant.refresh_from_db()
        self.assertEqual(participant.contribution_type, "attend")

    def test_scheduled_talk_blocks_type_change(self):
        submission = make_submission()
        _, _, talk = submission.publish()
        assert talk is not None
        talk.is_scheduled = True
        talk.save()

        submission.refresh_from_db()
        submission.contribution_type = "poster"
        submission.save()

        with self.assertRaises(ValidationError):
            submission.publish()
        self.assertTrue(Talk.objects.filter(pk=talk.pk).exists())

    def test_same_email_attend_does_not_delete_existing_talk(self):
        talk_submission = make_submission()
        talk_participant, abstract, talk = talk_submission.publish()
        assert abstract is not None
        assert talk is not None

        attend_submission = make_submission(
            contribution_type="attend", abstract_title="", abstract_text=""
        )
        attend_participant, attend_abstract, attend_talk = attend_submission.publish()

        self.assertNotEqual(attend_participant, talk_participant)
        self.assertIsNone(attend_abstract)
        self.assertIsNone(attend_talk)
        self.assertTrue(Abstract.objects.filter(pk=abstract.pk).exists())
        self.assertTrue(Talk.objects.filter(pk=talk.pk).exists())
        talk_participant.refresh_from_db()
        attend_participant.refresh_from_db()
        self.assertEqual(talk_participant.contribution_type, "talk")
        self.assertEqual(attend_participant.contribution_type, "attend")

    def test_same_email_poster_does_not_overwrite_existing_abstract(self):
        talk_submission = make_submission()
        _, abstract, talk = talk_submission.publish()
        assert abstract is not None
        assert talk is not None

        poster_submission = make_submission(
            contribution_type="poster", abstract_title="Poster Title"
        )
        poster_participant, poster_abstract, poster_talk = poster_submission.publish()

        self.assertIsNotNone(poster_abstract)
        assert poster_talk is not None
        self.assertNotEqual(poster_abstract, abstract)
        abstract.refresh_from_db()
        poster_talk.refresh_from_db()
        self.assertEqual(abstract.title, "Numerical Methods")
        self.assertTrue(Talk.objects.filter(pk=talk.pk).exists())
        self.assertEqual(poster_talk.talk_type, "poster")
        self.assertEqual(Abstract.objects.count(), 2)
        self.assertEqual(
            poster_participant.contribution_type,
            "poster",
        )

    def test_same_email_second_talk_gets_its_own_records(self):
        first = make_submission(abstract_title="First Talk")
        first_participant, first_abstract, first_talk = first.publish()
        assert first_abstract is not None
        assert first_talk is not None

        second = make_submission(abstract_title="Second Talk")
        second_participant, second_abstract, second_talk = second.publish()

        self.assertNotEqual(second_participant, first_participant)
        self.assertNotEqual(second_abstract, first_abstract)
        self.assertNotEqual(second_talk, first_talk)
        self.assertEqual(Abstract.objects.count(), 2)
        self.assertEqual(Talk.objects.count(), 2)
        first_abstract.refresh_from_db()
        self.assertEqual(first_abstract.title, "First Talk")

    def test_same_email_attend_leaves_scheduled_talk_untouched(self):
        talk_submission = make_submission()
        _, _, talk = talk_submission.publish()
        assert talk is not None
        talk.is_scheduled = True
        talk.save()

        attend_submission = make_submission(
            contribution_type="attend", abstract_title="", abstract_text=""
        )
        attend_submission.publish()

        talk.refresh_from_db()
        self.assertTrue(talk.is_scheduled)
        self.assertTrue(Talk.objects.filter(pk=talk.pk).exists())


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


class TestSubmissionUnpublish(TestCase):
    def test_unpublish_keeps_submission_and_removes_public_rows(self):
        submission = make_submission()
        participant, abstract, talk = submission.publish()
        assert participant is not None
        assert abstract is not None
        assert talk is not None

        submission.unpublish()

        submission.refresh_from_db()
        self.assertEqual(submission.status, "pending")
        self.assertIsNone(submission.published_participant)
        self.assertIsNone(submission.published_abstract)
        self.assertEqual(Participant.objects.count(), 0)
        self.assertEqual(Abstract.objects.count(), 0)
        self.assertEqual(Talk.objects.count(), 0)

    def test_admin_participant_delete_unpublishes_linked_submission(self):
        submission = make_submission()
        participant, abstract, talk = submission.publish()
        assert participant is not None
        assert abstract is not None
        assert talk is not None
        participant_id = participant.pk

        model_admin = ParticipantAdmin(Participant, django_admin.site)
        model_admin.delete_model(RequestFactory().get("/"), participant)

        submission.refresh_from_db()
        self.assertEqual(submission.status, "pending")
        self.assertIsNone(submission.published_participant)
        self.assertIsNone(submission.published_abstract)
        self.assertFalse(Participant.objects.filter(pk=participant_id).exists())
        self.assertEqual(Abstract.objects.count(), 0)
        self.assertEqual(Talk.objects.count(), 0)


class TestSubmissionRejectRestore(TestCase):
    def test_reject_pending_sets_message_and_review_timestamp(self):
        submission = make_submission()

        submission.reject("Please provide a longer abstract.")

        submission.refresh_from_db()
        self.assertEqual(submission.status, "rejected")
        self.assertEqual(
            submission.rejection_message, "Please provide a longer abstract."
        )
        self.assertIsNotNone(submission.reviewed_at)
        self.assertEqual(Participant.objects.count(), 0)
        self.assertEqual(Abstract.objects.count(), 0)

    def test_reject_approved_raises(self):
        submission = make_submission()
        submission.publish()

        with self.assertRaises(ValidationError):
            submission.reject("not allowed")

        submission.refresh_from_db()
        self.assertEqual(submission.status, "approved")

    def test_restore_rejected_clears_message_and_review_timestamp(self):
        submission = make_submission()
        submission.reject("Not accepted")

        submission.restore()

        submission.refresh_from_db()
        self.assertEqual(submission.status, "pending")
        self.assertEqual(submission.rejection_message, "")
        self.assertIsNone(submission.reviewed_at)

    def test_restore_pending_raises(self):
        submission = make_submission()

        with self.assertRaises(ValidationError):
            submission.restore()

        submission.refresh_from_db()
        self.assertEqual(submission.status, "pending")

    def test_publish_rejected_raises(self):
        submission = make_submission()
        submission.reject("Not accepted")

        with self.assertRaises(ValidationError):
            submission.publish()

        submission.refresh_from_db()
        self.assertEqual(submission.status, "rejected")


class TestSubmissionAdminBulkPublish(TestCase):
    def test_publish_selected_skips_rejected(self):
        pending = make_submission(name="Pending", email="pending@example.com")
        approved = make_submission(name="Approved", email="approved@example.com")
        approved.publish()
        rejected = make_submission(name="Rejected", email="rejected@example.com")
        rejected.reject("Not accepted")

        model_admin = ParticipantSubmissionAdmin(
            ParticipantSubmission, django_admin.site
        )
        request = RequestFactory().get("/")
        with patch.object(model_admin, "message_user") as message_user:
            model_admin.publish_selected(request, ParticipantSubmission.objects.all())

        message_user.assert_called_once()
        summary = message_user.call_args.args[1]
        self.assertIn("1 published", summary)
        self.assertIn("1 already published", summary)
        self.assertIn("1 rejected (restore first)", summary)
        pending.refresh_from_db()
        rejected.refresh_from_db()
        self.assertEqual(pending.status, "approved")
        self.assertEqual(rejected.status, "rejected")


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
        admin = User.objects.create_user(
            username="admin", password="pw", is_staff=True, is_superuser=True
        )
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

    def test_list_orders_submissions_by_surname(self):
        make_submission(name="Zoe Adams", email="zoe@example.com")
        make_submission(name="adam baker", email="adam@example.com")
        make_submission(name="Mia Clarke", email="mia@example.com")

        response = self.client.get(api("admin/submissions/"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            [row["name"] for row in response.data],
            ["Zoe Adams", "adam baker", "Mia Clarke"],
        )

    def test_list_status_filter_preserves_surname_order(self):
        make_submission(name="Zoe Adams", email="zoe@example.com", status="pending")
        make_submission(name="Adam Baker", email="adam@example.com", status="pending")
        make_submission(name="Mia Clarke", email="mia@example.com", status="approved")

        response = self.client.get(api("admin/submissions/"), {"status": "pending"})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            [row["name"] for row in response.data],
            ["Zoe Adams", "Adam Baker"],
        )

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
        assert participant is not None
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
            conference=other_conference(),
            contribution_type="attend",
            abstract_title="",
            abstract_text="",
        )
        sub_b.publish()
        self.assertIsNone(sub_b.published_abstract)

        response = self.client.patch(
            OTHER_SUBMISSION_URL.format(sub_b.id),
            {
                "contribution_type": "talk",
                "abstract_title": "Late Abstract",
                "abstract_text": "Late text",
            },
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

    def test_delete_via_api_is_not_allowed(self):
        submission = make_submission()
        submission.publish()

        response = self.client.delete(SUBMISSION_URL.format(submission.id))

        self.assertEqual(response.status_code, 405)
        self.assertTrue(ParticipantSubmission.objects.filter(pk=submission.pk).exists())
        self.assertEqual(Participant.objects.count(), 1)
        self.assertEqual(Abstract.objects.count(), 1)
        self.assertEqual(Talk.objects.count(), 1)

    def test_reject_pending_sets_message_and_removes_from_review(self):
        submission = make_submission()

        response = self.client.post(
            api(f"admin/submissions/{submission.id}/reject/"),
            {"message": "Please provide a longer abstract."},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        submission.refresh_from_db()
        self.assertEqual(submission.status, "rejected")
        self.assertEqual(
            submission.rejection_message, "Please provide a longer abstract."
        )
        self.assertIsNotNone(submission.reviewed_at)
        self.assertEqual(Participant.objects.count(), 0)
        self.assertEqual(Abstract.objects.count(), 0)

    def test_reject_without_message_is_allowed(self):
        submission = make_submission()

        response = self.client.post(
            api(f"admin/submissions/{submission.id}/reject/"),
            {},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        submission.refresh_from_db()
        self.assertEqual(submission.status, "rejected")
        self.assertEqual(submission.rejection_message, "")

    def test_reject_approved_returns_400(self):
        submission = make_submission()
        submission.publish()

        response = self.client.post(
            api(f"admin/submissions/{submission.id}/reject/"),
            {"message": "no"},
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        submission.refresh_from_db()
        self.assertEqual(submission.status, "approved")

    def test_restore_rejected_returns_to_pending(self):
        submission = make_submission()
        submission.reject("Not accepted")

        response = self.client.post(api(f"admin/submissions/{submission.id}/restore/"))

        self.assertEqual(response.status_code, 200)
        submission.refresh_from_db()
        self.assertEqual(submission.status, "pending")
        self.assertEqual(submission.rejection_message, "")
        self.assertIsNone(submission.reviewed_at)

    def test_restore_pending_returns_400(self):
        submission = make_submission()

        response = self.client.post(api(f"admin/submissions/{submission.id}/restore/"))

        self.assertEqual(response.status_code, 400)
        submission.refresh_from_db()
        self.assertEqual(submission.status, "pending")

    def test_publish_rejected_returns_400(self):
        submission = make_submission()
        submission.reject("Not accepted")

        response = self.client.post(api(f"admin/submissions/{submission.id}/publish/"))

        self.assertEqual(response.status_code, 400)
        submission.refresh_from_db()
        self.assertEqual(submission.status, "rejected")

    def test_list_excludes_rejected_by_default_and_filters_rejected(self):
        pending = make_submission(name="Pending Person", email="pending@example.com")
        approved = make_submission(name="Approved Person", email="approved@example.com")
        approved.publish()
        rejected = make_submission(name="Rejected Person", email="rejected@example.com")
        rejected.reject("No")

        default_response = self.client.get(api("admin/submissions/"))
        rejected_response = self.client.get(
            api("admin/submissions/"), {"status": "rejected"}
        )

        self.assertEqual(default_response.status_code, 200)
        self.assertEqual(
            {row["name"] for row in default_response.data},
            {"Pending Person", "Approved Person"},
        )
        self.assertEqual(rejected_response.status_code, 200)
        self.assertEqual(
            [row["name"] for row in rejected_response.data],
            ["Rejected Person"],
        )
        self.assertNotIn(pending.name, {row["name"] for row in rejected_response.data})

    def test_list_empty_status_excludes_rejected(self):
        make_submission(name="Pending Person", email="pending2@example.com")
        rejected = make_submission(
            name="Rejected Person", email="rejected2@example.com"
        )
        rejected.reject("No")

        response = self.client.get(api("admin/submissions/"), {"status": ""})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            [row["name"] for row in response.data],
            ["Pending Person"],
        )

    def test_list_invalid_status_returns_400(self):
        make_submission()

        response = self.client.get(
            api("admin/submissions/"), {"status": "not-a-status"}
        )

        self.assertEqual(response.status_code, 400)

    def test_unpublish_keeps_submission_and_resets_public_state(self):
        submission = make_submission()
        submission.publish()

        response = self.client.post(
            api(f"admin/submissions/{submission.id}/unpublish/")
        )

        self.assertEqual(response.status_code, 200)
        submission.refresh_from_db()
        self.assertEqual(submission.status, "pending")
        self.assertIsNone(submission.published_participant)
        self.assertIsNone(submission.published_abstract)
        self.assertEqual(Participant.objects.count(), 0)
        self.assertEqual(Abstract.objects.count(), 0)
        self.assertEqual(Talk.objects.count(), 0)

    def test_unpublish_rejects_pending_submission(self):
        submission = make_submission()

        response = self.client.post(
            api(f"admin/submissions/{submission.id}/unpublish/")
        )

        self.assertEqual(response.status_code, 400)
        submission.refresh_from_db()
        self.assertEqual(submission.status, "pending")

    def test_unpublish_rejects_rejected_submission(self):
        submission = make_submission()
        submission.reject("Not accepted")

        response = self.client.post(
            api(f"admin/submissions/{submission.id}/unpublish/")
        )

        self.assertEqual(response.status_code, 400)
        submission.refresh_from_db()
        self.assertEqual(submission.status, "rejected")

    def test_patch_to_attend_removes_published_abstract(self):
        submission = make_submission()
        submission.publish()
        self.assertEqual(Abstract.objects.count(), 1)

        response = self.client.patch(
            SUBMISSION_URL.format(submission.id),
            {"contribution_type": "attend"},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        submission.refresh_from_db()
        self.assertIsNone(submission.published_abstract)
        self.assertEqual(Abstract.objects.count(), 0)
        self.assertEqual(Talk.objects.count(), 0)
        participant = submission.published_participant
        assert participant is not None
        self.assertEqual(participant.contribution_type, "attend")

    def test_patch_rejects_type_disabled_for_conference(self):
        conference = wsc_conference()
        conference.registration_allow_poster = False
        conference.registration_allow_attend = False
        conference.save()
        submission = make_submission()

        response = self.client.patch(
            SUBMISSION_URL.format(submission.id),
            {"contribution_type": "poster"},
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("contribution_type", response.data)
        submission.refresh_from_db()
        self.assertEqual(submission.contribution_type, "talk")

    def test_patch_to_talk_requires_title(self):
        submission = make_submission(
            contribution_type="attend", abstract_title="", abstract_text=""
        )

        response = self.client.patch(
            SUBMISSION_URL.format(submission.id),
            {"contribution_type": "talk"},
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("abstract_title", response.data)

    def test_patch_type_change_with_scheduled_talk_returns_400(self):
        submission = make_submission()
        _, _, talk = submission.publish()
        assert talk is not None
        talk.is_scheduled = True
        talk.save()

        response = self.client.patch(
            SUBMISSION_URL.format(submission.id),
            {"contribution_type": "poster"},
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        submission.refresh_from_db()
        self.assertEqual(submission.contribution_type, "talk")
        self.assertTrue(Talk.objects.filter(pk=talk.pk).exists())
