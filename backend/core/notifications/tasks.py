from celery import shared_task
from django.conf import settings
from django.core.mail import EmailMessage
from django.db.models import F
from django.utils import timezone

from core.models import Notification


@shared_task(bind=True, ignore_result=True, max_retries=3)
def send_notification(self, notification_id):
    try:
        Notification.objects.get(pk=notification_id)
    except Notification.DoesNotExist:
        raise self.retry(countdown=10, max_retries=6) from None

    # Atomic claim: only a task that flips a non-terminal row to "retrying"
    # proceeds, so concurrent deliveries and re-enqueues cannot double-send.
    # "sent" rows are never claimed again.
    claimed = Notification.objects.filter(
        pk=notification_id,
        status__in=("pending", "retrying", "failed"),
    ).update(status="retrying")
    if not claimed:
        return

    notification = Notification.objects.get(pk=notification_id)
    if not notification.recipient:
        Notification.objects.filter(pk=notification_id).update(status="skipped")
        return

    try:
        EmailMessage(
            subject=notification.subject,
            body=notification.body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[notification.recipient],
        ).send(using="default")
    except Exception as exc:
        terminal = self.request.retries >= self.max_retries
        Notification.objects.filter(pk=notification_id).update(
            attempts=F("attempts") + 1,
            last_error=str(exc)[:2000],
            **({"status": "failed"} if terminal else {}),
        )
        if terminal:
            raise
        raise self.retry(
            exc=exc, countdown=min(60 * 2**self.request.retries, 900)
        ) from exc

    Notification.objects.filter(pk=notification_id).update(
        status="sent",
        attempts=F("attempts") + 1,
        sent_at=timezone.now(),
        last_error="",
    )
