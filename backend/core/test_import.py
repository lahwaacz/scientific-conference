"""CSV import of pre-registered participants.

Pins the generalized import engine (field-name matching, manual mapping,
delimiter/encoding handling, registration policy, duplicate detection, typed
payloads) and the Django-admin upload -> preview -> map -> confirm wizard.
"""

from datetime import date
from unittest import mock

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse

from .admin import MAX_UPLOAD_BYTES
from .importing import (
    STATUS_ERROR,
    STATUS_OK,
    STATUS_WARNING,
    ImportFileError,
    create_submissions,
    decode_csv_bytes,
    importable_fields,
    parse_csv,
    required_fields,
    resolve_mapping,
    validate_rows,
)
from .models import Conference, Participant, ParticipantSubmission
from .serializers import ParticipantSubmissionImportSerializer

IMPORT_URL_NAME = "admin:core_participantsubmission_import"

# A title column whose header contains a comma must be quoted in a comma CSV.
CSV_TITLE = (
    "Name,Email,Affiliation,Arrival Date,Departure Date,"
    '"Topic / Title (Tentative, for all now)"\n'
    "Jan Novák,jan@example.com,CTU,2027-05-02,2027-05-04,Quantum Fields\n"
)
CSV_PLAIN = (
    "Name,Email,Affiliation,Abstract Title,Arrival Date,Departure Date\n"
    "Jan Novák,jan@example.com,CTU,Quantum Fields,2027-05-02,2027-05-04\n"
)


def make_conference(
    slug="import-conf",
    start=None,
    end=None,
    collect_dates=True,
    allowed=("talk", "poster", "attend"),
):
    return Conference.objects.create(
        slug=slug,
        date_start=start,
        date_end=end,
        registration_collect_dates=collect_dates,
        registration_allow_talk="talk" in allowed,
        registration_allow_poster="poster" in allowed,
        registration_allow_attend="attend" in allowed,
    )


def evaluate(text, conference, manual=None):
    parsed = parse_csv(text)
    mapping = resolve_mapping(parsed.headers, conference, manual)
    return validate_rows(parsed, mapping, conference)


class ImportableFieldsTests(TestCase):
    def test_exposes_model_fields_but_not_managed_ones(self):
        conference = make_conference()
        names = {name for name, _ in importable_fields(conference)}
        self.assertIn("name", names)
        self.assertIn("abstract_title", names)
        self.assertIn("is_student", names)
        self.assertIn("contribution_type", names)
        self.assertIn("admin_notes", names)
        self.assertNotIn("photo", names)
        self.assertNotIn("status", names)
        self.assertNotIn("tracking_token", names)
        self.assertNotIn("stay_dates_derived", names)

    def test_dates_are_excluded_when_collection_is_off(self):
        conference = make_conference(collect_dates=False)
        names = {name for name, _ in importable_fields(conference)}
        self.assertNotIn("arrival_date", names)
        self.assertNotIn("departure_date", names)
        self.assertIn("admin_notes", names)

    def test_required_fields_follow_date_collection(self):
        collecting = make_conference()
        derived = make_conference(slug="derived-conf", collect_dates=False)
        self.assertEqual(
            required_fields(collecting),
            ("name", "email", "affiliation", "arrival_date", "departure_date"),
        )
        self.assertEqual(required_fields(derived), ("name", "email", "affiliation"))


class MappingTests(TestCase):
    def setUp(self):
        self.conf = make_conference()

    def resolve(self, headers, manual=None):
        return resolve_mapping(headers, self.conf, manual)

    def test_header_matches_field_name_ignoring_case_and_spaces(self):
        mapping = self.resolve(["Name", "Email", "Abstract Title"])
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
                ("Abstract Title", "Title"),
            ],
        )

    def test_unmatched_column_is_configurable(self):
        headers = ["Name", "Email", "Topic / Title (Tentative, for all now)"]
        mapping = self.resolve(headers)
        self.assertEqual(mapping.configurable, [(2, headers[2], "")])
        self.assertEqual(mapping.conflicts, [])

    def test_manual_mapping_assigns_a_field(self):
        headers = ["Name", "Email", "Topic"]
        mapping = self.resolve(headers, {2: "abstract_title"})
        self.assertEqual(mapping.field_to_indices["abstract_title"], [2])
        self.assertEqual(mapping.configurable, [(2, "Topic", "abstract_title")])

    def test_second_column_for_a_non_mergeable_field_is_a_conflict(self):
        mapping = self.resolve(["Name", "Email", "Abstract Title"], {2: "email"})
        self.assertEqual(mapping.field_to_indices["email"], [1])
        self.assertEqual(mapping.conflicts, [(2, "Abstract Title")])

    def test_columns_merging_into_admin_notes_do_not_conflict(self):
        headers = ["Name", "Email", "Notes", "Participation"]
        mapping = self.resolve(headers, {2: "admin_notes", 3: "admin_notes"})
        self.assertEqual(mapping.field_to_indices["admin_notes"], [2, 3])
        self.assertEqual(mapping.conflicts, [])

    def test_conflicting_auto_matched_column_stays_configurable(self):
        mapping = self.resolve(["Email", "E Mail"])
        self.assertEqual(mapping.field_to_indices["email"], [0])
        self.assertEqual(mapping.conflicts, [(1, "E Mail")])
        self.assertIn((1, "E Mail", "email"), mapping.configurable)

    def test_date_columns_are_unmapped_when_collection_is_off(self):
        self.conf.registration_collect_dates = False
        mapping = self.resolve(["Arrival Date", "Departure Date"])
        self.assertEqual(mapping.field_to_indices, {})
        self.assertEqual(mapping.conflicts, [])
        self.assertEqual(
            mapping.configurable,
            [(0, "Arrival Date", ""), (1, "Departure Date", "")],
        )


class ParsingTests(TestCase):
    def test_unknown_column_does_not_break_parsing(self):
        parsed = parse_csv(CSV_TITLE)
        self.assertEqual(len(parsed.records), 1)
        self.assertEqual(parsed.headers[5], "Topic / Title (Tentative, for all now)")

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
        self.conf = make_conference(
            start=date(2027, 5, 1),
            end=date(2027, 5, 3),
            collect_dates=False,
            allowed=("attend",),
        )

    def collecting_conference(self, slug="date-conf"):
        return make_conference(slug=slug, start=date(2027, 5, 1), end=date(2027, 5, 3))

    def test_valid_row_is_ok(self):
        results = evaluate(CSV_PLAIN, self.conf)
        self.assertEqual(results[0].status, STATUS_OK, results[0].messages)
        self.assertTrue(results[0].will_import)

    def test_missing_name_is_error(self):
        results = evaluate("Name,Email,Affiliation\n,jan@example.com,CTU\n", self.conf)
        self.assertEqual(results[0].status, STATUS_ERROR)

    def test_invalid_email_is_error(self):
        results = evaluate("Name,Email,Affiliation\nJan,not-an-email,CTU\n", self.conf)
        self.assertEqual(results[0].status, STATUS_ERROR)

    def test_is_student_is_parsed(self):
        results = evaluate(
            "Name,Email,Affiliation,Is Student\nJan,jan@example.com,CTU,Yes\n",
            self.conf,
        )
        self.assertIs(results[0].payload["is_student"], True)

    def test_contribution_type_is_parsed(self):
        conference = make_conference(
            slug="typed-conf",
            start=date(2027, 5, 1),
            end=date(2027, 5, 3),
            collect_dates=False,
        )
        results = evaluate(
            "Name,Email,Affiliation,Contribution Type,Abstract Title\n"
            "Jan,jan@example.com,CTU,Talk,Talk title\n"
            "Eva,eva@example.com,CTU,Poster,Poster title\n"
            "Petr,petr@example.com,CTU,Just attend,\n",
            conference,
        )
        self.assertEqual(results[0].payload["contribution_type"], "talk")
        self.assertEqual(results[1].payload["contribution_type"], "poster")
        self.assertEqual(results[2].payload["contribution_type"], "attend")

    def test_contribution_type_accepts_czech_values(self):
        conference = make_conference(
            slug="typed-conf",
            start=date(2027, 5, 1),
            end=date(2027, 5, 3),
            collect_dates=False,
        )
        results = evaluate(
            "Name,Email,Affiliation,Contribution Type,Abstract Title\n"
            "Jan,jan@example.com,CTU,přednáška,Talk title\n"
            "Eva,eva@example.com,CTU,účast,\n",
            conference,
        )
        self.assertEqual(results[0].payload["contribution_type"], "talk")
        self.assertEqual(results[1].payload["contribution_type"], "attend")

    def test_invalid_contribution_type_is_error(self):
        results = evaluate(
            "Name,Email,Affiliation,Contribution Type\n"
            "Jan,jan@example.com,CTU,workshop\n",
            self.conf,
        )
        self.assertEqual(results[0].status, STATUS_ERROR)
        self.assertTrue(
            any("Talk, Poster, or Just attend" in m for m in results[0].messages)
        )

    def test_abstract_does_not_infer_talk(self):
        results = evaluate(
            "Name,Email,Affiliation,Abstract Title\n"
            "Jan,jan@example.com,CTU,An unused title\n",
            self.conf,
        )
        self.assertEqual(results[0].payload["contribution_type"], "attend")
        self.assertEqual(results[0].payload["abstract_title"], "")

    def test_empty_contribution_type_cell_uses_first_allowed(self):
        conference = make_conference(
            slug="typed-conf",
            start=date(2027, 5, 1),
            end=date(2027, 5, 3),
            collect_dates=False,
            allowed=("poster", "attend"),
        )
        results = evaluate(
            "Name,Email,Affiliation,Contribution Type,Abstract Title\n"
            "Jan,jan@example.com,CTU,,Poster title\n",
            conference,
        )
        self.assertEqual(results[0].status, STATUS_OK, results[0].messages)
        self.assertEqual(results[0].payload["contribution_type"], "poster")

    def test_length_error_names_the_column(self):
        long_name = "x" * 300
        results = evaluate(
            f"Name,Email,Affiliation\n{long_name},jan@example.com,CTU\n", self.conf
        )
        self.assertEqual(results[0].status, STATUS_ERROR)
        self.assertTrue(any("Name is longer" in m for m in results[0].messages))

    def test_explicit_dates_are_used_when_collection_is_on(self):
        text = (
            "Name,Email,Affiliation,Abstract Title,Arrival Date,Departure Date\n"
            "Jan,jan@example.com,CTU,Quantum Fields,2027-06-01,2027-06-05\n"
        )
        results = evaluate(text, self.collecting_conference())
        self.assertEqual(results[0].payload["arrival_date"], date(2027, 6, 1))
        self.assertEqual(results[0].payload["departure_date"], date(2027, 6, 5))

    def test_invalid_date_is_error(self):
        text = (
            "Name,Email,Affiliation,Abstract Title,Arrival Date,Departure Date\n"
            "Jan,jan@example.com,CTU,Quantum Fields,not-a-date,2027-06-05\n"
        )
        results = evaluate(text, self.collecting_conference())
        self.assertEqual(results[0].status, STATUS_ERROR)
        self.assertTrue(
            any("Arrival date is not a valid date" in m for m in results[0].messages)
        )

    def test_empty_mapped_date_cell_is_an_error_without_fallback(self):
        text = (
            "Name,Email,Affiliation,Abstract Title,Arrival Date,Departure Date\n"
            "Jan,jan@example.com,CTU,Quantum Fields,,2027-06-05\n"
        )
        results = evaluate(text, self.collecting_conference())
        self.assertEqual(results[0].status, STATUS_ERROR)
        self.assertNotEqual(results[0].payload.get("arrival_date"), date(2027, 5, 1))

    def test_compact_iso_date_is_rejected(self):
        text = (
            "Name,Email,Affiliation,Abstract Title,Arrival Date,Departure Date\n"
            "Jan,jan@example.com,CTU,Quantum Fields,20270601,2027-06-05\n"
        )
        results = evaluate(text, self.collecting_conference())
        self.assertEqual(results[0].status, STATUS_ERROR)

    def test_empty_date_cell_without_conference_dates_is_error(self):
        bare = make_conference(slug="import-nodate")
        text = (
            "Name,Email,Affiliation,Abstract Title,Arrival Date,Departure Date\n"
            "Jan,jan@example.com,CTU,Quantum Fields,,2027-06-05\n"
        )
        results = evaluate(text, bare)
        self.assertEqual(results[0].status, STATUS_ERROR)
        self.assertTrue(
            any("required when participant dates" in m for m in results[0].messages)
        )

    def test_non_boolean_is_student_is_error(self):
        results = evaluate(
            "Name,Email,Affiliation,Is Student\nJan,jan@example.com,CTU,maybe\n",
            self.conf,
        )
        self.assertEqual(results[0].status, STATUS_ERROR)
        self.assertTrue(any("must be yes or no" in m for m in results[0].messages))

    def test_is_student_accepts_czech_ano_and_ne(self):
        results = evaluate(
            "Name,Email,Affiliation,Is Student\n"
            "Jan,jan@example.com,CTU,Ano\nEva,eva@example.com,CTU,Ne\n",
            self.conf,
        )
        self.assertIs(results[0].payload["is_student"], True)
        self.assertIs(results[1].payload["is_student"], False)

    def test_short_record_is_flagged(self):
        results = evaluate(
            "Name,Email,Affiliation,Info\nJan,jan@example.com,CTU\n", self.conf
        )
        self.assertEqual(results[0].status, STATUS_OK, results[0].messages)
        self.assertTrue(any("columns" in m for m in results[0].messages))

    def test_long_record_is_flagged(self):
        results = evaluate(
            "Name,Email,Affiliation\nJan,jan@example.com,CTU,extra\n", self.conf
        )
        self.assertEqual(results[0].status, STATUS_OK, results[0].messages)
        self.assertTrue(any("columns" in m for m in results[0].messages))

    def test_empty_is_student_cell_is_false(self):
        results = evaluate(
            "Name,Email,Affiliation,Is Student\nJan,jan@example.com,CTU,\n", self.conf
        )
        self.assertIs(results[0].payload["is_student"], False)

    def test_departure_before_arrival_is_error(self):
        text = (
            "Name,Email,Affiliation,Abstract Title,Arrival Date,Departure Date\n"
            "Jan,jan@example.com,CTU,Quantum Fields,2027-06-05,2027-06-01\n"
        )
        results = evaluate(text, self.collecting_conference())
        self.assertEqual(results[0].status, STATUS_ERROR)

    def test_missing_date_columns_are_row_errors_without_fallback(self):
        text = (
            "Name,Email,Affiliation,Abstract Title\n"
            "Jan,jan@example.com,CTU,Quantum Fields\n"
        )
        results = evaluate(text, self.collecting_conference())
        self.assertEqual(results[0].status, STATUS_ERROR)
        self.assertTrue(any("Arrival date" in m for m in results[0].messages))
        self.assertTrue(any("Departure date" in m for m in results[0].messages))

    def test_date_columns_allow_missing_conference_dates(self):
        bare = make_conference(slug="import-nodate")
        text = (
            "Name,Email,Affiliation,Abstract Title,Arrival Date,Departure Date\n"
            "Jan,jan@example.com,CTU,Quantum Fields,2027-06-01,2027-06-05\n"
        )
        results = evaluate(text, bare)
        self.assertEqual(results[0].status, STATUS_OK, results[0].messages)

    def test_duplicate_within_file_warned_and_skipped(self):
        results = evaluate(
            "Name,Email,Affiliation\n"
            "Jan,jan@example.com,CTU\nSecond,jan@example.com,CTU\n",
            self.conf,
        )
        self.assertEqual(results[0].status, STATUS_OK, results[0].messages)
        self.assertEqual(results[1].status, STATUS_WARNING)

    def test_duplicate_against_existing_submission(self):
        ParticipantSubmission.objects.create(
            conference=self.conf,
            name="Existing",
            email="old@example.com",
            affiliation="CTU",
            contribution_type="attend",
            arrival_date=self.conf.date_start,
            departure_date=self.conf.date_end,
        )
        results = evaluate(
            "Name,Email,Affiliation\nNew,old@example.com,CTU\n", self.conf
        )
        self.assertEqual(results[0].status, STATUS_WARNING)

    def test_duplicate_against_existing_participant(self):
        Participant.objects.create(
            conference=self.conf, name="Existing", email="person@example.com"
        )
        results = evaluate(
            "Name,Email,Affiliation\nNew,person@example.com,CTU\n", self.conf
        )
        self.assertEqual(results[0].status, STATUS_WARNING)

    def test_error_row_does_not_consume_the_duplicate_slot(self):
        results = evaluate(
            "Name,Email,Affiliation\n,jan@example.com,CTU\nSecond,jan@example.com,CTU\n",
            self.conf,
        )
        self.assertEqual(results[0].status, STATUS_ERROR)
        self.assertEqual(results[1].status, STATUS_OK, results[1].messages)

    def test_multiple_admin_notes_columns_are_merged(self):
        text = (
            "Name,Email,Affiliation,Notes,Participation\n"
            "Jan,jan@example.com,CTU,VIP guest,No\n"
        )
        results = evaluate(text, self.conf, {3: "admin_notes", 4: "admin_notes"})
        self.assertEqual(results[0].values["admin_notes"], "VIP guest\nNo")

    def test_empty_admin_notes_column_is_dropped_in_the_merge(self):
        text = (
            "Name,Email,Affiliation,Notes,Participation\nJan,jan@example.com,CTU,,No\n"
        )
        results = evaluate(text, self.conf, {3: "admin_notes", 4: "admin_notes"})
        self.assertEqual(results[0].values["admin_notes"], "No")


class RegistrationPolicyTests(TestCase):
    START = date(2027, 5, 1)
    END = date(2027, 5, 3)
    COLLECTED_CSV = (
        "Name,Email,Affiliation,Contribution Type,Abstract Title,Abstract Text,"
        "Additional Authors,Additional Affiliations,Arrival Date,Departure Date\n"
        "Jan,jan@example.com,CTU,talk,Quantum Fields,An abstract,"
        "Eva,Charles University,2027-05-02,2027-05-04\n"
    )

    def setUp(self):
        self.conf = make_conference(start=self.START, end=self.END)

    def conference(self, *, collect_dates=True, allowed=("talk", "poster", "attend")):
        self.conf.registration_collect_dates = collect_dates
        self.conf.registration_allow_talk = "talk" in allowed
        self.conf.registration_allow_poster = "poster" in allowed
        self.conf.registration_allow_attend = "attend" in allowed
        self.conf.save()
        return self.conf

    def test_default_is_first_allowed_type_for_every_combination(self):
        for talk in (False, True):
            for poster in (False, True):
                for attend in (False, True):
                    allowed = tuple(
                        name
                        for name, enabled in (
                            ("talk", talk),
                            ("poster", poster),
                            ("attend", attend),
                        )
                        if enabled
                    )
                    if not allowed:
                        continue
                    with self.subTest(allowed=allowed):
                        conference = self.conference(allowed=allowed)
                        text = (
                            "Name,Email,Affiliation,Abstract Title,"
                            "Arrival Date,Departure Date\n"
                            "Jan,jan@example.com,CTU,A title,2027-05-02,2027-05-04\n"
                        )
                        result = evaluate(text, conference)[0]
                        self.assertEqual(result.status, STATUS_OK, result.messages)
                        self.assertEqual(
                            result.payload["contribution_type"], allowed[0]
                        )

    def test_disallowed_contribution_type_is_rejected(self):
        conference = self.conference(allowed=("talk",))
        result = evaluate(self.COLLECTED_CSV.replace("talk", "poster"), conference)[0]
        self.assertEqual(result.status, STATUS_ERROR)
        self.assertIn("not available", " ".join(result.messages))

    def test_talk_and_poster_require_a_title(self):
        for contribution_type in ("talk", "poster"):
            with self.subTest(contribution_type=contribution_type):
                text = self.COLLECTED_CSV.replace("Quantum Fields", "").replace(
                    "talk", contribution_type
                )
                result = evaluate(text, self.conference())[0]
                self.assertEqual(result.status, STATUS_ERROR)
                self.assertIn("Title is required", " ".join(result.messages))

    def test_affiliation_is_required_and_has_minimum_length(self):
        blank = evaluate(self.COLLECTED_CSV.replace("CTU", ""), self.conference())[0]
        short = evaluate(self.COLLECTED_CSV.replace("CTU", "CT"), self.conference())[0]
        self.assertIn("Affiliation: This field may not be blank.", blank.messages)
        self.assertIn("at least 3 characters", " ".join(short.messages))

    def test_abstract_word_limit_is_enforced(self):
        text = self.COLLECTED_CSV.replace("An abstract", " ".join(["word"] * 251))
        result = evaluate(text, self.conference())[0]
        self.assertEqual(result.status, STATUS_ERROR)
        self.assertIn("250 words", " ".join(result.messages))

    def test_attend_clears_contribution_fields(self):
        text = self.COLLECTED_CSV.replace("talk", "attend")
        result = evaluate(text, self.conference())[0]
        self.assertEqual(result.status, STATUS_OK, result.messages)
        self.assertEqual(
            [
                result.payload[field]
                for field in (
                    "abstract_title",
                    "abstract_text",
                    "additional_authors",
                    "additional_affiliations",
                )
            ],
            ["", "", "", ""],
        )

    def test_blank_collected_dates_do_not_fall_back_to_conference_dates(self):
        text = self.COLLECTED_CSV.replace("2027-05-02", "").replace("2027-05-04", "")
        result = evaluate(text, self.conference())[0]
        self.assertEqual(result.status, STATUS_ERROR)
        self.assertNotEqual(result.payload.get("arrival_date"), self.START)
        self.assertNotEqual(result.payload.get("departure_date"), self.END)

    def test_invalid_and_explicit_dates_are_ignored_when_collection_is_off(self):
        text = self.COLLECTED_CSV.replace("2027-05-02", "not-a-date").replace(
            "2027-05-04", "also-not-a-date"
        )
        result = evaluate(text, self.conference(collect_dates=False))[0]
        self.assertEqual(result.status, STATUS_OK, result.messages)
        self.assertEqual(result.payload["arrival_date"], self.START)
        self.assertEqual(result.payload["departure_date"], self.END)
        self.assertIs(result.payload["stay_dates_derived"], True)

    def test_single_day_conference_derives_equal_dates_when_collection_is_off(self):
        conference = make_conference(
            slug="single-day",
            start=self.START,
            end=self.START,
            collect_dates=False,
            allowed=("attend",),
        )
        text = "Name,Email,Affiliation\nJan,jan@example.com,CTU\n"
        result = evaluate(text, conference)[0]
        self.assertEqual(result.status, STATUS_OK, result.messages)
        self.assertEqual(result.payload["arrival_date"], self.START)
        self.assertEqual(result.payload["departure_date"], self.START)
        self.assertIs(result.payload["stay_dates_derived"], True)

    def test_private_serializer_only_opens_admin_notes(self):
        serializer = ParticipantSubmissionImportSerializer(
            context={"conference": self.conference()}
        )
        self.assertFalse(serializer.fields["admin_notes"].read_only)
        for name in (
            "status",
            "linked_user",
            "published_participant",
            "published_abstract",
            "tracking_token",
            "participant_reference",
            "stay_dates_derived",
            "photo",
        ):
            with self.subTest(field=name):
                self.assertTrue(serializer.fields[name].read_only)


class CreateSubmissionsTests(TestCase):
    def setUp(self):
        self.conf = make_conference(start=date(2027, 5, 1), end=date(2027, 5, 3))

    def test_creates_pending_submission_with_token_and_csv_dates(self):
        results = evaluate(CSV_TITLE, self.conf, {5: "abstract_title"})
        summary = create_submissions(results, self.conf)

        self.assertEqual(summary.created, 1)
        submission = ParticipantSubmission.objects.get(conference=self.conf)
        self.assertEqual(submission.status, "pending")
        self.assertTrue(submission.tracking_token)
        self.assertEqual(submission.abstract_title, "Quantum Fields")
        self.assertEqual(submission.arrival_date, date(2027, 5, 2))
        self.assertEqual(submission.departure_date, date(2027, 5, 4))
        self.assertIs(submission.stay_dates_derived, False)
        self.assertEqual(Participant.objects.count(), 0)

    def test_merged_admin_notes_are_stored(self):
        text = (
            "Name,Email,Affiliation,Abstract Title,Arrival Date,Departure Date,"
            "Notes,Participation\n"
            "Jan,jan@example.com,CTU,Quantum Fields,2027-05-02,2027-05-04,"
            "VIP guest,No\n"
        )
        results = evaluate(text, self.conf, {6: "admin_notes", 7: "admin_notes"})
        create_submissions(results, self.conf)
        submission = ParticipantSubmission.objects.get(conference=self.conf)
        self.assertEqual(submission.admin_notes, "VIP guest\nNo")

    def test_dates_off_create_derives_stay_and_ignores_csv_dates(self):
        self.conf.registration_collect_dates = False
        self.conf.save()
        text = CSV_PLAIN.replace("2027-05-02", "2030-01-01").replace(
            "2027-05-04", "2030-01-02"
        )
        results = evaluate(text, self.conf)
        create_submissions(results, self.conf)

        submission = ParticipantSubmission.objects.get(conference=self.conf)
        self.assertEqual(submission.arrival_date, date(2027, 5, 1))
        self.assertEqual(submission.departure_date, date(2027, 5, 3))
        self.assertIs(submission.stay_dates_derived, True)

    def test_duplicate_rows_are_skipped_at_creation(self):
        results = evaluate(
            CSV_PLAIN + CSV_PLAIN.splitlines(keepends=True)[1], self.conf
        )
        summary = create_submissions(results, self.conf)
        self.assertEqual((summary.created, summary.skipped), (1, 1))
        self.assertEqual(
            ParticipantSubmission.objects.filter(conference=self.conf).count(), 1
        )

    def test_pre_registration_import_is_allowed(self):
        self.conf.registration_opening = date(2027, 1, 1)
        self.conf.registration_deadline = date(2027, 2, 1)
        self.conf.save()

        results = evaluate(CSV_PLAIN, self.conf)
        summary = create_submissions(results, self.conf)

        self.assertEqual(summary.created, 1)
        self.assertEqual(
            ParticipantSubmission.objects.get(conference=self.conf).status, "pending"
        )


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
        self.assertContains(response, 'name="map_5"')
        self.assertContains(response, "Update preview")

    def test_remap_applies_manual_mapping_without_writing(self):
        self.client.force_login(self.staff)
        self.preview(CSV_TITLE)
        response = self.client.post(
            self.url, {"step": "remap", "map_5": "abstract_title"}
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Title")
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
        self.client.post(self.url, {"step": "remap", "map_5": "abstract_title"})
        self.client.post(self.url, {"step": "confirm", "map_5": "abstract_title"})
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

    def test_confirm_with_missing_date_columns_keeps_the_session(self):
        bare = make_conference(slug="import-nodate-confirm")
        self.client.force_login(self.staff)
        self.client.post(
            self.url,
            {
                "step": "preview",
                "conference": bare.pk,
                "csv_file": self.upload(
                    "Name,Email,Affiliation,Abstract Title\n"
                    "Jan,jan@example.com,CTU,Quantum Fields\n"
                ),
            },
        )
        response = self.client.post(self.url, {"step": "confirm"})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Map a column to: Arrival date, Departure date")
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

    def test_preview_blank_date_has_no_conference_fallback(self):
        bare = make_conference(slug="import-nodate")
        self.client.force_login(self.staff)
        response = self.client.post(
            self.url,
            {
                "step": "preview",
                "conference": bare.pk,
                "csv_file": self.upload(CSV_PLAIN.replace("2027-05-02", "")),
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "required when participant dates are collected")

    def test_preview_requires_affiliation_mapping(self):
        self.client.force_login(self.staff)
        response = self.preview(
            "Name,Email,Abstract Title,Arrival Date,Departure Date\n"
            "Jan,jan@example.com,Quantum Fields,2027-05-02,2027-05-04\n"
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Map a column to: Affiliation")
        self.assertNotContains(response, 'value="confirm"')

    def test_dates_off_wizard_ignores_dates_and_stores_derived_stay(self):
        self.conf.registration_collect_dates = False
        self.conf.save()
        self.client.force_login(self.staff)

        preview = self.preview()
        self.assertContains(preview, "ignored and derived stays are marked accordingly")
        self.assertContains(preview, 'name="map_4"')
        self.assertContains(preview, 'name="map_5"')
        response = self.client.post(self.url, {"step": "confirm"})

        self.assertEqual(response.status_code, 302)
        submission = ParticipantSubmission.objects.get(conference=self.conf)
        self.assertEqual(submission.arrival_date, date(2027, 5, 1))
        self.assertEqual(submission.departure_date, date(2027, 5, 3))
        self.assertIs(submission.stay_dates_derived, True)
