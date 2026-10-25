from datetime import timedelta

from django.core.management.base import BaseCommand, CommandError
from django.db.models import Q
from django.utils import timezone

from core.models import Notification
from core.notifications import enqueue_notification

ALLOWED_STATUSES = ("pending", "failed", "retrying")


class Command(BaseCommand):
    help = "Re-enqueue stored notifications that have not been sent."

    def add_arguments(self, parser):
        parser.add_argument("--limit", type=int, default=500)
        parser.add_argument("--status", default="pending,failed")
        parser.add_argument("--stuck-retrying-minutes", type=int, default=None)
        parser.add_argument("--dry-run", action="store_true")

    def handle(self, *args, **options):
        statuses = [s.strip() for s in options["status"].split(",") if s.strip()]
        if not statuses:
            raise CommandError("--status must name at least one status")
        invalid = sorted(set(statuses) - set(ALLOWED_STATUSES))
        if invalid:
            raise CommandError(
                f"--status accepts only {ALLOWED_STATUSES}; got {invalid}"
            )
        limit = options["limit"]
        if limit < 1:
            raise CommandError("--limit must be a positive integer")

        condition = Q()
        direct = [status for status in statuses if status != "retrying"]
        if direct:
            condition |= Q(status__in=direct)
        if "retrying" in statuses:
            minutes = options["stuck_retrying_minutes"]
            if minutes is None:
                raise CommandError(
                    "--status retrying requires --stuck-retrying-minutes: a healthy "
                    "retry finishes within minutes, so only explicitly old rows may "
                    "be swept"
                )
            if minutes < 1:
                raise CommandError(
                    "--stuck-retrying-minutes must be a positive integer"
                )
            cutoff = timezone.now() - timedelta(minutes=minutes)
            condition |= Q(status="retrying", created_at__lt=cutoff)

        notification_ids = list(
            Notification.objects.filter(condition)
            .order_by("created_at")
            .values_list("pk", flat=True)[:limit]
        )
        if options["dry_run"]:
            self.stdout.write(f"Would enqueue {len(notification_ids)} notification(s).")
            return
        enqueued = sum(1 for nid in notification_ids if enqueue_notification(nid))
        self.stdout.write(
            f"Enqueued {enqueued} of {len(notification_ids)} notification(s)."
        )
