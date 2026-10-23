"""The link_gitlab_account management command: reassigning a GitLab social

account to a local staff user (never touching is_staff), and the
--delete-orphan guard honoring Person.user / ParticipantSubmission.linked_user
references.
"""

from io import StringIO

import pytest
from allauth.socialaccount.models import SocialAccount
from django.contrib.auth.models import User
from django.core.management import CommandError, call_command
from django.test import TestCase

from .models import Conference, ParticipantSubmission, Person


class LinkGitlabAccountTestCase(TestCase):
    def setUp(self):
        self.gitlab_user = User.objects.create_user(
            username="alice1", email="alice@example.com"
        )
        self.local_user = User.objects.create_user(
            username="alice-local", email="alice@example.com", is_staff=True
        )
        self.account = SocialAccount.objects.create(
            provider="gitlab",
            uid="123",
            user=self.gitlab_user,
            extra_data={"username": "alice"},
        )

    def run_command(self, *args, delete_orphan=False):
        stdout = StringIO()
        call_command(
            "link_gitlab_account", *args, delete_orphan=delete_orphan, stdout=stdout
        )
        return stdout.getvalue()

    def test_links_account_to_local_user_and_preserves_staff_flags(self):
        output = self.run_command("alice", "alice-local")
        self.account.refresh_from_db()
        self.assertEqual(self.account.user, self.local_user)
        self.local_user.refresh_from_db()
        self.gitlab_user.refresh_from_db()
        self.assertTrue(self.local_user.is_staff)
        self.assertFalse(self.gitlab_user.is_staff)
        # Orphan not deleted unless explicitly requested.
        self.assertTrue(User.objects.filter(username="alice1").exists())
        self.assertIn("alice-local", output)

    def test_matches_by_uid_when_username_differs(self):
        output = self.run_command("123", "alice-local")
        self.account.refresh_from_db()
        self.assertEqual(self.account.user, self.local_user)
        self.assertIn("alice-local", output)

    def test_already_linked_is_a_noop_but_succeeds(self):
        self.account.user = self.local_user
        self.account.save()
        output = self.run_command("alice", "alice-local")
        self.assertIn("already linked", output)

    def test_unknown_local_user_fails(self):
        with pytest.raises(CommandError):
            self.run_command("alice", "no-such-user")

    def test_unknown_gitlab_account_fails(self):
        with pytest.raises(CommandError):
            self.run_command("bob", "alice-local")

    def test_delete_orphan_removes_unreferenced_user(self):
        self.run_command("alice", "alice-local", delete_orphan=True)
        self.assertFalse(User.objects.filter(username="alice1").exists())

    def test_delete_orphan_keeps_user_referenced_by_person(self):
        conference = Conference.objects.get_or_create(slug="wsc2026-test")[0]
        Person.objects.create(
            conference=conference, name="Alice", user=self.gitlab_user
        )
        output = self.run_command("alice", "alice-local", delete_orphan=True)
        self.assertTrue(User.objects.filter(username="alice1").exists())
        self.assertIn("Keeping user", output)

    def test_delete_orphan_keeps_user_referenced_by_submission(self):
        conference = Conference.objects.get_or_create(slug="wsc2026-test")[0]
        ParticipantSubmission.objects.create(
            conference=conference,
            name="Alice",
            email="alice@example.com",
            affiliation="CU",
            arrival_date="2026-06-01",
            departure_date="2026-06-05",
            linked_user=self.gitlab_user,
        )
        output = self.run_command("alice", "alice-local", delete_orphan=True)
        self.assertTrue(User.objects.filter(username="alice1").exists())
        self.assertIn("Keeping user", output)
