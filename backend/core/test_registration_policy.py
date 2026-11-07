"""Unit tests for the shared registration policy and its thin model wiring."""

from dataclasses import dataclass
from datetime import date

import pytest
from django.core.exceptions import ValidationError

from .models import Conference, ParticipantSubmission
from .registration import (
    default_contribution_type,
    derived_stay_dates,
    validate_common_fields,
    validate_conference_configuration,
)
from .serializers import ConferenceInfoWriteSerializer

START = date(2026, 5, 1)
END = date(2026, 5, 3)
ATTRIBUTES = str | date | bool | None


@dataclass(frozen=True, slots=True)
class ConferenceStub:
    date_start: date | None = START
    date_end: date | None = END
    registration_collect_dates: bool = True
    registration_deadline: date | None = None
    submission_edit_deadline: date | None = None
    registration_allow_talk: bool = True
    registration_allow_poster: bool = True
    registration_allow_attend: bool = True

    @property
    def allowed_contribution_types(self) -> tuple[str, ...]:
        return tuple(
            name
            for name, enabled in (
                ("talk", self.registration_allow_talk),
                ("poster", self.registration_allow_poster),
                ("attend", self.registration_allow_attend),
            )
            if enabled
        )


@dataclass(frozen=True, slots=True)
class SubmissionStub:
    name: str = "Jane Doe"
    email: str = "jane@example.com"
    affiliation: str = "CTU"
    contribution_type: str = "talk"
    abstract_title: str = "Numerical methods"
    abstract_text: str = "An abstract"
    arrival_date: date | None = START
    departure_date: date | None = END
    stay_dates_derived: bool = False


def config_values(conference: ConferenceStub) -> dict[str, ATTRIBUTES]:
    return {
        field: getattr(conference, field)
        for field in (
            "date_start",
            "date_end",
            "registration_collect_dates",
            "registration_deadline",
            "submission_edit_deadline",
            "registration_allow_talk",
            "registration_allow_poster",
            "registration_allow_attend",
        )
    }


def valid_submission(**changes: ATTRIBUTES) -> dict[str, ATTRIBUTES]:
    values: dict[str, ATTRIBUTES] = {
        "name": "Jane Doe",
        "email": "jane@example.com",
        "affiliation": "CTU",
        "contribution_type": "talk",
        "abstract_title": "Numerical methods",
        "abstract_text": "An abstract",
        "arrival_date": START,
        "departure_date": END,
    }
    values.update(changes)
    return values


@pytest.mark.parametrize(
    ("conference", "expected"),
    [
        (
            ConferenceStub(date_start=START, date_end=START),
            "registration_collect_dates",
        ),
        (ConferenceStub(date_start=END, date_end=START), "date_end"),
        (
            ConferenceStub(registration_collect_dates=False, date_start=None),
            "date_start",
        ),
        (
            ConferenceStub(registration_collect_dates=False, date_end=None),
            "date_end",
        ),
    ],
)
def test_configuration_rejects_invalid_date_policy(conference, expected):
    assert expected in validate_conference_configuration(config_values(conference))


@pytest.mark.parametrize(
    "conference",
    [
        ConferenceStub(),
        ConferenceStub(
            date_start=START, date_end=START, registration_collect_dates=False
        ),
        ConferenceStub(registration_collect_dates=False),
    ],
)
def test_configuration_accepts_valid_date_policy(conference):
    assert validate_conference_configuration(config_values(conference)) == {}


def test_configuration_preserves_both_deadline_messages():
    conference = ConferenceStub(
        registration_deadline=date(2026, 5, 5),
        submission_edit_deadline=date(2026, 5, 4),
    )

    errors = validate_conference_configuration(config_values(conference))

    assert errors["submission_edit_deadline"] == [
        "Submission editing deadline must be on or after the registration deadline.",
        "Submission editing deadline must be on or before the conference end date.",
    ]


def test_configuration_preserves_allowed_type_message():
    conference = ConferenceStub(
        registration_allow_talk=False,
        registration_allow_poster=False,
        registration_allow_attend=False,
    )
    assert validate_conference_configuration(config_values(conference)) == {
        "registration_allow_talk": ["At least one contribution type must be allowed."]
    }


def test_default_contribution_type_uses_first_allowed_type():
    conference = ConferenceStub(registration_allow_talk=False)
    assert default_contribution_type(conference) == "poster"


def test_derived_stay_dates_returns_stored_conference_range():
    assert derived_stay_dates(ConferenceStub()) == (START, END)


@pytest.mark.parametrize(
    "conference",
    [
        ConferenceStub(date_start=None),
        ConferenceStub(date_end=None),
        ConferenceStub(date_start=END, date_end=START),
    ],
)
def test_derived_stay_dates_rejects_missing_or_inverted_dates(conference):
    with pytest.raises(ValidationError):
        derived_stay_dates(conference)


@pytest.mark.parametrize("field", ["name", "email", "affiliation"])
def test_common_fields_are_required_on_create(field):
    attrs = valid_submission(**{field: "  "})
    assert field in validate_common_fields(
        attrs, conference=ConferenceStub(), creating=True
    )


def test_common_fields_absent_on_update_are_not_required():
    assert validate_common_fields({}, conference=ConferenceStub(), creating=False) == {}


@pytest.mark.parametrize("affiliation", ["ab", "  ab  "])
def test_affiliation_uses_trimmed_minimum_length(affiliation):
    attrs = valid_submission(affiliation=affiliation)
    assert "affiliation" in validate_common_fields(
        attrs, conference=ConferenceStub(), creating=True
    )


def test_abstract_word_limit_excludes_attendance_only_registrations():
    words = " ".join(["word"] * 251)
    attrs = valid_submission(abstract_text=words)
    assert "abstract_text" in validate_common_fields(
        attrs, conference=ConferenceStub(), creating=True
    )
    attrs["contribution_type"] = "attend"
    assert (
        validate_common_fields(attrs, conference=ConferenceStub(), creating=True) == {}
    )


@pytest.mark.parametrize("contribution_type", ["talk", "poster"])
def test_title_is_required_on_create_for_a_contribution(contribution_type):
    attrs = valid_submission(contribution_type=contribution_type, abstract_title=" ")
    assert "abstract_title" in validate_common_fields(
        attrs, conference=ConferenceStub(), creating=True
    )


def test_changing_to_a_contribution_requires_a_title():
    instance = SubmissionStub(contribution_type="attend", abstract_title="")
    attrs = {"contribution_type": "talk"}
    assert "abstract_title" in validate_common_fields(
        attrs, conference=ConferenceStub(), instance=instance, creating=False
    )


def test_unchanged_legacy_type_exception_covers_type_and_title():
    conference = ConferenceStub(registration_allow_talk=False)
    instance = SubmissionStub(abstract_title="")
    attrs = {"name": "New name", "contribution_type": "talk"}
    assert (
        validate_common_fields(
            attrs, conference=conference, instance=instance, creating=False
        )
        == {}
    )


def test_changing_to_disabled_type_is_rejected():
    conference = ConferenceStub(registration_allow_poster=False)
    instance = SubmissionStub()
    attrs = {"contribution_type": "poster", "abstract_title": "A poster"}
    assert "contribution_type" in validate_common_fields(
        attrs, conference=conference, instance=instance, creating=False
    )


def test_conference_and_serializer_share_the_single_day_rule():
    with pytest.raises(ValidationError) as caught:
        Conference(slug="single-day", date_start=START, date_end=START).clean()
    assert "registration_collect_dates" in caught.value.message_dict
    serializer = ConferenceInfoWriteSerializer(
        Conference(slug="missing-dates"),
        data={"registration_collect_dates": False},
        partial=True,
    )
    assert not serializer.is_valid()
    assert set(serializer.errors) == {"date_start", "date_end"}


def test_submission_clean_requires_a_title_and_clears_attend_fields():
    conference = Conference(slug="policy-model", date_start=START, date_end=END)
    talk = ParticipantSubmission(
        conference=conference,
        name="Jane",
        email="jane@example.com",
        affiliation="CTU",
        arrival_date=START,
        departure_date=END,
    )
    with pytest.raises(ValidationError) as caught:
        talk.clean()
    assert "abstract_title" in caught.value.message_dict
    attend = replace_model(talk, contribution_type="attend", abstract_title="Stale")
    attend.clean()
    assert attend.abstract_title == attend.abstract_text == ""


def test_submission_clean_allows_an_unassigned_conference():
    ParticipantSubmission().clean()


def replace_model(instance, **changes):
    for field, value in changes.items():
        setattr(instance, field, value)
    return instance
