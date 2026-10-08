"""Tests for submission tracking token, participant reference and linked user."""

from datetime import date, timedelta
from io import BytesIO
from pathlib import Path
from typing import Any, cast

import pytest
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import IntegrityError, transaction
from django.urls import reverse
from django.utils import timezone
from PIL import Image
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from .conftest import api
from .models import ConferenceInfo, ParticipantSubmission
from .serializers import (
    ParticipantSubmissionCreateSerializer,
    ParticipantSubmissionSerializer,
    ParticipantTrackingSerializer,
    ParticipantTrackingUpdateSerializer,
)


def make_submission(conference, **overrides):
    data = {
        "name": "Jane Doe",
        "email": "jane@example.com",
        "affiliation": "CTU",
        "abstract_title": "Numerical Methods",
        "abstract_text": "Some abstract text",
        "arrival_date": date(2026, 9, 10),
        "departure_date": date(2026, 9, 12),
        "conference": conference,
    }
    data.update(overrides)
    return ParticipantSubmission.objects.create(**data)


@pytest.mark.django_db
class TestTrackingToken:
    def test_two_submissions_get_distinct_non_empty_tokens(self, wsc):
        first = make_submission(wsc, email="a@example.com")
        second = make_submission(wsc, email="b@example.com")

        assert first.tracking_token
        assert second.tracking_token
        assert first.tracking_token != second.tracking_token

    def test_duplicate_tracking_token_rejected(self, wsc):
        first = make_submission(wsc)

        with pytest.raises(IntegrityError), transaction.atomic():
            make_submission(
                wsc, email="clone@example.com", tracking_token=first.tracking_token
            )

        # The atomic block rolled the violation back to its savepoint, so
        # the outer transaction is still usable and the original row is intact.
        first.refresh_from_db()
        assert first.tracking_token


@pytest.mark.django_db
class TestParticipantReference:
    def test_reference_is_slug_and_zero_padded_pk(self, wsc):
        submission = make_submission(wsc)

        assert submission.participant_reference == f"{wsc.slug}-{submission.pk:04d}"

    def test_reference_is_empty_on_unsaved_instance(self, wsc):
        submission = ParticipantSubmission(conference=wsc, name="Unsaved")

        assert submission.pk is None
        assert submission.participant_reference == ""


@pytest.mark.django_db
class TestLinkedUser:
    def test_linked_user_defaults_to_none(self, wsc):
        submission = make_submission(wsc)

        assert submission.linked_user is None

    def test_linked_user_accepts_staff_user(self, wsc):
        staff = User.objects.create_user(
            username="staff1", password="pw", is_staff=True
        )

        submission = make_submission(wsc, linked_user=staff)

        submission.refresh_from_db()
        assert submission.linked_user == staff
        assert submission in staff.linked_submissions.all()


@pytest.mark.django_db
class TestSubmissionAdminAddPage:
    def test_add_page_returns_200(self, admin_client):
        response = admin_client.get(reverse("admin:core_participantsubmission_add"))

        assert response.status_code == 200


CREATE_PAYLOAD = {
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
}


def make_image(name="photo.jpg"):
    buffer = BytesIO()
    Image.new("RGB", (2, 2), (10, 20, 30)).save(buffer, format="JPEG")
    return SimpleUploadedFile(name, buffer.getvalue(), content_type="image/jpeg")


def serializer_payload(serializer):
    # DRF ships no type info; .data is a ReturnDict at runtime but pyright
    # can only infer the untyped property, so pin the shape at the boundary.
    return cast("dict[str, Any]", serializer.data)


@pytest.mark.django_db
class TestAdminSerializerTrackingFields:
    def test_serializes_token_reference_and_linked_user(self, wsc):
        staff = User.objects.create_user(username="adm", password="x")
        submission = make_submission(wsc, linked_user=staff)

        data = serializer_payload(ParticipantSubmissionSerializer(submission))

        assert data["tracking_token"] == submission.tracking_token
        assert data["participant_reference"] == submission.participant_reference
        assert data["linked_user"] == staff.pk

    def test_token_and_reference_are_read_only_on_update(self, wsc):
        submission = make_submission(wsc)
        original_token = submission.tracking_token

        serializer = ParticipantSubmissionSerializer(
            submission,
            data={"tracking_token": "forged", "participant_reference": "x-9999"},
            partial=True,
        )
        assert serializer.is_valid(), serializer.errors
        serializer.save()
        submission.refresh_from_db()

        assert submission.tracking_token == original_token
        assert submission.participant_reference == (f"{wsc.slug}-{submission.pk:04d}")

    def test_linked_user_settable_by_pk_and_nullable(self, wsc):
        staff = User.objects.create_user(username="linkme", password="x")
        submission = make_submission(wsc)

        serializer = ParticipantSubmissionSerializer(
            submission, data={"linked_user": staff.pk}, partial=True
        )
        assert serializer.is_valid(), serializer.errors
        serializer.save()
        submission.refresh_from_db()
        assert submission.linked_user == staff

        serializer = ParticipantSubmissionSerializer(
            submission, data={"linked_user": None}, partial=True
        )
        assert serializer.is_valid(), serializer.errors
        serializer.save()
        submission.refresh_from_db()
        assert submission.linked_user is None


@pytest.mark.django_db
class TestCreateSerializerTrackingGuards:
    def test_admin_controlled_and_linking_fields_cannot_be_injected(self, wsc):
        staff = User.objects.create_user(username="admin2", password="x")
        payload = {
            **CREATE_PAYLOAD,
            "status": "approved",
            "admin_notes": "x",
            "linked_user": staff.pk,
        }

        serializer = ParticipantSubmissionCreateSerializer(data=payload)
        assert serializer.is_valid(), serializer.errors
        submission = serializer.save(conference=wsc)

        assert submission.status == "pending"
        assert submission.admin_notes == ""
        assert submission.linked_user is None
        assert serializer_payload(serializer)["linked_user"] is None

    def test_create_response_exposes_token_and_reference(self, wsc):
        serializer = ParticipantSubmissionCreateSerializer(data=CREATE_PAYLOAD)
        assert serializer.is_valid(), serializer.errors
        submission = serializer.save(conference=wsc)
        data = serializer_payload(serializer)

        assert data["tracking_token"] == submission.tracking_token
        assert data["participant_reference"] == submission.participant_reference


@pytest.mark.django_db
class TestTrackingReadSerializer:
    def test_payload_has_exactly_the_participant_fields(self, wsc):
        submission = make_submission(wsc)

        data = serializer_payload(ParticipantTrackingSerializer(submission))

        assert set(data) == {
            "participant_reference",
            "name",
            "email",
            "affiliation",
            "photo",
            "abstract_title",
            "abstract_text",
            "additional_authors",
            "additional_affiliations",
            "arrival_date",
            "departure_date",
            "stay_duration",
            "status",
            "submitted_at",
            "reviewed_at",
            "info",
            "is_student",
        }

    def test_payload_hides_admin_and_linking_fields(self, wsc):
        staff = User.objects.create_user(username="s", password="x")
        submission = make_submission(wsc, linked_user=staff, admin_notes="secret")

        data = serializer_payload(ParticipantTrackingSerializer(submission))

        for field in (
            "admin_notes",
            "tracking_token",
            "linked_user",
            "published_participant",
            "published_abstract",
        ):
            assert field not in data

    def test_every_field_is_read_only(self):
        serializer = ParticipantTrackingSerializer()

        assert all(field.read_only for field in serializer.fields.values())


@pytest.mark.django_db
class TestTrackingUpdateSerializer:
    @pytest.fixture(autouse=True)
    def _media_root(self, settings, tmp_path):
        settings.MEDIA_ROOT = str(tmp_path)

    def test_updates_writable_fields_on_pending_submission(self, wsc):
        submission = make_submission(wsc)
        data = {
            "name": "Jane Q. Citizen",
            "email": "jane.new@example.com",
            "affiliation": "MIT",
            "abstract_title": "New Title",
            "abstract_text": "New text",
            "additional_authors": "John Smith",
            "additional_affiliations": "Harvard",
            "arrival_date": "2026-09-11",
            "departure_date": "2026-09-13",
            "info": "Vegetarian",
            "is_student": True,
        }

        serializer = ParticipantTrackingUpdateSerializer(
            submission, data=data, partial=True
        )
        assert serializer.is_valid(), serializer.errors
        submission = serializer.save()

        submission.refresh_from_db()
        assert submission.name == "Jane Q. Citizen"
        assert submission.email == "jane.new@example.com"
        assert submission.affiliation == "MIT"
        assert submission.abstract_title == "New Title"
        assert submission.abstract_text == "New text"
        assert submission.additional_authors == "John Smith"
        assert submission.additional_affiliations == "Harvard"
        assert submission.arrival_date == date(2026, 9, 11)
        assert submission.departure_date == date(2026, 9, 13)
        assert submission.info == "Vegetarian"
        assert submission.is_student is True
        assert submission.status == "pending"
        assert submission.reviewed_at is None

    def test_ignores_admin_and_linking_input_keys(self, wsc):
        staff = User.objects.create_user(username="admin3", password="x")
        submission = make_submission(wsc)
        original_token = submission.tracking_token
        data = {
            "name": "New Name",
            "status": "approved",
            "admin_notes": "hack",
            "tracking_token": "forged",
            "linked_user": staff.pk,
            "reviewed_at": "2026-01-01T00:00:00Z",
            "submitted_at": "2026-01-01T00:00:00Z",
            "participant_reference": "x-0000",
        }

        serializer = ParticipantTrackingUpdateSerializer(
            submission, data=data, partial=True
        )
        assert serializer.is_valid(), serializer.errors
        submission = serializer.save()

        assert submission.name == "New Name"
        assert submission.status == "pending"
        assert submission.admin_notes == ""
        assert submission.tracking_token == original_token
        assert submission.linked_user is None
        assert submission.reviewed_at is None
        assert submission.participant_reference == (f"{wsc.slug}-{submission.pk:04d}")

    def test_approved_edit_reverts_to_pending_and_kills_review_timestamp(self, wsc):
        submission = make_submission(wsc)
        submission.publish()
        assert submission.status == "approved"
        assert submission.reviewed_at is not None

        serializer = ParticipantTrackingUpdateSerializer(
            submission,
            data={"abstract_text": "Participant-edited text"},
            partial=True,
        )
        assert serializer.is_valid(), serializer.errors
        submission = serializer.save()

        assert submission.abstract_text == "Participant-edited text"
        assert submission.status == "pending"
        assert submission.reviewed_at is None

    def test_approved_edit_leaves_published_rows_byte_identical(self, wsc):
        submission = make_submission(wsc)
        submission.publish()
        participant = submission.published_participant
        abstract = submission.published_abstract
        assert participant is not None
        assert abstract is not None
        participant_before = {
            field: getattr(participant, field)
            for field in ("name", "email", "affiliation")
        }
        abstract_before = {
            field: getattr(abstract, field)
            for field in ("title", "text", "authors", "department")
        }

        serializer = ParticipantTrackingUpdateSerializer(
            submission,
            data={"abstract_text": "Changed by participant"},
            partial=True,
        )
        assert serializer.is_valid(), serializer.errors
        serializer.save()

        participant.refresh_from_db()
        abstract.refresh_from_db()
        participant_after = {
            field: getattr(participant, field)
            for field in ("name", "email", "affiliation")
        }
        abstract_after = {
            field: getattr(abstract, field)
            for field in ("title", "text", "authors", "department")
        }
        assert participant_after == participant_before
        assert abstract_after == abstract_before

    def test_departure_must_be_after_arrival(self, wsc):
        submission = make_submission(wsc)

        serializer = ParticipantTrackingUpdateSerializer(
            submission, data={"departure_date": "2026-09-10"}, partial=True
        )
        assert not serializer.is_valid()
        assert "departure_date" in serializer.errors

        serializer = ParticipantTrackingUpdateSerializer(
            submission, data={"arrival_date": "2026-09-13"}, partial=True
        )
        assert not serializer.is_valid()
        assert "departure_date" in serializer.errors

    def test_absent_photo_keeps_existing_file(self, wsc):
        submission = make_submission(wsc, photo=make_image("old.jpg"))
        original_name = submission.photo.name

        serializer = ParticipantTrackingUpdateSerializer(
            submission, data={"info": "no photo change"}, partial=True
        )
        assert serializer.is_valid(), serializer.errors
        serializer.save()
        submission.refresh_from_db()

        assert submission.photo.name == original_name
        assert Path(submission.photo.path).exists()

    def test_null_photo_deletes_file_and_clears_field(self, wsc):
        submission = make_submission(wsc, photo=make_image("old.jpg"))
        old_path = submission.photo.path

        serializer = ParticipantTrackingUpdateSerializer(
            submission, data={"photo": None}, partial=True
        )
        assert serializer.is_valid(), serializer.errors
        serializer.save()
        submission.refresh_from_db()

        assert not submission.photo
        assert not Path(old_path).exists()

    def test_new_photo_replaces_and_removes_old_file(self, wsc):
        submission = make_submission(wsc, photo=make_image("old.jpg"))
        old_path = submission.photo.path

        serializer = ParticipantTrackingUpdateSerializer(
            submission, data={"photo": make_image("new.jpg")}, partial=True
        )
        assert serializer.is_valid(), serializer.errors
        serializer.save()
        submission.refresh_from_db()

        assert submission.photo.name == "submissions/photos/new.jpg"
        assert Path(submission.photo.path).exists()
        assert not Path(old_path).exists()


def make_staff_client():
    user = User.objects.create_user(username="publisher", password="pw", is_staff=True)
    token = RefreshToken.for_user(user)
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {token.access_token}")
    return client


@pytest.mark.django_db
class TestTrackingEndpoint:
    @pytest.fixture(autouse=True)
    def _media_root(self, settings, tmp_path):
        settings.MEDIA_ROOT = str(tmp_path)

    def setup_method(self):
        self.client = APIClient()

    def test_submit_returns_token_and_reference(self, wsc):
        response = self.client.post(api("submit/"), CREATE_PAYLOAD, format="json")

        assert response.status_code == 201
        body = response.json()
        assert body["tracking_token"]
        assert body["participant_reference"]

    def test_get_returns_submission_without_admin_notes(self, wsc):
        submission = make_submission(wsc, admin_notes="secret")

        response = self.client.get(api(f"track/{submission.tracking_token}/"))

        assert response.status_code == 200
        body = response.json()
        assert body["participant_reference"] == submission.participant_reference
        assert body["status"] == "pending"
        assert body["name"] == "Jane Doe"
        assert "admin_notes" not in body

    def test_cross_conference_token_404s(self, wsc, other):
        submission = make_submission(other, email="cross@example.com")

        response = self.client.get(
            api(f"track/{submission.tracking_token}/", slug=wsc.slug)
        )

        assert response.status_code == 404

    def test_fabricated_token_404s(self, wsc):
        response = self.client.get(api("track/a" * 32 + "/"))

        assert response.status_code == 404

    def test_unknown_slug_404s(self, wsc):
        submission = make_submission(wsc)

        response = self.client.get(
            api(f"track/{submission.tracking_token}/", slug="zz-no-such-conference")
        )

        assert response.status_code == 404

    def test_get_allowed_when_registration_closed(self, wsc):
        submission = make_submission(wsc)
        ConferenceInfo.objects.create(
            conference=wsc,
            registration_deadline=timezone.localdate() - timedelta(days=1),
        )

        response = self.client.get(api(f"track/{submission.tracking_token}/"))

        assert response.status_code == 200
        assert response.json()["participant_reference"] == (
            submission.participant_reference
        )

    def test_get_allowed_when_submission_edit_deadline_passed(self, wsc):
        submission = make_submission(wsc)
        ConferenceInfo.objects.create(
            conference=wsc,
            submission_edit_deadline=timezone.localdate() - timedelta(days=1),
        )

        response = self.client.get(api(f"track/{submission.tracking_token}/"))

        assert response.status_code == 200
        assert response.json()["participant_reference"] == (
            submission.participant_reference
        )

    def test_patch_pending_updates_field(self, wsc):
        submission = make_submission(wsc)

        response = self.client.patch(
            api(f"track/{submission.tracking_token}/"),
            {"affiliation": "MIT"},
            format="json",
        )

        assert response.status_code == 200
        submission.refresh_from_db()
        assert submission.affiliation == "MIT"
        assert submission.status == "pending"
        body = response.json()
        assert body["affiliation"] == "MIT"
        assert body["participant_reference"] == submission.participant_reference
        assert "admin_notes" not in body

    def test_patch_approved_reverts_to_pending_and_leaves_published_rows(self, wsc):
        submission = make_submission(wsc)
        submission.publish()
        submission.refresh_from_db()
        participant = submission.published_participant
        assert participant is not None
        assert submission.status == "approved"
        assert submission.reviewed_at is not None

        response = self.client.patch(
            api(f"track/{submission.tracking_token}/"),
            {"abstract_text": "Participant-edited text"},
            format="json",
        )

        assert response.status_code == 200
        submission.refresh_from_db()
        assert submission.abstract_text == "Participant-edited text"
        assert submission.status == "pending"
        assert submission.reviewed_at is None
        participant.refresh_from_db()
        assert participant.name == "Jane Doe"

    def test_patch_allowed_when_registration_closed_and_no_edit_deadline(self, wsc):
        submission = make_submission(wsc)
        ConferenceInfo.objects.create(
            conference=wsc,
            registration_deadline=timezone.localdate() - timedelta(days=1),
        )

        response = self.client.patch(
            api(f"track/{submission.tracking_token}/"),
            {"affiliation": "MIT"},
            format="json",
        )

        assert response.status_code == 200
        submission.refresh_from_db()
        assert submission.affiliation == "MIT"

    def test_patch_rejected_when_submission_edit_deadline_passed(self, wsc):
        submission = make_submission(wsc)
        ConferenceInfo.objects.create(
            conference=wsc,
            registration_deadline=timezone.localdate() + timedelta(days=30),
            submission_edit_deadline=timezone.localdate() - timedelta(days=1),
        )

        response = self.client.patch(
            api(f"track/{submission.tracking_token}/"),
            {"affiliation": "MIT"},
            format="json",
        )

        assert response.status_code == 400
        assert response.json()["detail"] == (
            "Editing submissions is not open for this conference."
        )
        submission.refresh_from_db()
        assert submission.affiliation == "CTU"

    def test_patch_allowed_when_registration_closed_but_edit_window_open(self, wsc):
        submission = make_submission(wsc)
        ConferenceInfo.objects.create(
            conference=wsc,
            registration_deadline=timezone.localdate() - timedelta(days=1),
            submission_edit_deadline=timezone.localdate() + timedelta(days=30),
        )

        response = self.client.patch(
            api(f"track/{submission.tracking_token}/"),
            {"affiliation": "MIT"},
            format="json",
        )

        assert response.status_code == 200
        submission.refresh_from_db()
        assert submission.affiliation == "MIT"

    def test_patch_rejected_when_conference_ended_without_edit_deadline(self, wsc):
        submission = make_submission(wsc)
        ConferenceInfo.objects.create(
            conference=wsc,
            date_end=timezone.localdate() - timedelta(days=1),
            registration_deadline=timezone.localdate() + timedelta(days=30),
        )

        response = self.client.patch(
            api(f"track/{submission.tracking_token}/"),
            {"affiliation": "MIT"},
            format="json",
        )

        assert response.status_code == 400
        assert response.json()["detail"] == (
            "Editing submissions is not open for this conference."
        )
        submission.refresh_from_db()
        assert submission.affiliation == "CTU"

    def test_patch_allowed_on_conference_end_day(self, wsc):
        submission = make_submission(wsc)
        ConferenceInfo.objects.create(
            conference=wsc,
            date_end=timezone.localdate(),
            registration_deadline=timezone.localdate() + timedelta(days=30),
        )

        response = self.client.patch(
            api(f"track/{submission.tracking_token}/"),
            {"affiliation": "MIT"},
            format="json",
        )

        assert response.status_code == 200
        submission.refresh_from_db()
        assert submission.affiliation == "MIT"

    def test_patch_rejected_when_no_edit_deadline_and_conference_started(self, wsc):
        submission = make_submission(wsc)
        ConferenceInfo.objects.create(
            conference=wsc,
            date_start=timezone.localdate(),
            registration_deadline=timezone.localdate() + timedelta(days=30),
        )

        response = self.client.patch(
            api(f"track/{submission.tracking_token}/"),
            {"affiliation": "MIT"},
            format="json",
        )

        assert response.status_code == 400
        assert response.json()["detail"] == (
            "Editing submissions is not open for this conference."
        )
        submission.refresh_from_db()
        assert submission.affiliation == "CTU"

    def test_patch_allowed_when_no_edit_deadline_and_conference_not_started(self, wsc):
        submission = make_submission(wsc)
        ConferenceInfo.objects.create(
            conference=wsc,
            date_start=timezone.localdate() + timedelta(days=30),
            registration_deadline=timezone.localdate() + timedelta(days=30),
        )

        response = self.client.patch(
            api(f"track/{submission.tracking_token}/"),
            {"affiliation": "MIT"},
            format="json",
        )

        assert response.status_code == 200
        submission.refresh_from_db()
        assert submission.affiliation == "MIT"

    def test_patch_ignores_injected_admin_fields(self, wsc):
        submission = make_submission(wsc)

        response = self.client.patch(
            api(f"track/{submission.tracking_token}/"),
            {"name": "New Name", "status": "approved", "admin_notes": "hack"},
            format="json",
        )

        assert response.status_code == 200
        submission.refresh_from_db()
        assert submission.name == "New Name"
        assert submission.status == "pending"
        assert submission.admin_notes == ""

    def test_patch_multipart_photo_replaces_file(self, wsc):
        submission = make_submission(wsc, photo=make_image("old.jpg"))
        old_path = submission.photo.path

        response = self.client.patch(
            api(f"track/{submission.tracking_token}/"),
            {"photo": make_image("new.jpg")},
            format="multipart",
        )

        assert response.status_code == 200
        submission.refresh_from_db()
        assert submission.photo.name == "submissions/photos/new.jpg"
        assert Path(submission.photo.path).exists()
        assert not Path(old_path).exists()

    def test_republish_syncs_participant_edits(self, wsc):
        submission = make_submission(wsc)
        submission.publish()
        submission.refresh_from_db()
        participant = submission.published_participant
        assert participant is not None
        assert participant.name == "Jane Doe"

        response = self.client.patch(
            api(f"track/{submission.tracking_token}/"),
            {
                "name": "Edited Name",
                "affiliation": "Edited Affil",
                "email": "edited@example.com",
            },
            format="json",
        )
        assert response.status_code == 200
        submission.refresh_from_db()
        assert submission.status == "pending"

        publish = make_staff_client().post(
            api(f"admin/submissions/{submission.pk}/publish/")
        )
        assert publish.status_code == 200

        participant.refresh_from_db()
        assert participant.name == "Edited Name"
        assert participant.affiliation == "Edited Affil"
        assert participant.email == "edited@example.com"

    def test_conference_info_payload_exposes_submission_edit_deadline(self, wsc):
        staff = make_staff_client()
        response = staff.patch(
            api("conference-info/edit/"),
            {"submission_edit_deadline": "2026-08-31"},
            format="json",
        )
        assert response.status_code == 200

        response = self.client.get(api("conference-info/"))

        assert response.status_code == 200
        assert response.json()["submission_edit_deadline"] == "2026-08-31"
