"""CSV import engine for pre-registered participants.

Framework-light helpers shared by the Django-admin import wizard
(``core/admin.py``): decode and parse a CSV export, map its headers onto
``ParticipantSubmission`` fields, validate every row, and create the
submissions.

Design notes
------------
* CSV only (stdlib ``csv``); the project keeps its dependency list minimal.
* A header maps onto a field automatically when it matches the field name
  ignoring case, spaces and punctuation (``Abstract Title`` -> ``abstract_title``).
  Every other column can be mapped to a field by hand on the preview screen.
* Imported rows become **pending** ``ParticipantSubmission`` rows: each carries
  a ``tracking_token`` (the registration link distributed later) but stays
  invisible until an admin publishes it.
* Stay dates follow the conference registration policy: explicitly mapped and
  required when collected, otherwise derived and marked with provenance.
* Duplicate emails -- within the file or already present in the conference --
  are warned about and skipped, never created. Re-running the import is
  therefore idempotent.
"""

from __future__ import annotations

import csv
import io
import re
from dataclasses import dataclass, field
from datetime import date

from django.core.exceptions import ValidationError
from django.core.validators import validate_email

from .models import Conference, Participant, ParticipantSubmission
from .registration import DATE_FIELDS
from .serializers import ParticipantSubmissionImportSerializer

STATUS_OK = "ok"
STATUS_WARNING = "warning"
STATUS_ERROR = "error"

# A safety cap so a huge upload cannot exhaust memory or bloat the session.
MAX_ROWS = 10000

# Managed by the app, never taken from the CSV.
_EXCLUDED_FIELDS = frozenset(
    {
        "id",
        "conference",
        "photo",
        "status",
        "submitted_at",
        "reviewed_at",
        "rejection_message",
        "published_participant",
        "published_abstract",
        "tracking_token",
        "linked_user",
        "stay_dates_derived",
    }
)

# Fields that accept several source columns, whose values are merged.
MERGEABLE_FIELDS = frozenset({"admin_notes"})

_TRUE_VALUES = frozenset({"1", "true", "yes", "y", "ano"})
_FALSE_VALUES = frozenset({"0", "false", "no", "n", "ne", ""})

_CONTRIBUTION_VALUES = {
    "talk": "talk",
    "prednaska": "talk",
    "přednáška": "talk",
    "poster": "poster",
    "attend": "attend",
    "ucast": "attend",
    "účast": "attend",
    "just attend": "attend",
}


class ImportFileError(Exception):
    """A file-level problem (empty file, no rows, unmappable required columns)."""


def _build_importable_fields() -> list[tuple[str, str]]:
    fields: list[tuple[str, str]] = []
    for model_field in ParticipantSubmission._meta.get_fields():
        if not getattr(model_field, "concrete", False):
            continue
        if not getattr(model_field, "editable", False):
            continue
        if model_field.name in _EXCLUDED_FIELDS:
            continue
        fields.append((model_field.name, str(model_field.verbose_name).capitalize()))
    return fields


def importable_fields(conference: Conference) -> list[tuple[str, str]]:
    fields = _build_importable_fields()
    if conference.registration_collect_dates:
        return fields
    return [(name, label) for name, label in fields if name not in DATE_FIELDS]


def required_fields(conference: Conference) -> tuple[str, ...]:
    fields = ("name", "email", "affiliation")
    if conference.registration_collect_dates:
        return (*fields, *DATE_FIELDS)
    return fields


_LABELS = dict(_build_importable_fields())


def _build_max_lengths() -> dict[str, int]:
    limits: dict[str, int] = {}
    for model_field in ParticipantSubmission._meta.get_fields():
        if not getattr(model_field, "concrete", False):
            continue
        limit = getattr(model_field, "max_length", None)
        if limit:
            limits[model_field.name] = limit
    return limits


_MAX_LENGTHS = _build_max_lengths()


def field_label(name: str) -> str:
    return _LABELS.get(name, name)


def _normalize(value: str) -> str:
    return re.sub(r"[^a-z0-9]", "", value.lower())


def decode_csv_bytes(data: bytes) -> str:
    """Decode CSV bytes, tolerating a UTF-8 BOM and Czech Windows-1250."""
    for encoding in ("utf-8-sig", "cp1250", "latin-1"):
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            continue
    raise ImportFileError("Could not decode the file; use UTF-8 or Windows-1250.")


def _detect_delimiter(text: str) -> str:
    lines = text.splitlines()
    first_line = lines[0] if lines else ""
    counts = {delimiter: 0 for delimiter in (",", "\t", ";")}
    in_quotes = False
    for char in first_line:
        if char == '"':
            in_quotes = not in_quotes
        elif not in_quotes and char in counts:
            counts[char] += 1
    best = max(counts, key=lambda delimiter: counts[delimiter])
    return best if counts[best] else ","


@dataclass
class ParsedCsv:
    headers: list[str]
    records: list[list[str]]
    line_numbers: list[int]


def parse_csv(text: str) -> ParsedCsv:
    reader = csv.reader(io.StringIO(text), delimiter=_detect_delimiter(text))
    rows_iter = iter(reader)
    try:
        header = next(rows_iter)
    except StopIteration:
        raise ImportFileError("The CSV file is empty.") from None

    headers = [cell.strip() for cell in header]
    records: list[list[str]] = []
    line_numbers: list[int] = []
    for record in rows_iter:
        line = reader.line_num
        if not any((cell or "").strip() for cell in record):
            continue
        records.append(record)
        line_numbers.append(line)
        if len(records) > MAX_ROWS:
            raise ImportFileError(f"The CSV file has more than {MAX_ROWS} data rows.")

    if not records:
        raise ImportFileError("The CSV file has a header but no data rows.")

    return ParsedCsv(headers=headers, records=records, line_numbers=line_numbers)


@dataclass
class ColumnMapping:
    field_to_indices: dict[str, list[int]]
    # (index, header, current choice) for every column the admin may (re)map.
    configurable: list[tuple[int, str, str]]
    # Columns whose chosen field could not be applied (unknown or already taken).
    conflicts: list[tuple[int, str]]
    # Auto-matched columns: (header, field label).
    recognized: list[tuple[str, str]]


def resolve_mapping(
    headers: list[str],
    conference: Conference,
    manual: dict[int, str] | None = None,
) -> ColumnMapping:
    manual = manual or {}
    importable = importable_fields(conference)
    field_names = frozenset(name for name, _ in importable)
    by_norm = {_normalize(name): name for name in field_names}
    field_to_indices: dict[str, list[int]] = {}
    configurable: list[tuple[int, str, str]] = []
    conflicts: list[tuple[int, str]] = []
    recognized: list[tuple[str, str]] = []

    for index, header in enumerate(headers):
        if index in manual:
            choice = manual[index]
            explicit = True
        else:
            auto = by_norm.get(_normalize(header))
            choice = auto if auto is not None else ""
            explicit = False

        applied = False
        if (
            choice
            and choice in field_names
            and (choice in MERGEABLE_FIELDS or choice not in field_to_indices)
        ):
            field_to_indices.setdefault(choice, []).append(index)
            applied = True

        if not applied and choice:
            conflicts.append((index, header))
        if explicit or not applied:
            configurable.append((index, header, choice))
        else:
            recognized.append((header, field_label(choice)))

    return ColumnMapping(field_to_indices, configurable, conflicts, recognized)


def parsed_to_session(parsed: ParsedCsv) -> dict:
    return {
        "headers": parsed.headers,
        "records": parsed.records,
        "line_numbers": parsed.line_numbers,
    }


def parsed_from_session(data: dict) -> ParsedCsv:
    return ParsedCsv(
        headers=list(data["headers"]),
        records=[list(record) for record in data["records"]],
        line_numbers=list(data["line_numbers"]),
    )


@dataclass
class RowResult:
    line: int
    values: dict[str, str]
    payload: dict
    status: str
    messages: list[str] = field(default_factory=list)

    @property
    def will_import(self) -> bool:
        return self.status == STATUS_OK


def _row_values(record: list[str], mapping: ColumnMapping) -> dict[str, str]:
    values: dict[str, str] = {}
    for name, indices in mapping.field_to_indices.items():
        parts = [
            record[index].strip()
            for index in indices
            if index < len(record) and record[index] and record[index].strip()
        ]
        values[name] = "\n".join(parts)
    return values


def _duplicate_message(
    email: str,
    has_errors: bool,
    existing: set[str],
    seen: dict[str, int],
    line: int,
) -> str | None:
    if not email or has_errors:
        return None
    key = email.lower()
    if key in existing:
        return "Duplicate: email already exists in this conference - skipped."
    if key in seen:
        return f"Duplicate: email also on line {seen[key]} - skipped."
    seen[key] = line
    return None


def _typed_payload(values: dict[str, str], errors: list[str]) -> dict:
    payload: dict = {}
    for name, value in values.items():
        if name == "is_student":
            normalized = value.strip().lower()
            if normalized in _TRUE_VALUES:
                payload[name] = True
            elif normalized in _FALSE_VALUES:
                payload[name] = False
            else:
                errors.append(f'{field_label(name)} must be yes or no (got "{value}").')
        elif name == "contribution_type":
            if not value.strip():
                continue
            contribution_type = _CONTRIBUTION_VALUES.get(value.strip().lower())
            if contribution_type is None:
                errors.append(
                    f'{field_label(name)} must be Talk, Poster, or Just attend (got "{value}").'
                )
            else:
                payload[name] = contribution_type
        elif name in DATE_FIELDS:
            if value:
                if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
                    errors.append(
                        f"{field_label(name)} is not a valid date (use YYYY-MM-DD)."
                    )
                else:
                    try:
                        payload[name] = date.fromisoformat(value)
                    except ValueError:
                        errors.append(
                            f"{field_label(name)} is not a valid date (use YYYY-MM-DD)."
                        )
        else:
            payload[name] = value
    return payload


def validate_rows(
    parsed: ParsedCsv,
    mapping: ColumnMapping,
    conference: Conference,
) -> list[RowResult]:
    existing: set[str] = set()
    existing.update(
        email.strip().lower()
        for email in ParticipantSubmission.objects.filter(
            conference=conference
        ).values_list("email", flat=True)
        if email
    )
    existing.update(
        email.strip().lower()
        for email in Participant.objects.filter(conference=conference).values_list(
            "email", flat=True
        )
        if email
    )

    seen: dict[str, int] = {}
    results: list[RowResult] = []
    for line, record in zip(parsed.line_numbers, parsed.records, strict=True):
        values = _row_values(record, mapping)
        errors: list[str] = []

        name = values.get("name", "")
        email = values.get("email", "")
        if not name:
            errors.append("Name is required.")
        if not email:
            errors.append("Email is required.")
        else:
            try:
                validate_email(email)
            except ValidationError:
                errors.append(f'"{email}" is not a valid email address.')

        for name_key, limit in _MAX_LENGTHS.items():
            if name_key in values and len(values[name_key]) > limit:
                errors.append(
                    f"{field_label(name_key)} is longer than {limit} characters."
                )

        payload = _typed_payload(values, errors)
        serializer = ParticipantSubmissionImportSerializer(
            data=payload, context={"conference": conference}
        )
        if serializer.is_valid():
            normalized = serializer.validated_data
            if isinstance(normalized, dict):
                payload = normalized
        else:
            for field_name, field_messages in serializer.errors.items():
                for message in field_messages:
                    if field_name == "non_field_errors":
                        errors.append(str(message))
                    elif message == "This field is required.":
                        errors.append(f"{field_label(field_name)} is required.")
                    else:
                        errors.append(f"{field_label(field_name)}: {message}")

        duplicate = _duplicate_message(email, bool(errors), existing, seen, line)
        messages = list(errors)
        if len(record) != len(parsed.headers):
            messages.append(
                f"Row has {len(record)} columns; the header has {len(parsed.headers)}."
            )
        if duplicate:
            messages.append(duplicate)

        if errors:
            status = STATUS_ERROR
        elif duplicate:
            status = STATUS_WARNING
        else:
            status = STATUS_OK

        results.append(
            RowResult(
                line=line,
                values=values,
                payload=payload,
                status=status,
                messages=messages,
            )
        )
    return results


@dataclass
class ImportSummary:
    created: int
    skipped: int
    failed: int


def summarise(results: list[RowResult]) -> ImportSummary:
    created = sum(1 for r in results if r.status == STATUS_OK)
    skipped = sum(1 for r in results if r.status == STATUS_WARNING)
    failed = sum(1 for r in results if r.status == STATUS_ERROR)
    return ImportSummary(created=created, skipped=skipped, failed=failed)


def create_submissions(
    results: list[RowResult], conference: Conference
) -> ImportSummary:
    """Create a pending submission for every ``ok`` row."""
    for result in results:
        if result.status != STATUS_OK:
            continue
        serializer = ParticipantSubmissionImportSerializer(
            data=result.payload, context={"conference": conference}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save(conference=conference)
    return summarise(results)
