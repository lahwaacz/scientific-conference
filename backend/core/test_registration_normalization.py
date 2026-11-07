"""Tests for submission clearing, date ordering and create/update normalization."""

from datetime import date

import pytest
from django.core.exceptions import ValidationError

from .registration import (
    clear_attend_fields,
    normalize_new_submission,
    normalize_submission_update,
    validate_date_order,
)
from .test_registration_policy import (
    END,
    START,
    ConferenceStub,
    SubmissionStub,
    valid_submission,
)


def test_attend_fields_are_cleared_without_mutating_input():
    attrs = valid_submission(
        contribution_type="attend",
        additional_authors="A. Author",
        additional_affiliations="Other University",
    )
    normalized = clear_attend_fields(attrs)
    assert [
        normalized[field]
        for field in (
            "abstract_title",
            "abstract_text",
            "additional_authors",
            "additional_affiliations",
        )
    ] == ["", "", "", ""]
    assert attrs["abstract_title"] == "Numerical methods"


@pytest.mark.parametrize(
    ("collect", "creating", "supplied", "departure", "valid"),
    [
        (True, True, True, START, False),
        (True, False, True, START, False),
        (True, False, False, START, True),
        (False, False, True, START, True),
        (False, False, False, date(2026, 4, 30), False),
    ],
)
def test_date_order_respects_collection_and_legacy_rows(
    collect, creating, supplied, departure, valid
):
    conference = ConferenceStub(registration_collect_dates=collect)
    attrs = {"arrival_date": START, "departure_date": departure}
    errors = validate_date_order(
        attrs,
        instance=SubmissionStub(),
        conference=conference,
        dates_supplied=supplied,
        creating=creating,
    )
    assert (errors == {}) is valid


def test_normalize_new_submission_defaults_contribution_type():
    conference = ConferenceStub(registration_allow_talk=False)
    attrs = valid_submission()
    del attrs["contribution_type"]
    normalized = normalize_new_submission(attrs, conference=conference)
    assert normalized["contribution_type"] == "poster"
    assert normalized["stay_dates_derived"] is False


def test_normalize_new_submission_derives_and_discards_dates_when_off():
    conference = ConferenceStub(registration_collect_dates=False)
    attrs = valid_submission(
        arrival_date=date(2027, 1, 1), departure_date=date(2027, 1, 5)
    )
    normalized = normalize_new_submission(attrs, conference=conference)
    assert (normalized["arrival_date"], normalized["departure_date"]) == (START, END)
    assert normalized["stay_dates_derived"] is True


@pytest.mark.parametrize("field", ["arrival_date", "departure_date"])
def test_normalize_new_submission_requires_collected_dates(field):
    attrs = valid_submission()
    del attrs[field]
    with pytest.raises(ValidationError) as caught:
        normalize_new_submission(attrs, conference=ConferenceStub())
    assert field in caught.value.message_dict


def test_normalize_new_submission_enforces_strict_dates_when_on():
    attrs = valid_submission(departure_date=START)
    with pytest.raises(ValidationError) as caught:
        normalize_new_submission(attrs, conference=ConferenceStub())
    assert "departure_date" in caught.value.message_dict


def test_public_update_discards_injected_dates_and_preserves_provenance_when_off():
    conference = ConferenceStub(registration_collect_dates=False)
    instance = SubmissionStub(stay_dates_derived=True)
    attrs = {"arrival_date": date(2027, 1, 1), "departure_date": date(2027, 1, 2)}
    normalized = normalize_submission_update(
        attrs, instance=instance, conference=conference, allow_date_override=False
    )
    assert "arrival_date" not in normalized and "departure_date" not in normalized
    assert "stay_dates_derived" not in normalized


def test_public_update_uses_stored_type_for_abstract_validation():
    instance = SubmissionStub(abstract_text="Original")
    attrs = {"abstract_text": " ".join(["word"] * 251)}
    with pytest.raises(ValidationError) as caught:
        normalize_submission_update(
            attrs,
            instance=instance,
            conference=ConferenceStub(),
            allow_date_override=False,
        )
    assert "abstract_text" in caught.value.message_dict


def test_public_update_rejects_clearing_an_existing_talk_title():
    instance = SubmissionStub(abstract_title="Original title")
    with pytest.raises(ValidationError) as caught:
        normalize_submission_update(
            {"abstract_title": ""},
            instance=instance,
            conference=ConferenceStub(),
            allow_date_override=False,
        )
    assert "abstract_title" in caught.value.message_dict


def test_public_update_clears_contribution_fields_for_existing_attend():
    instance = SubmissionStub(
        contribution_type="attend", abstract_title="", abstract_text=""
    )
    attrs = {
        "abstract_title": "Injected title",
        "abstract_text": "Injected abstract",
        "additional_authors": "Injected authors",
        "additional_affiliations": "Injected affiliations",
    }
    normalized = normalize_submission_update(
        attrs,
        instance=instance,
        conference=ConferenceStub(),
        allow_date_override=False,
    )
    assert normalized == dict.fromkeys(attrs, "")


def test_public_update_grandfathers_an_omitted_talk_title():
    normalized = normalize_submission_update(
        {"name": "New name"},
        instance=SubmissionStub(abstract_title="Original title"),
        conference=ConferenceStub(),
        allow_date_override=False,
    )
    assert normalized == {"name": "New name"}


@pytest.mark.parametrize("contribution_type", ["talk", "poster"])
def test_public_update_requires_a_title_when_changing_to_a_contribution(
    contribution_type,
):
    instance = SubmissionStub(
        contribution_type="attend", abstract_title="", abstract_text=""
    )
    with pytest.raises(ValidationError) as caught:
        normalize_submission_update(
            {"contribution_type": contribution_type},
            instance=instance,
            conference=ConferenceStub(),
            allow_date_override=False,
        )
    assert "abstract_title" in caught.value.message_dict


def test_public_update_records_real_date_override_and_preserves_unchanged_provenance():
    instance = SubmissionStub(stay_dates_derived=True)
    changed = normalize_submission_update(
        {"arrival_date": date(2026, 5, 2)},
        instance=instance,
        conference=ConferenceStub(),
        allow_date_override=False,
    )
    assert changed["stay_dates_derived"] is False
    unchanged = normalize_submission_update(
        {"arrival_date": START},
        instance=instance,
        conference=ConferenceStub(),
        allow_date_override=False,
    )
    assert "stay_dates_derived" not in unchanged


def test_update_without_dates_skips_legacy_equal_ordering():
    instance = SubmissionStub(departure_date=START, stay_dates_derived=True)
    normalized = normalize_submission_update(
        {"info": "Vegetarian"},
        instance=instance,
        conference=ConferenceStub(),
        allow_date_override=False,
    )
    assert normalized == {"info": "Vegetarian"}


def test_admin_update_accepts_equal_dates_when_off_and_strict_dates_when_on():
    instance = SubmissionStub(stay_dates_derived=True)
    attrs = {"arrival_date": START, "departure_date": START}
    off = normalize_submission_update(
        attrs,
        instance=instance,
        conference=ConferenceStub(registration_collect_dates=False),
        allow_date_override=True,
    )
    assert off["stay_dates_derived"] is False
    with pytest.raises(ValidationError):
        normalize_submission_update(
            attrs,
            instance=instance,
            conference=ConferenceStub(),
            allow_date_override=True,
        )
