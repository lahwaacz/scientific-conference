"""Tests for the publish-notification email signal."""

from datetime import date

from django.core import mail
from django.test import TestCase

from .models import ParticipantSubmission


def make_submission(**overrides):
    data = {
        "name": "Jane Doe",
        "email": "jane@example.com",
        "affiliation": "CTU",
        "abstract_title": "Numerical Methods",
        "abstract_text": "Some abstract text",
        "arrival_date": date(2026, 9, 10),
        "departure_date": date(2026, 9, 12),
    }
    data.update(overrides)
    return ParticipantSubmission.objects.create(**data)


class TestPublishEmailSignal(TestCase):
    def test_publish_sends_email_to_participant(self):
        submission = make_submission()

        submission.publish()

        self.assertEqual(len(mail.outbox), 1)
        message = mail.outbox[0]
        self.assertEqual(message.subject, "Your submission has been published")
        self.assertEqual(message.to, ["jane@example.com"])
        self.assertIn("Jane Doe", message.body)
        self.assertIn("Numerical Methods", message.body)

    def test_resaving_approved_submission_sends_no_email(self):
        submission = make_submission()
        submission.publish()
        self.assertEqual(len(mail.outbox), 1)

        submission.name = "Jane D."
        submission.save()

        self.assertEqual(len(mail.outbox), 1)

    def test_submission_without_email_sends_nothing(self):
        submission = make_submission(email="")

        submission.publish()

        self.assertEqual(len(mail.outbox), 0)

    def test_create_with_approved_status_fires_email(self):
        make_submission(status="approved")

        self.assertEqual(len(mail.outbox), 1)

    def test_bulk_queryset_update_bypasses_signal(self):
        submission = make_submission()
        mail.outbox.clear()

        ParticipantSubmission.objects.filter(pk=submission.pk).update(status="approved")

        self.assertEqual(len(mail.outbox), 0)
