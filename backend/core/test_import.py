"""CSV import of pre-registered participants.

Pins the generalized import engine (field-name matching, manual mapping,
delimiter/encoding handling, date defaults, duplicate detection, typed payloads)
and the Django-admin upload -> preview -> map -> confirm wizard.
"""

from datetime import date
from unittest import mock

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse

from .admin import MAX_UPLOAD_BYTES
from .importing import (
    IMPORTABLE_FIELDS,
    STATUS_ERROR,
    STATUS_OK,
    STATUS_WARNING,
    ImportFileError,
    create_submissions,
    decode_csv_bytes,
    parse_csv,
    resolve_date_defaults,
    resolve_mapping,
    validate_rows,
)
from .models import Conference, ConferenceInfo, Participant, ParticipantSubmission

IMPORT_URL_NAME = "admin:core_participantsubmission_import"

# A title column whose header contains a comma must be quoted in a comma CSV.
CSV_TITLE = (
    'Name,Email,"Topic / Title (Tentative, for all now)"\n'
    "Jan Novák,jan@example.com,Quantum Fields\n"
)
CSV_PLAIN = "Name,Email,Affiliation\nJan Novák,jan@example.com,CTU\n"


def make_conference(slug="import-conf", start=None, end=None):
    conference = Conference.objects.create(slug=slug)
    ConferenceInfo.objects.create(conference=conference, date_start=start, date_end=end)
    return conference


def evaluate(text, conference, manual=None):
    parsed = parse_csv(text)
    mapping = resolve_mapping(parsed.headers, manual)
    defaults = resolve_date_defaults(conference, mapping)
    return validate_rows(parsed, mapping, conference, defaults)


class ImportableFieldsTests(TestCase):
    def test_exposes_model_fields_but_not_managed_ones(self):
        names = {name for name, _ in IMPORTABLE_FIELDS}
        self.assertIn("name", names)
        self.assertIn("abstract_title", names)
        self.assertIn("is_student", names)
        self.assertIn("admin_notes", names)
        self.assertNotIn("photo", names)
        self.assertNotIn("status", names)
        self.assertNotIn("tracking_token", names)


class MappingTests(TestCase):
    def test_header_matches_field_name_ignoring_case_and_spaces(self):
        mapping = resolve_mapping(["Name", "Email", "Abstract Title"])
        self.assertEqual(
            mapping.field_to_indices,
            {"name": [0], "email": [1], "abstract_title": [2]},
        )
        self.assertEqual(mapping.configurable, [])
        self.assertEqual(
            mapping.recognized,
            [
                ("Name", "Name"),
                ("Email", "Email"),
                ("Abstract Title", "Abstract title"),
            ],
        )

    def test_unmatched_column_is_configurable(self):
        headers = ["Name", "Email", "Topic / Title (Tentative, for all now)"]
        mapping = resolve_mapping(headers)
        self.assertEqual(mapping.configurable, [(2, headers[2], "")])
        self.assertEqual(mapping.conflicts, [])

    def test_manual_mapping_assigns_a_field(self):
        headers = ["Name", "Email", "Topic"]
        mapping = resolve_mapping(headers, {2: "abstract_title"})
        self.assertEqual(mapping.field_to_indices["abstract_title"], [2])
        self.assertEqual(mapping.configurable, [(2, "Topic", "abstract_title")])

    def test_second_column_for_a_non_mergeable_field_is_a_conflict(self):
        mapping = resolve_mapping(["Name", "Email", "Abstract Title"], {2: "email"})
        self.assertEqual(mapping.field_to_indices["email"], [1])
        self.assertEqual(mapping.conflicts, [(2, "Abstract Title")])

    def test_columns_merging_into_admin_notes_do_not_conflict(self):
        headers = ["Name", "Email", "Notes", "Participation"]
        mapping = resolve_mapping(headers, {2: "admin_notes", 3: "admin_notes"})
        self.assertEqual(mapping.field_to_indices["admin_notes"], [2, 3])
        self.assertEqual(mapping.conflicts, [])

    def test_conflicting_auto_matched_column_stays_configurable(self):
        mapping = resolve_mapping(["Email", "E Mail"])
        self.assertEqual(mapping.field_to_indices["email"], [0])
        self.assertEqual(mapping.conflicts, [(1, "E Mail")])
        self.assertIn((1, "E Mail", "email"), mapping.configurable)


class ParsingTests(TestCase):
    def test_unknown_column_does_not_break_parsing(self):
        parsed = parse_csv(CSV_TITLE)
        self.assertEqual(len(parsed.records), 1)
        self.assertEqual(parsed.headers[2], "Topic / Title (Tentative, for all now)")

    def test_empty_file_raises(self):
        with self.assertRaises(ImportFileError):
            parse_csv("")

    def test_header_without_rows_raises(self):
        with self.assertRaises(ImportFileError):
            parse_csv("Name,Email\n")

    def test_blank_lines_are_skipped(self):
        parsed = parse_csv("Name,Email\n\nJan,jan@example.com\n,\n")
        self.assertEqual(len(parsed.records), 1)

    def test_semicolon_delimiter_detected(self):
        parsed = parse_csv("Name;Email\nJan;jan@example.com\n")
        self.assertEqual(parsed.records[0][1], "jan@example.com")

    def test_tab_delimiter_detected(self):
        parsed = parse_csv("Name\tEmail\nJan\tjan@example.com\n")
        self.assertEqual(parsed.records[0][1], "jan@example.com")

    def test_quoted_commas_do_not_flip_semicolon_detection(self):
        parsed = parse_csv('Name;Email;"a,b,c,d"\nJan;jan@example.com;x\n')
        self.assertEqual(parsed.headers, ["Name", "Email", "a,b,c,d"])
        self.assertEqual(parsed.records[0], ["Jan", "jan@example.com", "x"])

    def test_decode_utf8_bom(self):
        self.assertEqual(
            decode_csv_bytes("Name\nJan\n".encode("utf-8-sig")), "Name\nJan\n"
        )

    def test_decode_czech_windows_1250(self):
        self.assertEqual(
            decode_csv_bytes("Jméno\nJan Novák\n".encode("cp1250")),
            "Jméno\nJan Novák\n",
        )

    def test_decode_latin1_fallback_for_cp1250_invalid_byte(self):
        self.assertEqual(decode_csv_bytes(b"\x81"), "\x81")

    def test_row_cap_is_enforced(self):
        text = "Name,Email\na,a@example.com\nb,b@example.com\nc,c@example.com\n"
        with (
            mock.patch("core.importing.MAX_ROWS", 2),
            self.assertRaises(ImportFileError),
        ):
            parse_csv(text)

    def test_physical_line_number_is_used_for_multiline_fields(self):
        parsed = parse_csv(
            'Name,Email,Notes\nJan,jan@example.com,"line one\nline two"\n'
            "Bob,bob@example.com,x\n"
        )
        self.assertEqual(parsed.line_numbers, [3, 4])


class ValidationTests(TestCase):
    def setUp(self):
        self.conf = make_conference(start=date(2027, 5, 1), end=date(2027, 5, 3))
        self.defaults = resolve_date_defaults(self.conf, resolve_mapping(["Name"]))

    def test_valid_row_is_ok(self):
        results = evaluate(CSV_PLAIN, self.conf)
        self.assertEqual(results[0].status, STATUS_OK)
        self.assertTrue(results[0].will_import)

    def test_missing_name_is_error(self):
        results = evaluate("Name,Email\n,jan@example.com\n", self.conf)
        self.assertEqual(results[0].status, STATUS_ERROR)

    def test_invalid_email_is_error(self):
        results = evaluate("Name,Email\nJan,not-an-email\n", self.conf)
        self.assertEqual(results[0].status, STATUS_ERROR)

    def test_is_student_is_parsed(self):
        results = evaluate(
            "Name,Email,Is Student\nJan,jan@example.com,Yes\n", self.conf
        )
        self.assertIs(results[0].payload["is_student"], True)

    def test_length_error_names_the_column(self):
        long_name = "x" * 300
        results = evaluate(f"Name,Email\n{long_name},jan@example.com\n", self.conf)
        self.assertEqual(results[0].status, STATUS_ERROR)
        self.assertTrue(any("Name is longer" in m for m in results[0].messages))

    def test_date_columns_override_the_conference_defaults(self):
        text = (
            "Name,Email,Arrival Date,Departure Date\n"
            "Jan,jan@example.com,2027-06-01,2027-06-05\n"
        )
        results = evaluate(text, self.conf)
        self.assertEqual(results[0].payload["arrival_date"], date(2027, 6, 1))
        self.assertEqual(results[0].payload["departure_date"], date(2027, 6, 5))

    def test_invalid_date_is_error(self):
        text = "Name,Email,Arrival Date\nJan,jan@example.com,not-a-date\n"
        results = evaluate(text, self.conf)
        self.assertEqual(results[0].status, STATUS_ERROR)
        self.assertTrue(
            any("Arrival date is not a valid date" in m for m in results[0].messages)
        )

    def test_empty_mapped_date_cell_falls_back_to_the_default(self):
        text = "Name,Email,Arrival Date\nJan,jan@example.com,\n"
        results = evaluate(text, self.conf)
        self.assertEqual(results[0].status, STATUS_OK)
        self.assertEqual(results[0].payload["arrival_date"], date(2027, 5, 1))

    def test_compact_iso_date_is_rejected(self):
        text = "Name,Email,Arrival Date\nJan,jan@example.com,20270601\n"
        results = evaluate(text, self.conf)
        self.assertEqual(results[0].status, STATUS_ERROR)

    def test_empty_date_cell_without_conference_dates_is_error(self):
        bare = make_conference(slug="import-nodate")
        text = (
            "Name,Email,Arrival Date,Departure Date\nJan,jan@example.com,,2027-06-05\n"
        )
        results = evaluate(text, bare)
        self.assertEqual(results[0].status, STATUS_ERROR)
        self.assertTrue(any("no start date" in m for m in results[0].messages))

    def test_non_boolean_is_student_is_error(self):
        results = evaluate(
            "Name,Email,Is Student\nJan,jan@example.com,maybe\n", self.conf
        )
        self.assertEqual(results[0].status, STATUS_ERROR)
        self.assertTrue(any("must be yes or no" in m for m in results[0].messages))

    def test_is_student_accepts_czech_ano_and_ne(self):
        results = evaluate(
            "Name,Email,Is Student\nJan,jan@example.com,Ano\nEva,eva@example.com,Ne\n",
            self.conf,
        )
        self.assertIs(results[0].payload["is_student"], True)
        self.assertIs(results[1].payload["is_student"], False)

    def test_short_record_is_flagged(self):
        results = evaluate("Name,Email,Affiliation\nJan,jan@example.com\n", self.conf)
        self.assertEqual(results[0].status, STATUS_OK)
        self.assertTrue(any("columns" in m for m in results[0].messages))

    def test_long_record_is_flagged(self):
        results = evaluate("Name,Email\nJan,jan@example.com,extra\n", self.conf)
        self.assertEqual(results[0].status, STATUS_OK)
        self.assertTrue(any("columns" in m for m in results[0].messages))

    def test_empty_is_student_cell_is_false(self):
        results = evaluate("Name,Email,Is Student\nJan,jan@example.com,\n", self.conf)
        self.assertIs(results[0].payload["is_student"], False)

    def test_departure_before_arrival_is_error(self):
        text = (
            "Name,Email,Arrival Date,Departure Date\n"
            "Jan,jan@example.com,2027-06-05,2027-06-01\n"
        )
        results = evaluate(text, self.conf)
        self.assertEqual(results[0].status, STATUS_ERROR)

    def test_missing_date_column_without_conference_dates_raises(self):
        bare = make_conference(slug="import-nodate")
        with self.assertRaises(ImportFileError):
            evaluate(CSV_PLAIN, bare)

    def test_date_columns_allow_missing_conference_dates(self):
        bare = make_conference(slug="import-nodate")
        text = (
            "Name,Email,Arrival Date,Departure Date\n"
            "Jan,jan@example.com,2027-06-01,2027-06-05\n"
        )
        results = evaluate(text, bare)
        self.assertEqual(results[0].status, STATUS_OK)

    def test_duplicate_within_file_warned_and_skipped(self):
        results = evaluate(
            "Name,Email\nJan,jan@example.com\nSecond,jan@example.com\n", self.conf
        )
        self.assertEqual(results[0].status, STATUS_OK)
        self.assertEqual(results[1].status, STATUS_WARNING)

    def test_duplicate_against_existing_submission(self):
        ParticipantSubmission.objects.create(
            conference=self.conf,
            name="Existing",
            email="old@example.com",
            affiliation="",
            arrival_date=self.defaults.arrival,
            departure_date=self.defaults.departure,
        )
        results = evaluate("Name,Email\nNew,old@example.com\n", self.conf)
        self.assertEqual(results[0].status, STATUS_WARNING)

    def test_duplicate_against_existing_participant(self):
        Participant.objects.create(
            conference=self.conf, name="Existing", email="person@example.com"
        )
        results = evaluate("Name,Email\nNew,person@example.com\n", self.conf)
        self.assertEqual(results[0].status, STATUS_WARNING)

    def test_error_row_does_not_consume_the_duplicate_slot(self):
        results = evaluate(
            "Name,Email\n,jan@example.com\nSecond,jan@example.com\n", self.conf
        )
        self.assertEqual(results[0].status, STATUS_ERROR)
        self.assertEqual(results[1].status, STATUS_OK)

    def test_multiple_admin_notes_columns_are_merged(self):
        text = "Name,Email,Notes,Participation\nJan,jan@example.com,VIP guest,No\n"
        results = evaluate(text, self.conf, {2: "admin_notes", 3: "admin_notes"})
        self.assertEqual(results[0].values["admin_notes"], "VIP guest\nNo")

    def test_empty_admin_notes_column_is_dropped_in_the_merge(self):
        text = "Name,Email,Notes,Participation\nJan,jan@example.com,,No\n"
        results = evaluate(text, self.conf, {2: "admin_notes", 3: "admin_notes"})
        self.assertEqual(results[0].values["admin_notes"], "No")


class CreateSubmissionsTests(TestCase):
    def setUp(self):
        self.conf = make_conference(start=date(2027, 5, 1), end=date(2027, 5, 3))

    def test_creates_pending_submission_with_token_and_default_dates(self):
        parsed = parse_csv(CSV_TITLE)
        mapping = resolve_mapping(parsed.headers, {2: "abstract_title"})
        defaults = resolve_date_defaults(self.conf, mapping)
        results = validate_rows(parsed, mapping, self.conf, defaults)
        summary = create_submissions(results, self.conf, defaults)

        self.assertEqual(summary.created, 1)
        submission = ParticipantSubmission.objects.get(conference=self.conf)
        self.assertEqual(submission.status, "pending")
        self.assertTrue(submission.tracking_token)
        self.assertEqual(submission.abstract_title, "Quantum Fields")
        self.assertEqual(submission.arrival_date, date(2027, 5, 1))
        self.assertEqual(submission.departure_date, date(2027, 5, 3))
        self.assertEqual(Participant.objects.count(), 0)

    def test_merged_admin_notes_are_stored(self):
        text = "Name,Email,Notes,Participation\nJan,jan@example.com,VIP guest,No\n"
        parsed = parse_csv(text)
        mapping = resolve_mapping(parsed.headers, {2: "admin_notes", 3: "admin_notes"})
        defaults = resolve_date_defaults(self.conf, mapping)
        results = validate_rows(parsed, mapping, self.conf, defaults)
        create_submissions(results, self.conf, defaults)
        submission = ParticipantSubmission.objects.get(conference=self.conf)
        self.assertEqual(submission.admin_notes, "VIP guest\nNo")


class ImportAdminViewTests(TestCase):
    def setUp(self):
        self.conf = make_conference(start=date(2027, 5, 1), end=date(2027, 5, 3))
        self.url = reverse(IMPORT_URL_NAME)
        self.staff = User.objects.create_superuser(username="importer", password="pw")

    def upload(self, text=CSV_PLAIN):
        return SimpleUploadedFile(
            "participants.csv", text.encode("utf-8"), content_type="text/csv"
        )

    def preview(self, text=CSV_PLAIN):
        return self.client.post(
            self.url,
            {
                "step": "preview",
                "conference": self.conf.pk,
                "csv_file": self.upload(text),
            },
        )

    def test_requires_staff(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 302)
        self.assertIn("/admin/login/", response.url)

    def test_get_renders_form_with_single_heading(self):
        self.client.force_login(self.staff)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Import pre-registered participants")
        self.assertEqual(
            response.content.decode().count(
                "<h1>Import pre-registered participants</h1>"
            ),
            1,
        )

    def test_changelist_shows_import_button(self):
        self.client.force_login(self.staff)
        response = self.client.get(
            reverse("admin:core_participantsubmission_changelist")
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Import CSV")

    def test_preview_lists_rows_without_writing(self):
        self.client.force_login(self.staff)
        response = self.preview()
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "jan@example.com")
        self.assertEqual(ParticipantSubmission.objects.count(), 0)

    def test_preview_offers_mapping_for_unmatched_column(self):
        self.client.force_login(self.staff)
        response = self.preview(CSV_TITLE)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'name="map_2"')
        self.assertContains(response, "Update preview")

    def test_remap_applies_manual_mapping_without_writing(self):
        self.client.force_login(self.staff)
        self.preview(CSV_TITLE)
        response = self.client.post(
            self.url, {"step": "remap", "map_2": "abstract_title"}
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Abstract title")
        self.assertContains(response, "Quantum Fields")
        self.assertEqual(ParticipantSubmission.objects.count(), 0)

    def test_confirm_creates_pending_rows(self):
        self.client.force_login(self.staff)
        self.preview()
        response = self.client.post(self.url, {"step": "confirm"})
        self.assertEqual(response.status_code, 302)
        submission = ParticipantSubmission.objects.get(conference=self.conf)
        self.assertEqual(submission.status, "pending")
        self.assertTrue(submission.tracking_token)

    def test_confirm_honours_manual_mapping(self):
        self.client.force_login(self.staff)
        self.preview(CSV_TITLE)
        self.client.post(self.url, {"step": "remap", "map_2": "abstract_title"})
        self.client.post(self.url, {"step": "confirm", "map_2": "abstract_title"})
        submission = ParticipantSubmission.objects.get(conference=self.conf)
        self.assertEqual(submission.abstract_title, "Quantum Fields")

    def test_missing_required_column_blocks_confirm(self):
        self.client.force_login(self.staff)
        response = self.client.post(
            self.url,
            {
                "step": "preview",
                "conference": self.conf.pk,
                "csv_file": self.upload("Email,Whatever\njan@example.com,x\n"),
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Map a column to: Name")
        self.assertNotContains(response, 'value="confirm"')

    def test_confirm_with_missing_required_keeps_the_session(self):
        self.client.force_login(self.staff)
        self.client.post(
            self.url,
            {
                "step": "preview",
                "conference": self.conf.pk,
                "csv_file": self.upload("Email,Whatever\njan@example.com,x\n"),
            },
        )
        response = self.client.post(self.url, {"step": "confirm"})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Map a column to: Name")
        self.assertEqual(ParticipantSubmission.objects.count(), 0)
        self.assertEqual(self.client.post(self.url, {"step": "remap"}).status_code, 200)

    def test_confirm_with_dates_error_keeps_the_session(self):
        bare = make_conference(slug="import-nodate-confirm")
        self.client.force_login(self.staff)
        self.client.post(
            self.url,
            {"step": "preview", "conference": bare.pk, "csv_file": self.upload()},
        )
        response = self.client.post(self.url, {"step": "confirm"})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "no start date")
        self.assertEqual(ParticipantSubmission.objects.count(), 0)
        self.assertEqual(self.client.post(self.url, {"step": "remap"}).status_code, 200)

    def test_oversize_file_is_rejected(self):
        self.client.force_login(self.staff)
        oversize = SimpleUploadedFile(
            "big.csv",
            b"Name,Email\n" + b"x" * MAX_UPLOAD_BYTES,
            content_type="text/csv",
        )
        response = self.client.post(
            self.url,
            {"step": "preview", "conference": self.conf.pk, "csv_file": oversize},
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "larger than 2 MB")
        self.assertEqual(ParticipantSubmission.objects.count(), 0)

    def test_confirm_without_session_redirects(self):
        self.client.force_login(self.staff)
        response = self.client.post(self.url, {"step": "confirm"})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, self.url)

    def test_double_confirm_does_not_duplicate(self):
        self.client.force_login(self.staff)
        self.preview()
        self.client.post(self.url, {"step": "confirm"})
        second = self.client.post(self.url, {"step": "confirm"})
        self.assertEqual(second.url, self.url)
        self.assertEqual(
            ParticipantSubmission.objects.filter(conference=self.conf).count(), 1
        )

    def test_preview_missing_conference_dates_shows_error(self):
        bare = make_conference(slug="import-nodate")
        self.client.force_login(self.staff)
        response = self.client.post(
            self.url,
            {"step": "preview", "conference": bare.pk, "csv_file": self.upload()},
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "no start date")
