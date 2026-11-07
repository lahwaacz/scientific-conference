"""Pure registration policy shared by models, serializers and importers."""

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date
from typing import Final, Protocol

from django.core.exceptions import ValidationError

type ErrorDict = dict[str, list[str]]

CONFIGURATION_FIELDS: Final = (
    "submission_edit_deadline",
    "registration_deadline",
    "date_start",
    "date_end",
    "registration_collect_dates",
    "registration_allow_talk",
    "registration_allow_poster",
    "registration_allow_attend",
)
ATTEND_FIELDS: Final = (
    "abstract_title",
    "abstract_text",
    "additional_authors",
    "additional_affiliations",
)
DATE_FIELDS: Final = ("arrival_date", "departure_date")
DATES_REQUIRED: Final = "Both conference dates are required for derived stays."
DATE_ORDER_ERROR: Final = "Conference end date must be on or after the start date."


class ConferencePolicy(Protocol):
    @property
    def date_start(self) -> date | None: ...

    @property
    def date_end(self) -> date | None: ...

    @property
    def registration_collect_dates(self) -> bool: ...

    @property
    def allowed_contribution_types(self) -> tuple[str, ...]: ...


class SubmissionPolicy(Protocol):
    @property
    def contribution_type(self) -> str: ...

    @property
    def abstract_title(self) -> str: ...

    @property
    def arrival_date(self) -> date | None: ...

    @property
    def departure_date(self) -> date | None: ...


@dataclass(frozen=True, slots=True)
class SubmissionSnapshot:
    contribution_type: str
    abstract_title: str
    arrival_date: date | None
    departure_date: date | None


def _text(value) -> str:
    return value if isinstance(value, str) else ""


def _date(value) -> date | None:
    return value if isinstance(value, date) else None


def validate_conference_configuration[Value](
    values: Mapping[str, Value],
) -> ErrorDict:
    errors: ErrorDict = {}
    start = _date(values.get("date_start"))
    end = _date(values.get("date_end"))
    deadline = _date(values.get("submission_edit_deadline"))
    registration_deadline = _date(values.get("registration_deadline"))

    if deadline is not None:
        if registration_deadline is not None and deadline < registration_deadline:
            errors.setdefault("submission_edit_deadline", []).append(
                "Submission editing deadline must be on or after the registration deadline."
            )
        if end is not None and deadline > end:
            errors.setdefault("submission_edit_deadline", []).append(
                "Submission editing deadline must be on or before the conference end date."
            )

    if not any(values.get(field) for field in CONFIGURATION_FIELDS[-3:]):
        errors["registration_allow_talk"] = [
            "At least one contribution type must be allowed."
        ]

    if start is not None and end is not None:
        if start > end:
            errors["date_end"] = [DATE_ORDER_ERROR]
        if start == end and values.get("registration_collect_dates", True):
            errors["registration_collect_dates"] = [
                "Participant dates cannot be collected for a single-day conference."
            ]

    if not values.get("registration_collect_dates", True):
        for field, value in (("date_start", start), ("date_end", end)):
            if value is None:
                errors[field] = [DATES_REQUIRED]
    return errors


def derived_stay_dates(conference: ConferencePolicy) -> tuple[date, date]:
    start = _date(conference.date_start)
    end = _date(conference.date_end)
    if start is None or end is None:
        errors = {
            field: [DATES_REQUIRED]
            for field, value in (("date_start", start), ("date_end", end))
            if value is None
        }
        raise ValidationError(errors)
    if start > end:
        raise ValidationError({"date_end": [DATE_ORDER_ERROR]})
    return start, end


def default_contribution_type(conference: ConferencePolicy) -> str:
    if not (allowed := conference.allowed_contribution_types):
        raise ValidationError(
            {"contribution_type": ["Registration is not accepting contributions."]}
        )
    return allowed[0]


def validate_common_fields[Value](
    attrs: Mapping[str, Value],
    *,
    conference: ConferencePolicy,
    instance: SubmissionPolicy | None = None,
    creating: bool,
) -> ErrorDict:
    errors: ErrorDict = {}
    for field in ("name", "email", "affiliation"):
        if (creating or field in attrs) and not _text(attrs.get(field)).strip():
            errors[field] = ["This field is required."]

    affiliation = _text(attrs.get("affiliation")).strip()
    if (creating or "affiliation" in attrs) and affiliation and len(affiliation) < 3:
        errors["affiliation"] = ["Affiliation must be at least 3 characters long."]

    allowed = conference.allowed_contribution_types
    if not allowed:
        errors["contribution_type"] = ["Registration is not accepting contributions."]
    current = instance.contribution_type if instance is not None else None
    supplied = "contribution_type" in attrs
    contribution_type = _text(attrs.get("contribution_type", current))
    contribution_type = contribution_type or next(iter(allowed), "")
    if allowed and contribution_type not in allowed and contribution_type != current:
        errors["contribution_type"] = [
            "This contribution type is not available for this conference."
        ]

    if (
        contribution_type != "attend"
        and "abstract_text" in attrs
        and len(_text(attrs.get("abstract_text")).split()) > 250
    ):
        errors["abstract_text"] = ["Abstract must not exceed 250 words."]

    if contribution_type in ("talk", "poster") and (
        creating
        or "abstract_title" in attrs
        or (supplied and contribution_type != current)
    ):
        supplied_title = attrs.get("abstract_title")
        title = _text(supplied_title)
        if supplied_title is None and instance is not None:
            title = instance.abstract_title
        if not title.strip():
            errors["abstract_title"] = ["Title is required for a talk or poster."]
    return errors


def clear_attend_fields[Value](
    attrs: Mapping[str, Value], *, contribution_type: str | None = None
) -> dict[str, Value | str]:
    normalized: dict[str, Value | str] = dict(attrs)
    if _text(normalized.get("contribution_type", contribution_type)) == "attend":
        for field in ATTEND_FIELDS:
            normalized[field] = ""
    return normalized


def validate_date_order[Value](
    attrs: Mapping[str, Value],
    *,
    instance: SubmissionPolicy | None = None,
    conference: ConferencePolicy,
    dates_supplied: bool,
    creating: bool,
) -> ErrorDict:
    current_arrival = instance.arrival_date if instance is not None else None
    current_departure = instance.departure_date if instance is not None else None
    arrival = _date(attrs.get("arrival_date", current_arrival))
    departure = _date(attrs.get("departure_date", current_departure))
    if arrival is None or departure is None:
        return {}
    if departure < arrival or (
        departure == arrival
        and conference.registration_collect_dates
        and (creating or dates_supplied)
    ):
        return {"departure_date": ["Departure date must be after arrival date"]}
    return {}


def normalize_new_submission[Value](
    attrs: Mapping[str, Value], *, conference: ConferencePolicy
) -> dict[str, Value | str | date | bool]:
    normalized: dict[str, Value | str | date | bool] = dict(attrs)
    if not _text(normalized.get("contribution_type")):
        normalized["contribution_type"] = default_contribution_type(conference)
    errors: ErrorDict = {}
    if conference.registration_collect_dates:
        for field in DATE_FIELDS:
            if normalized.get(field) is None:
                errors[field] = [
                    "This field is required when participant dates are collected."
                ]
    else:
        start, end = derived_stay_dates(conference)
        normalized["arrival_date"] = start
        normalized["departure_date"] = end
    normalized["stay_dates_derived"] = not conference.registration_collect_dates
    normalized = dict(clear_attend_fields(normalized))
    errors.update(
        validate_common_fields(normalized, conference=conference, creating=True)
    )
    errors.update(
        validate_date_order(
            normalized,
            conference=conference,
            dates_supplied=True,
            creating=True,
        )
    )
    if errors:
        raise ValidationError(errors)
    return normalized


def normalize_submission_update[Value](
    attrs: Mapping[str, Value],
    *,
    instance: SubmissionPolicy,
    conference: ConferencePolicy,
    allow_date_override: bool,
) -> dict[str, Value | str | bool]:
    normalized: dict[str, Value | str | bool] = dict(attrs)
    dates_supplied = any(field in normalized for field in DATE_FIELDS)
    if not allow_date_override and not conference.registration_collect_dates:
        for field in DATE_FIELDS:
            normalized.pop(field, None)
        dates_supplied = False
    elif dates_supplied:
        arrival = normalized.get("arrival_date", instance.arrival_date)
        departure = normalized.get("departure_date", instance.departure_date)
        if arrival != instance.arrival_date or departure != instance.departure_date:
            normalized["stay_dates_derived"] = False
    normalized = dict(
        clear_attend_fields(normalized, contribution_type=instance.contribution_type)
    )
    errors = validate_common_fields(
        normalized, conference=conference, instance=instance, creating=False
    )
    errors.update(
        validate_date_order(
            normalized,
            instance=instance,
            conference=conference,
            dates_supplied=dates_supplied,
            creating=False,
        )
    )
    if errors:
        raise ValidationError(errors)
    return normalized
