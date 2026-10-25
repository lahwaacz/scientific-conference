from typing import Any, cast

from django.conf import settings
from django.db import transaction
from django.template.loader import render_to_string

from core.models import Notification

from .tasks import send_notification


def _reference(submission):
    return f"{submission.conference.slug}-{submission.pk:04d}"


def _absolute_tracking_url(conference, submission):
    return (
        f"{settings.PUBLIC_BASE_URL}"
        f"{conference.slug}/#/track/{submission.tracking_token}"
    )


def _truncate_subject(subject):
    # SQLite does not enforce max_length; an overlong subject would still be
    # an invalid (folded) mail header, so cap it here.
    return subject[:200]


def _render(template_name, context):
    return render_to_string(f"notifications/{template_name}", context)


def enqueue_notification(notification_id) -> bool:
    # A broker outage must never reach the HTTP response: record the failure
    # on the row instead; the drain command re-enqueues it after recovery.
    try:
        cast(Any, send_notification).delay(notification_id)
    except Exception as exc:  # noqa: BLE001
        Notification.objects.filter(pk=notification_id).update(
            status="failed",
            last_error=f"enqueue failed: {exc}"[:2000],
        )
        return False
    return True


def _create(
    *,
    conference,
    kind,
    audience,
    recipient,
    subject,
    body,
    submission,
    dedupe_key=None,
):
    if dedupe_key is not None:
        notification, created = Notification.objects.get_or_create(
            dedupe_key=dedupe_key,
            defaults={
                "conference": conference,
                "kind": kind,
                "audience": audience,
                "recipient": recipient,
                "subject": subject,
                "body": body,
                "submission": submission,
            },
        )
        if not created:
            # A duplicate event (retried request, repeated hook) reuses the
            # existing row without enqueuing another send; if that row's own
            # enqueue was lost, the drain command recovers it, not a repeat hook.
            return notification
    else:
        notification = Notification.objects.create(
            conference=conference,
            kind=kind,
            audience=audience,
            recipient=recipient,
            subject=subject,
            body=body,
            submission=submission,
        )
    # Enqueue only after the surrounding transaction commits, so the task
    # never races an uncommitted row.
    transaction.on_commit(lambda: enqueue_notification(notification.pk))
    return notification


def notify_submission_received(submission):
    if not submission.email:
        return

    conference = submission.conference
    reference = _reference(submission)
    info_desk_email = conference.info_desk_email

    participant_context = {
        "conference": conference,
        "submission": submission,
        "reference": reference,
        "tracking_url": _absolute_tracking_url(conference, submission),
        "info_desk_email": info_desk_email,
    }
    _create(
        conference=conference,
        kind="submission_received",
        audience="participant",
        recipient=submission.email,
        subject=_truncate_subject(
            f"[{conference.title}] Submission received — {reference}"
        ),
        body=_render("submission_received.txt", participant_context),
        submission=submission,
        dedupe_key=f"submission_received:participant:{submission.pk}",
    )

    if info_desk_email:
        organizer_context = {
            "conference": conference,
            "submission": submission,
            "reference": reference,
            "info_desk_email": info_desk_email,
        }
        _create(
            conference=conference,
            kind="submission_received",
            audience="organizer",
            recipient=info_desk_email,
            subject=_truncate_subject(
                f"[{conference.title}] New submission {reference}"
            ),
            body=_render("submission_received_organizer.txt", organizer_context),
            submission=submission,
            dedupe_key=f"submission_received:organizer:{submission.pk}",
        )


def notify_submission_updated(submission, was_approved):
    if not submission.email:
        return

    conference = submission.conference
    reference = _reference(submission)
    info_desk_email = conference.info_desk_email

    participant_context = {
        "conference": conference,
        "submission": submission,
        "reference": reference,
        "tracking_url": _absolute_tracking_url(conference, submission),
        "info_desk_email": info_desk_email,
        "was_approved": was_approved,
    }
    _create(
        conference=conference,
        kind="submission_updated",
        audience="participant",
        recipient=submission.email,
        subject=_truncate_subject(
            f"[{conference.title}] Submission updated — {reference}"
        ),
        body=_render("submission_updated.txt", participant_context),
        submission=submission,
        dedupe_key=None,
    )

    if info_desk_email:
        organizer_context = {
            "conference": conference,
            "submission": submission,
            "reference": reference,
            "info_desk_email": info_desk_email,
            "was_approved": was_approved,
        }
        _create(
            conference=conference,
            kind="submission_updated",
            audience="organizer",
            recipient=info_desk_email,
            subject=_truncate_subject(
                f"[{conference.title}] Submission {reference} updated"
            ),
            body=_render("submission_updated_organizer.txt", organizer_context),
            submission=submission,
            dedupe_key=None,
        )
