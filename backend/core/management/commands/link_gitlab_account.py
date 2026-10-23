from allauth.socialaccount.models import SocialAccount
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db.models import Q

from core.models import ParticipantSubmission, Person


class Command(BaseCommand):
    help = (
        "Reassign a GitLab social account to an existing local user, e.g. "
        "after the first GitLab login auto-created a separate user. "
        "is_staff is never modified."
    )

    def add_arguments(self, parser):
        parser.add_argument("gitlab_username")
        parser.add_argument("local_username")
        parser.add_argument(
            "--delete-orphan",
            action="store_true",
            help="Delete the previous owner of the social account if nothing "
            "references it (no Person.user / ParticipantSubmission.linked_user).",
        )

    def handle(self, gitlab_username, local_username, delete_orphan, **options):
        user_model = get_user_model()
        try:
            local_user = user_model.objects.get(username=local_username)
        except user_model.DoesNotExist:
            raise CommandError(
                f"Local user {local_username!r} does not exist."
            ) from None

        account = (
            SocialAccount.objects.filter(provider="gitlab")
            .filter(Q(extra_data__username=gitlab_username) | Q(uid=gitlab_username))
            .first()
        )
        if account is None:
            raise CommandError(
                f"No GitLab social account with username or uid "
                f"{gitlab_username!r} found."
            )

        previous_user = account.user
        if previous_user == local_user:
            self.stdout.write(
                f"GitLab account {gitlab_username!r} is already linked to "
                f"{local_username!r}; nothing to do."
            )
            return

        account.user = local_user
        account.save()
        self.stdout.write(
            self.style.SUCCESS(
                f"Linked GitLab account {gitlab_username!r} "
                f"(uid {account.uid}) to {local_username!r} "
                f"(previously owned by {previous_user.username!r})."
            )
        )

        if delete_orphan:
            self._delete_orphan(previous_user)

    def _delete_orphan(self, orphan):
        if Person.objects.filter(user=orphan).exists():
            self._warn_referenced(orphan, "Person.user")
            return
        if ParticipantSubmission.objects.filter(linked_user=orphan).exists():
            self._warn_referenced(orphan, "ParticipantSubmission.linked_user")
            return
        orphan.delete()
        self.stdout.write(f"Deleted orphaned user {orphan.username!r}.")

    def _warn_referenced(self, orphan, reference):
        self.stdout.write(
            self.style.WARNING(
                f"Keeping user {orphan.username!r}: still referenced by {reference}."
            )
        )
