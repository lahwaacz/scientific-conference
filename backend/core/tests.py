from datetime import date

from django.contrib import admin as django_admin
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.test import RequestFactory, TestCase
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from .admin import ParticipantSubmissionAdmin
from .conftest import api
from .models import (
    Abstract,
    Conference,
    Participant,
    ParticipantSubmission,
    Talk,
)
from .serializers import ParticipantSubmissionSerializer


def wsc_conference(**fields):
    conference, _ = Conference.objects.get_or_create(slug="wsc2026-test")
    if fields:
        for name, value in fields.items():
            setattr(conference, name, value)
        conference.save()
    return conference


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

    def make_legacy_talk(self, conference):
        return ParticipantSubmission.objects.create(
            conference=conference,
            name="Carol White",
            email="carol@example.com",
            affiliation="CTU",
            abstract_title="Finite Elements",
            abstract_text="Short abstract",
            arrival_date=date(2027, 5, 10),
            departure_date=date(2027, 5, 10),
            stay_dates_derived=True,
        )

    def test_full_clean_rejects_change_to_disallowed_contribution_type(self):
        conference = wsc_conference(
            date_start=date(2027, 5, 10),
            date_end=date(2027, 5, 10),
            registration_allow_poster=False,
        )
        submission = self.make_legacy_talk(conference)
        submission.contribution_type = "poster"
        submission.abstract_title = "A poster"

        with self.assertRaises(ValidationError) as caught:
            submission.full_clean()

        self.assertIn("contribution_type", caught.exception.message_dict)

    def test_full_clean_allows_unchanged_legacy_contribution_type(self):
        conference = wsc_conference(
            date_start=date(2027, 5, 10), date_end=date(2027, 5, 10)
        )
        submission = self.make_legacy_talk(conference)
        conference.registration_allow_talk = False
        conference.registration_allow_poster = False
        conference.save(
            update_fields=["registration_allow_talk", "registration_allow_poster"]
        )
        submission.info = "Vegetarian"

        submission.full_clean()

        self.assertEqual(submission.contribution_type, "talk")


class TestParticipantSubmissionSerializer(TestCase):
    def setUp(self):
        self.conference = wsc_conference()

    def make_submission(self, **overrides):
        values = {
            "conference": self.conference,
            "name": "Carol White",
            "email": "carol@example.com",
            "affiliation": "CTU",
            "abstract_title": "Finite Elements",
            "abstract_text": "Short abstract",
            "arrival_date": date(2027, 5, 10),
            "departure_date": date(2027, 5, 12),
            "stay_dates_derived": True,
        }
        values.update(overrides)
        return ParticipantSubmission.objects.create(**values)

    def update_serializer(self, submission, data):
        return ParticipantSubmissionSerializer(
            submission,
            data=data,
            partial=True,
            context={"conference": self.conference},
        )

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

        serializer = ParticipantSubmissionSerializer(
            data=data, context={"conference": self.conference}
        )
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

        serializer = ParticipantSubmissionSerializer(
            data=data, context={"conference": self.conference}
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)

    def test_admin_payload_has_exact_fields(self):
        submission = self.make_submission()

        data = ParticipantSubmissionSerializer(submission).data

        self.assertEqual(
            list(data),
            [
                "id",
                "name",
                "email",
                "affiliation",
                "photo",
                "contribution_type",
                "abstract_title",
                "abstract_text",
                "additional_authors",
                "additional_affiliations",
                "arrival_date",
                "departure_date",
                "stay_duration",
                "stay_dates_derived",
                "status",
                "submitted_at",
                "reviewed_at",
                "rejection_message",
                "admin_notes",
                "published_participant",
                "published_abstract",
                "info",
                "is_student",
                "tracking_token",
                "participant_reference",
                "linked_user",
            ],
        )

    def test_admin_can_override_dates_and_clear_provenance_when_collection_is_off(self):
        self.conference.registration_collect_dates = False
        self.conference.save()
        submission = self.make_submission()
        serializer = self.update_serializer(
            submission,
            {"arrival_date": "2027-06-01", "departure_date": "2027-06-03"},
        )

        self.assertTrue(serializer.is_valid(), serializer.errors)
        updated = serializer.save()

        self.assertEqual(updated.arrival_date, date(2027, 6, 1))
        self.assertEqual(updated.departure_date, date(2027, 6, 3))
        self.assertFalse(updated.stay_dates_derived)

    def test_admin_preserves_provenance_when_supplied_dates_are_unchanged(self):
        self.conference.registration_collect_dates = False
        self.conference.save()
        submission = self.make_submission()
        serializer = self.update_serializer(
            submission,
            {"arrival_date": "2027-05-10", "departure_date": "2027-05-12", "info": "x"},
        )

        self.assertTrue(serializer.is_valid(), serializer.errors)
        updated = serializer.save()

        self.assertTrue(updated.stay_dates_derived)

    def test_admin_allows_equal_dates_only_when_collection_is_off(self):
        submission = self.make_submission(departure_date=date(2027, 5, 10))

        off = self.update_serializer(
            submission,
            {"arrival_date": "2027-05-10", "departure_date": "2027-05-10"},
        )
        self.assertFalse(off.is_valid())
        self.assertIn("departure_date", off.errors)

        self.conference.registration_collect_dates = False
        self.conference.save()
        off = self.update_serializer(
            submission,
            {"arrival_date": "2027-05-11", "departure_date": "2027-05-11"},
        )
        self.assertTrue(off.is_valid(), off.errors)
        updated = off.save()
        self.assertEqual(updated.arrival_date, updated.departure_date)
        self.assertFalse(updated.stay_dates_derived)

    def test_admin_rejects_inverted_dates_when_collection_is_off(self):
        self.conference.registration_collect_dates = False
        self.conference.save()
        submission = self.make_submission()
        serializer = self.update_serializer(
            submission,
            {"arrival_date": "2027-06-03", "departure_date": "2027-06-01"},
        )

        self.assertFalse(serializer.is_valid())
        self.assertIn("departure_date", serializer.errors)

    def test_admin_clears_attend_fields_and_validates_supplied_affiliation(self):
        submission = self.make_submission(
            contribution_type="attend", abstract_title="", abstract_text=""
        )
        serializer = self.update_serializer(
            submission,
            {
                "abstract_title": "Injected",
                "abstract_text": "Injected",
                "additional_authors": "Injected",
                "additional_affiliations": "Injected",
            },
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)
        updated = serializer.save()
        for field in (
            "abstract_title",
            "abstract_text",
            "additional_authors",
            "additional_affiliations",
        ):
            self.assertEqual(getattr(updated, field), "")

        serializer = self.update_serializer(submission, {"affiliation": "CU"})
        self.assertFalse(serializer.is_valid())
        self.assertIn("affiliation", serializer.errors)

    def test_admin_notes_remain_writable(self):
        submission = self.make_submission()
        serializer = self.update_serializer(submission, {"admin_notes": "Check visa"})

        self.assertTrue(serializer.is_valid(), serializer.errors)
        self.assertEqual(serializer.save().admin_notes, "Check visa")


class TestParticipantSubmissionAdminForm(TestCase):
    def setUp(self):
        self.admin_user = User.objects.create_superuser(
            username="form-admin", email="form-admin@example.com", password="pw"
        )
        self.conference = wsc_conference(
            date_start=date(2027, 5, 10), date_end=date(2027, 5, 10)
        )
        self.submission = ParticipantSubmission.objects.create(
            conference=self.conference,
            name="Carol White",
            email="carol@example.com",
            affiliation="CTU",
            abstract_title="Finite Elements",
            abstract_text="Short abstract",
            arrival_date=date(2027, 5, 10),
            departure_date=date(2027, 5, 10),
            stay_dates_derived=True,
        )

    def form_for(self, **overrides):
        data = {
            "conference": self.conference.pk,
            "name": self.submission.name,
            "email": self.submission.email,
            "affiliation": self.submission.affiliation,
            "contribution_type": self.submission.contribution_type,
            "abstract_title": self.submission.abstract_title,
            "abstract_text": self.submission.abstract_text,
            "additional_authors": self.submission.additional_authors,
            "additional_affiliations": self.submission.additional_affiliations,
            "arrival_date": self.submission.arrival_date,
            "departure_date": self.submission.departure_date,
            "status": self.submission.status,
            "rejection_message": "",
            "admin_notes": "",
            "info": "",
        }
        data.update(overrides)
        model_admin = ParticipantSubmissionAdmin(
            ParticipantSubmission, django_admin.site
        )
        request = RequestFactory().get("/")
        request.user = self.admin_user
        form_class = model_admin.get_form(request, obj=self.submission, change=True)
        return form_class(data=data, instance=self.submission)

    def test_change_to_disallowed_contribution_type_is_rejected(self):
        self.conference.registration_allow_poster = False
        self.conference.save(update_fields=["registration_allow_poster"])
        form = self.form_for(contribution_type="poster", abstract_title="A poster")

        self.assertFalse(form.is_valid())
        self.assertIn("contribution_type", form.errors)

    def test_unchanged_allowed_contribution_type_is_valid(self):
        self.conference.registration_allow_poster = False
        self.conference.save(update_fields=["registration_allow_poster"])
        form = self.form_for(info="Vegetarian")

        self.assertTrue(form.is_valid(), form.errors)

    def test_unchanged_legacy_disallowed_contribution_type_is_valid(self):
        self.conference.registration_allow_talk = False
        self.conference.registration_allow_poster = False
        self.conference.save(
            update_fields=["registration_allow_talk", "registration_allow_poster"]
        )
        form = self.form_for(info="Vegetarian")

        self.assertTrue(form.is_valid(), form.errors)

    def test_changed_equal_dates_are_rejected_when_collection_is_on(self):
        form = self.form_for(
            arrival_date=date(2027, 5, 11), departure_date=date(2027, 5, 11)
        )

        self.assertFalse(form.is_valid())
        self.assertIn("departure_date", form.errors)

    def test_unchanged_legacy_equal_dates_allow_unrelated_edit(self):
        form = self.form_for(info="Vegetarian")

        self.assertTrue(form.is_valid(), form.errors)
        updated = form.save()
        self.assertEqual(updated.info, "Vegetarian")
        self.assertTrue(updated.stay_dates_derived)

    def test_equal_date_override_clears_provenance_when_collection_is_off(self):
        self.conference.registration_collect_dates = False
        self.conference.save()
        form = self.form_for(
            arrival_date=date(2027, 5, 11), departure_date=date(2027, 5, 11)
        )

        self.assertTrue(form.is_valid(), form.errors)
        updated = form.save()
        self.assertEqual(updated.arrival_date, updated.departure_date)
        self.assertFalse(updated.stay_dates_derived)

    def test_inverted_dates_are_always_rejected(self):
        self.conference.registration_collect_dates = False
        self.conference.save()
        form = self.form_for(
            arrival_date=date(2027, 5, 12), departure_date=date(2027, 5, 10)
        )

        self.assertFalse(form.is_valid())
        self.assertIn("departure_date", form.errors)


class TestRegistrationWindow(TestCase):
    def info_with(self, **kwargs):
        return wsc_conference(**kwargs)

    def test_open_when_no_bounds(self):
        info = self.info_with()
        self.assertTrue(info.is_registration_open(date(2026, 1, 1)))

    def test_closed_before_opening(self):
        info = self.info_with(registration_opening=date(2026, 5, 1))
        self.assertFalse(info.is_registration_open(date(2026, 4, 30)))
        self.assertTrue(info.is_registration_open(date(2026, 5, 1)))

    def test_closed_after_deadline(self):
        info = self.info_with(registration_deadline=date(2026, 5, 1))
        self.assertTrue(info.is_registration_open(date(2026, 5, 1)))
        self.assertFalse(info.is_registration_open(date(2026, 5, 2)))

    def test_open_only_inside_window(self):
        info = self.info_with(
            registration_opening=date(2026, 5, 1),
            registration_deadline=date(2026, 5, 31),
        )
        self.assertFalse(info.is_registration_open(date(2026, 4, 30)))
        self.assertTrue(info.is_registration_open(date(2026, 5, 15)))
        self.assertFalse(info.is_registration_open(date(2026, 6, 1)))

    def test_past_conference_is_closed_without_deadline(self):
        info = self.info_with(date_end=date(2026, 5, 31))
        self.assertTrue(info.is_registration_open(date(2026, 5, 31)))
        self.assertFalse(info.is_registration_open(date(2026, 6, 1)))

    def test_past_conference_stays_closed_even_with_future_deadline(self):
        info = self.info_with(
            date_end=date(2026, 5, 31),
            registration_deadline=date(2030, 1, 1),
        )
        self.assertFalse(info.is_registration_open(date(2026, 6, 1)))

    def test_unended_conference_without_dates_is_open(self):
        info = self.info_with(date_end=date(2026, 12, 31))
        self.assertTrue(info.is_registration_open(date(2026, 6, 1)))


class TestSubmissionEditWindow(TestCase):
    def info_with(self, **kwargs):
        return wsc_conference(**kwargs)

    def test_open_when_no_deadline_and_no_start_date(self):
        info = self.info_with()
        self.assertTrue(info.is_submission_edit_open(date(2099, 1, 1)))

    def test_open_before_deadline(self):
        info = self.info_with(submission_edit_deadline=date(2026, 5, 1))
        self.assertTrue(info.is_submission_edit_open(date(2026, 4, 30)))

    def test_open_on_deadline_day(self):
        info = self.info_with(submission_edit_deadline=date(2026, 5, 1))
        self.assertTrue(info.is_submission_edit_open(date(2026, 5, 1)))

    def test_closed_after_deadline(self):
        info = self.info_with(submission_edit_deadline=date(2026, 5, 1))
        self.assertFalse(info.is_submission_edit_open(date(2026, 5, 2)))

    def test_open_day_before_conference_start(self):
        info = self.info_with(date_start=date(2026, 5, 10))
        self.assertTrue(info.is_submission_edit_open(date(2026, 5, 9)))

    def test_closed_on_conference_start_day(self):
        info = self.info_with(date_start=date(2026, 5, 10))
        self.assertFalse(info.is_submission_edit_open(date(2026, 5, 10)))

    def test_closed_after_conference_start(self):
        info = self.info_with(date_start=date(2026, 5, 10))
        self.assertFalse(info.is_submission_edit_open(date(2026, 5, 11)))

    def test_explicit_deadline_overrides_start_date(self):
        info = self.info_with(
            date_start=date(2026, 5, 10),
            submission_edit_deadline=date(2026, 6, 1),
        )
        self.assertTrue(info.is_submission_edit_open(date(2026, 6, 1)))
        self.assertFalse(info.is_submission_edit_open(date(2026, 6, 2)))

    def test_open_even_when_registration_deadline_passed(self):
        info = self.info_with(registration_deadline=date(2026, 5, 1))
        self.assertFalse(info.is_registration_open(date(2026, 6, 1)))
        self.assertTrue(info.is_submission_edit_open(date(2026, 6, 1)))

    def test_closed_when_conference_started_without_edit_deadline(self):
        info = self.info_with(
            date_start=date(2026, 5, 10),
            date_end=date(2026, 5, 14),
        )
        self.assertFalse(info.is_registration_open(date(2026, 5, 17)))
        self.assertFalse(info.is_submission_edit_open(date(2026, 5, 17)))

    def test_open_on_conference_end_day_closed_the_day_after(self):
        info = self.info_with(date_end=date(2026, 5, 31))
        self.assertTrue(info.is_submission_edit_open(date(2026, 5, 31)))
        self.assertFalse(info.is_submission_edit_open(date(2026, 6, 1)))

    def test_date_end_caps_a_later_explicit_deadline(self):
        # Defensive: date_end wins even if data bypasses validation.
        info = self.info_with(
            date_end=date(2026, 5, 31),
            submission_edit_deadline=date(2026, 6, 30),
        )
        self.assertFalse(info.is_submission_edit_open(date(2026, 6, 1)))


class TestSubmissionAPI(APITestCase):
    def setUp(self):
        self.conference = wsc_conference()

    def post_submission(self, **overrides):
        data = {
            "name": "Window Tester",
            "email": "window@example.com",
            "affiliation": "CTU",
            "abstract_title": "Windows",
            "abstract_text": "A short abstract",
            "additional_authors": "",
            "additional_affiliations": "",
            "arrival_date": "2026-09-10",
            "departure_date": "2026-09-12",
            "info": "",
            "is_student": False,
        }
        for name, value in overrides.items():
            if value is None:
                data.pop(name, None)
            else:
                data[name] = value
        return self.client.post(api("submit/"), data, format="json")

    def configure_dates(self, collect, start, end):
        self.conference.registration_collect_dates = collect
        self.conference.date_start = start
        self.conference.date_end = end
        self.conference.save()

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
        # self-declared on the public registration form (badge/list display)
        self.assertTrue(created.is_student)

    def test_create_submission_ignores_admin_controlled_fields(self):
        wsc_conference()
        url = api("submit/")
        data = {
            "name": "Mallory Doe",
            "email": "mallory@example.com",
            "affiliation": "Evil Corp",
            "abstract_title": "Pre-approved talk",
            "abstract_text": "A short abstract",
            "additional_authors": "",
            "additional_affiliations": "",
            "arrival_date": "2026-09-10",
            "departure_date": "2026-09-12",
            "info": "",
            "is_student": False,
            "status": "approved",
            "admin_notes": "injected by anonymous poster",
        }

        response = self.client.post(url, data, format="json")

        self.assertEqual(response.status_code, 201)
        created = ParticipantSubmission.objects.first()
        assert created is not None
        self.assertEqual(created.status, "pending")
        self.assertEqual(created.admin_notes, "")
        self.assertEqual(response.data["status"], "pending")
        self.assertEqual(response.data["admin_notes"], "")

    def test_submission_rejected_before_registration_opens(self):
        wsc_conference(registration_opening=date(2030, 1, 1))

        response = self.post_submission()

        self.assertEqual(response.status_code, 400)
        self.assertEqual(ParticipantSubmission.objects.count(), 0)

    def test_submission_rejected_after_deadline(self):
        wsc_conference(registration_deadline=date(2020, 1, 1))

        response = self.post_submission()

        self.assertEqual(response.status_code, 400)
        self.assertEqual(ParticipantSubmission.objects.count(), 0)

    def test_submission_allowed_inside_window(self):
        wsc_conference(
            registration_opening=date(2020, 1, 1),
            registration_deadline=date(2030, 1, 1),
        )

        response = self.post_submission()

        self.assertEqual(response.status_code, 201)
        self.assertEqual(ParticipantSubmission.objects.count(), 1)

    def test_dates_off_create_derives_omitted_dates(self):
        self.configure_dates(False, date(2027, 5, 10), date(2027, 5, 12))
        response = self.post_submission(arrival_date=None, departure_date=None)

        self.assertEqual(response.status_code, 201, response.data)
        created = ParticipantSubmission.objects.get()
        self.assertEqual(created.arrival_date, date(2027, 5, 10))
        self.assertEqual(created.departure_date, date(2027, 5, 12))
        self.assertTrue(created.stay_dates_derived)

    def test_dates_off_create_ignores_injected_and_malformed_dates(self):
        self.configure_dates(False, date(2027, 5, 10), date(2027, 5, 12))
        for arrival, departure in (
            ("2027-06-01", "2027-06-03"),
            ("not-a-date", "also-not-a-date"),
        ):
            with self.subTest(arrival=arrival, departure=departure):
                response = self.post_submission(
                    arrival_date=arrival,
                    departure_date=departure,
                    email=f"{arrival}@example.com",
                )
                self.assertEqual(response.status_code, 201, response.data)
                created = ParticipantSubmission.objects.latest("pk")
                self.assertEqual(created.arrival_date, date(2027, 5, 10))
                self.assertEqual(created.departure_date, date(2027, 5, 12))
                self.assertTrue(created.stay_dates_derived)

    def test_dates_off_single_day_create_uses_equal_derived_dates(self):
        self.configure_dates(False, date(2027, 5, 10), date(2027, 5, 10))
        response = self.post_submission()
        response.render()

        self.assertEqual(response.status_code, 201, response.content)
        created = ParticipantSubmission.objects.get()
        self.assertEqual(created.arrival_date, date(2027, 5, 10))
        self.assertEqual(created.departure_date, date(2027, 5, 10))
        self.assertTrue(created.stay_dates_derived)

    def test_dates_on_create_requires_both_dates_as_field_errors(self):
        self.configure_dates(True, date(2027, 5, 10), date(2027, 5, 12))
        response = self.post_submission(arrival_date=None, departure_date=None)

        self.assertEqual(response.status_code, 400)
        self.assertIn("arrival_date", response.data)
        self.assertIn("departure_date", response.data)
        self.assertEqual(ParticipantSubmission.objects.count(), 0)

    def test_dates_on_create_rejects_equal_dates(self):
        response = self.post_submission(
            arrival_date="2027-05-10", departure_date="2027-05-10"
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("departure_date", response.data)

    def test_dates_on_create_rejects_inverted_dates(self):
        response = self.post_submission(
            arrival_date="2027-05-12", departure_date="2027-05-10"
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("departure_date", response.data)

    def test_public_create_clears_attend_contribution_fields(self):
        response = self.post_submission(
            contribution_type="attend",
            abstract_title="Injected title",
            abstract_text="Injected abstract",
            additional_authors="Injected authors",
            additional_affiliations="Injected affiliations",
        )

        self.assertEqual(response.status_code, 201, response.data)
        created = ParticipantSubmission.objects.get()
        for field in (
            "abstract_title",
            "abstract_text",
            "additional_authors",
            "additional_affiliations",
        ):
            self.assertEqual(getattr(created, field), "")

    def test_public_create_requires_three_affiliation_characters(self):
        response = self.post_submission(affiliation="CU")

        self.assertEqual(response.status_code, 400)
        self.assertIn("affiliation", response.data)

    def test_public_create_rejects_abstract_over_250_words(self):
        response = self.post_submission(abstract_text=" ".join(["word"] * 251))

        self.assertEqual(response.status_code, 400)
        self.assertIn("abstract_text", response.data)

    def test_public_create_accepts_abstract_with_exactly_250_words(self):
        response = self.post_submission(abstract_text=" ".join(["word"] * 250))

        self.assertEqual(response.status_code, 201, response.data)

    def test_public_create_does_not_expose_provenance_override(self):
        response = self.post_submission(stay_dates_derived=True)

        self.assertEqual(response.status_code, 201, response.data)
        created = ParticipantSubmission.objects.get()
        self.assertFalse(created.stay_dates_derived)
        self.assertFalse(response.data["stay_dates_derived"])


class TestPublishSubmissionAPI(APITestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            username="admin",
            password="adminpass",
            is_staff=True,
            is_superuser=True,
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

    def test_admin_edit_endpoint_ignores_status_and_sets_admin_notes(self):
        url = api(f"admin/submissions/{self.submission.id}/")
        response = self.client.patch(
            url,
            {"status": "approved", "admin_notes": "verified by phone"},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.submission.refresh_from_db()
        self.assertEqual(self.submission.status, "pending")
        self.assertEqual(self.submission.admin_notes, "verified by phone")

    def test_publish_endpoint_rejects_non_staff(self):
        self.client.credentials()
        url = api(f"admin/submissions/{self.submission.id}/publish/")
        response = self.client.post(url)

        self.assertIn(response.status_code, [401, 403])
