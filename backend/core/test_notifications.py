"""Tests for the notification outbox, Celery task and drain command."""

from datetime import date, timedelta
from io import StringIO
from types import SimpleNamespace
from typing import Any, cast

import pytest
from django.contrib import admin
from django.core import mail
from django.core.mail import EmailMessage
from django.core.management import CommandError, call_command
from django.test import RequestFactory
from django.test import TestCase as _DjangoTestCase
from django.utils import timezone
from rest_framework.test import APIClient

from .admin import NotificationAdmin
from .conftest import api
from .models import Notification, ParticipantSubmission
from .notifications import notify_submission_received
from .notifications.tasks import send_notification

pytestmark = pytest.mark.django_db

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

INFO_DESK_EMAIL = "info-desk@example.com"


@pytest.fixture(autouse=True)
def _notification_settings(settings):
    # Celery's Django fixup listens to setting_changed, so assigning the
    # setting puts the worker into eager mode without a broker.
    settings.CELERY_TASK_ALWAYS_EAGER = True
    settings.PUBLIC_BASE_URL = "https://conf.example/"


def capture_on_commit_callbacks():
    # Django 6.1 removed the standalone
    # django.test.utils.django_capture_on_commit_callbacks helper; the same
    # context manager survives as a (classmethod) TestCase method.
    return _DjangoTestCase.captureOnCommitCallbacks(execute=True)


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


def make_notification(conference, **overrides):
    data = {
        "conference": conference,
        "kind": "submission_received",
        "audience": "participant",
        "recipient": "jane@example.com",
        "subject": "Subject",
        "body": "Body",
    }
    data.update(overrides)
    return Notification.objects.create(**data)


def make_reference(conference, submission):
    return f"{conference.slug}-{submission.pk:04d}"


def make_tracking_url(conference, submission):
    return f"https://conf.example/{conference.slug}/#/track/{submission.tracking_token}"


def messages_to(address):
    return [message for message in mail.outbox if message.to == [address]]


class _RetryScheduled(Exception):
    """Sentinel raised by the task stub instead of scheduling a real retry."""


class _MailError(Exception):
    """Raised by the monkeypatched EmailMessage.send."""


class _TaskStub:
    """Minimal stand-in for the bound Celery task instance (``self``)."""

    def __init__(self, retries, max_retries=3):
        self.request = SimpleNamespace(retries=retries)
        self.max_retries = max_retries
        self.retry_calls = []

    def retry(self, *args, **kwargs):
        self.retry_calls.append(kwargs)
        raise _RetryScheduled


def _raise_mail_error(self, *args, **kwargs):
    raise _MailError("smtp connection lost")


def apply_task(notification_id):
    cast("Any", send_notification).apply(args=[notification_id])


def run_task(stub, notification_id):
    # Celery binds .run to the registered task; .__func__ is the raw body,
    # which lets the stub stand in for the task instance.
    cast("Any", send_notification).run.__func__(stub, notification_id)


class TestTaskRegistration:
    def test_send_notification_is_registered(self):
        # Autodiscovery does not recurse into core/notifications/; the task
        # arrives via CELERY_IMPORTS or the worker would never run it.
        from backend.celery import app

        app.loader.import_default_modules()

        assert "core.notifications.tasks.send_notification" in app.tasks


class TestSubmissionReceived:
    def setup_method(self):
        self.client = APIClient()

    def test_post_sends_the_participant_confirmation(self, wsc):
        with capture_on_commit_callbacks():
            response = self.client.post(api("submit/"), CREATE_PAYLOAD, format="json")

        assert response.status_code == 201
        submission = ParticipantSubmission.objects.get(conference=wsc)
        reference = make_reference(wsc, submission)

        assert Notification.objects.filter(conference=wsc).count() == 1
        notification = Notification.objects.get(
            conference=wsc, kind="submission_received", audience="participant"
        )
        assert notification.status == "sent"
        assert notification.recipient == "jane@example.com"
        assert notification.submission == submission
        assert notification.sent_at is not None

        assert len(mail.outbox) == 1
        message = mail.outbox[0]
        assert message.to == ["jane@example.com"]
        assert reference in message.body
        assert make_tracking_url(wsc, submission) in message.body

    def test_post_copies_the_organizer_without_the_tracking_link(self, wsc):
        wsc.info_desk_email = INFO_DESK_EMAIL
        wsc.save()

        with capture_on_commit_callbacks():
            response = self.client.post(api("submit/"), CREATE_PAYLOAD, format="json")

        assert response.status_code == 201
        submission = ParticipantSubmission.objects.get(conference=wsc)
        reference = make_reference(wsc, submission)

        assert Notification.objects.filter(conference=wsc).count() == 2
        organizer = Notification.objects.get(
            conference=wsc, kind="submission_received", audience="organizer"
        )
        assert organizer.recipient == INFO_DESK_EMAIL
        assert organizer.status == "sent"

        assert len(mail.outbox) == 2
        organizer_messages = messages_to(INFO_DESK_EMAIL)
        assert len(organizer_messages) == 1
        body = organizer_messages[0].body
        assert reference in body
        assert "jane@example.com" in body
        assert submission.tracking_token not in body
        assert "/#/track" not in body

    def test_post_without_an_info_desk_sends_no_organizer_copy(self, wsc):
        with capture_on_commit_callbacks():
            response = self.client.post(api("submit/"), CREATE_PAYLOAD, format="json")

        assert response.status_code == 201
        assert not Notification.objects.filter(audience="organizer").exists()
        assert len(mail.outbox) == 1


class TestServiceDedupe:
    def test_repeated_notify_enqueues_only_one_message(self, wsc):
        submission = make_submission(wsc)

        with capture_on_commit_callbacks():
            notify_submission_received(submission)
            notify_submission_received(submission)

        participants = Notification.objects.filter(
            kind="submission_received", audience="participant"
        )
        assert participants.count() == 1
        notification = participants.get()
        assert notification.status == "sent"
        assert (
            Notification.objects.filter(
                dedupe_key=f"submission_received:participant:{submission.pk}"
            ).count()
            == 1
        )
        assert len(mail.outbox) == 1


class TestTaskIdempotency:
    def test_reprocessing_a_sent_row_is_a_noop(self, wsc):
        notification = make_notification(wsc)

        apply_task(notification.pk)
        notification.refresh_from_db()
        assert notification.status == "sent"
        assert notification.attempts == 1
        assert len(mail.outbox) == 1

        apply_task(notification.pk)
        notification.refresh_from_db()
        assert notification.status == "sent"
        assert notification.attempts == 1
        assert len(mail.outbox) == 1


class TestSubmissionUpdated:
    def setup_method(self):
        self.client = APIClient()

    def test_patch_notifies_the_participant_and_the_organizer(self, wsc):
        wsc.info_desk_email = INFO_DESK_EMAIL
        wsc.save()
        submission = make_submission(wsc)

        with capture_on_commit_callbacks():
            response = self.client.patch(
                api(f"track/{submission.tracking_token}/"),
                {"affiliation": "MIT"},
                format="json",
            )

        assert response.status_code == 200

        participant = Notification.objects.get(
            conference=wsc, kind="submission_updated", audience="participant"
        )
        assert participant.status == "sent"
        assert participant.recipient == "jane@example.com"
        assert "Status: Pending" in participant.body
        assert make_tracking_url(wsc, submission) in participant.body

        organizer = Notification.objects.get(
            conference=wsc, kind="submission_updated", audience="organizer"
        )
        assert organizer.recipient == INFO_DESK_EMAIL
        assert organizer.status == "sent"
        # Same rule as the received-organizer copy: the shared mailbox never
        # sees the tracking link (a bearer capability).
        assert submission.tracking_token not in organizer.body
        assert "/#/track" not in organizer.body

        assert len(mail.outbox) == 2

    def test_patch_after_approval_says_it_went_back_to_review(self, wsc):
        wsc.info_desk_email = INFO_DESK_EMAIL
        wsc.save()
        submission = make_submission(wsc)
        submission.publish()
        assert len(mail.outbox) == 1  # the existing publish signal mail
        mail.outbox.clear()

        with capture_on_commit_callbacks():
            response = self.client.patch(
                api(f"track/{submission.tracking_token}/"),
                {"abstract_text": "Participant-edited text"},
                format="json",
            )

        assert response.status_code == 200
        submission.refresh_from_db()
        assert submission.status == "pending"

        participant = Notification.objects.get(
            conference=wsc, kind="submission_updated", audience="participant"
        )
        assert "returned to review" in participant.body

        organizer = Notification.objects.get(
            conference=wsc, kind="submission_updated", audience="organizer"
        )
        assert organizer.recipient == INFO_DESK_EMAIL
        assert "returned it to review" in " ".join(organizer.body.split())

        assert len(mail.outbox) == 2


class TestBlankRecipient:
    def test_blank_submission_email_creates_no_rows(self, wsc):
        # ORM-only on purpose: the API requires an e-mail, so a blank one
        # can only reach the service from a code path outside registration.
        submission = make_submission(wsc)
        submission.email = ""

        with capture_on_commit_callbacks():
            notify_submission_received(submission)

        assert Notification.objects.count() == 0
        assert len(mail.outbox) == 0


class TestBrokerOutage:
    def setup_method(self):
        self.client = APIClient()

    def test_enqueue_failure_marks_the_row_failed_but_keeps_the_201(
        self, wsc, monkeypatch
    ):
        def boom(*args, **kwargs):
            raise ConnectionError("broker refused connection")

        monkeypatch.setattr(send_notification, "delay", boom)

        with capture_on_commit_callbacks():
            response = self.client.post(api("submit/"), CREATE_PAYLOAD, format="json")

        assert response.status_code == 201
        notification = Notification.objects.get(conference=wsc)
        assert notification.status == "failed"
        assert notification.last_error.startswith("enqueue failed")
        assert len(mail.outbox) == 0


class TestTaskRetries:
    def test_non_terminal_failure_keeps_the_row_retrying(self, wsc, monkeypatch):
        notification = make_notification(wsc)
        monkeypatch.setattr(EmailMessage, "send", _raise_mail_error)
        stub = _TaskStub(retries=0, max_retries=3)

        with pytest.raises(_RetryScheduled):
            run_task(stub, notification.pk)

        notification.refresh_from_db()
        assert notification.status == "retrying"
        assert notification.attempts == 1
        assert "smtp connection lost" in notification.last_error
        assert len(stub.retry_calls) == 1
        retry_kwargs = stub.retry_calls[0]
        assert isinstance(retry_kwargs["exc"], _MailError)
        assert retry_kwargs["countdown"] == 60
        assert len(mail.outbox) == 0

    def test_terminal_failure_marks_the_row_failed(self, wsc, monkeypatch):
        notification = make_notification(wsc)
        monkeypatch.setattr(EmailMessage, "send", _raise_mail_error)
        stub = _TaskStub(retries=3, max_retries=3)

        with pytest.raises(_MailError):
            run_task(stub, notification.pk)

        notification.refresh_from_db()
        assert notification.status == "failed"
        assert notification.attempts == 1
        assert "smtp connection lost" in notification.last_error
        assert stub.retry_calls == []
        assert len(mail.outbox) == 0

    def test_success_after_a_failure(self, wsc, monkeypatch):
        notification = make_notification(wsc)
        real_send = EmailMessage.send
        failing = {"active": True}

        def flaky_send(self, *args, **kwargs):
            if failing["active"]:
                raise _MailError("smtp connection lost")
            return real_send(self, *args, **kwargs)

        monkeypatch.setattr(EmailMessage, "send", flaky_send)

        with pytest.raises(_RetryScheduled):
            run_task(_TaskStub(retries=0), notification.pk)
        notification.refresh_from_db()
        assert notification.status == "retrying"
        assert notification.attempts == 1

        failing["active"] = False
        run_task(_TaskStub(retries=1), notification.pk)

        notification.refresh_from_db()
        assert notification.status == "sent"
        assert notification.attempts == 2
        assert notification.last_error == ""
        assert notification.sent_at is not None
        assert len(mail.outbox) == 1
        assert mail.outbox[0].to == ["jane@example.com"]


class TestDrainCommand:
    def test_dry_run_reports_pending_rows_and_changes_nothing(self, wsc):
        make_notification(wsc, status="pending")
        make_notification(wsc, status="retrying")
        out = StringIO()

        call_command("send_pending_notifications", "--dry-run", stdout=out)

        assert "Would enqueue 1 notification(s)." in out.getvalue()
        assert set(Notification.objects.values_list("status", flat=True)) == {
            "pending",
            "retrying",
        }
        assert len(mail.outbox) == 0

    def test_enqueues_failed_rows(self, wsc, monkeypatch):
        notification = make_notification(wsc, status="failed")
        enqueued = []
        monkeypatch.setattr(send_notification, "delay", enqueued.append)
        out = StringIO()

        call_command("send_pending_notifications", stdout=out)

        assert enqueued == [notification.pk]
        assert "Enqueued 1 of 1 notification(s)." in out.getvalue()

    def test_stuck_retrying_sweep(self, wsc, monkeypatch):
        aged = make_notification(wsc, status="retrying")
        Notification.objects.filter(pk=aged.pk).update(
            created_at=timezone.now() - timedelta(hours=2)
        )
        make_notification(wsc, status="retrying")  # fresh: still in flight
        out = StringIO()

        call_command(
            "send_pending_notifications",
            "--status",
            "pending,failed,retrying",
            "--stuck-retrying-minutes",
            "60",
            "--dry-run",
            stdout=out,
        )
        assert "Would enqueue 1 notification(s)." in out.getvalue()

        enqueued = []
        monkeypatch.setattr(send_notification, "delay", enqueued.append)
        out = StringIO()
        call_command(
            "send_pending_notifications",
            "--status",
            "pending,failed,retrying",
            "--stuck-retrying-minutes",
            "60",
            stdout=out,
        )
        assert enqueued == [aged.pk]
        assert "Enqueued 1 of 1 notification(s)." in out.getvalue()

    def test_retrying_requires_the_stuck_flag(self, wsc):
        with pytest.raises(CommandError, match="--stuck-retrying-minutes"):
            call_command("send_pending_notifications", "--status", "retrying")


class TestAdminResend:
    def test_resend_enqueues_only_pending_and_failed_rows(self, wsc, monkeypatch):
        pending = make_notification(wsc, status="pending")
        failed = make_notification(wsc, status="failed")
        make_notification(wsc, status="sent")
        make_notification(wsc, status="retrying")

        enqueued = []
        monkeypatch.setattr(send_notification, "delay", enqueued.append)
        model_admin = NotificationAdmin(Notification, admin.site)
        reported = []
        monkeypatch.setattr(
            model_admin,
            "message_user",
            lambda request, message, level: reported.append(message),
        )
        request = RequestFactory().get("/admin/core/notification/")

        model_admin.resend(request, Notification.objects.all())

        assert sorted(enqueued) == sorted([pending.pk, failed.pk])
        assert reported == ["Re-enqueued 2 of 2 notification(s)."]


class TestCrossConferenceIsolation:
    def setup_method(self):
        self.client = APIClient()

    def test_other_conference_uses_its_own_slug_and_info_desk(self, wsc, other):
        wsc.info_desk_email = "wsc-desk@example.com"
        wsc.save()
        other.info_desk_email = "other-desk@example.com"
        other.save()

        with capture_on_commit_callbacks():
            response = self.client.post(
                api("submit/", slug=other.slug), CREATE_PAYLOAD, format="json"
            )

        assert response.status_code == 201
        submission = ParticipantSubmission.objects.get(conference=other)

        participant = Notification.objects.get(conference=other, audience="participant")
        assert make_tracking_url(other, submission) in participant.body

        organizer = Notification.objects.get(conference=other, audience="organizer")
        assert organizer.recipient == "other-desk@example.com"
        assert not Notification.objects.filter(
            recipient="wsc-desk@example.com"
        ).exists()


class TestRejectedSubmissionEdit:
    def setup_method(self):
        self.client = APIClient()

    def test_patch_rejected_submission_sends_nothing(self, wsc):
        submission = make_submission(wsc)
        submission.reject("Not accepted")

        with capture_on_commit_callbacks():
            response = self.client.patch(
                api(f"track/{submission.tracking_token}/"),
                {"affiliation": "MIT"},
                format="json",
            )

        assert response.status_code == 403
        assert Notification.objects.count() == 0
        assert len(mail.outbox) == 0
