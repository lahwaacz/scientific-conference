from django.conf import settings
from django.core.mail import send_mail
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver

from .models import ParticipantSubmission


@receiver(pre_save, sender=ParticipantSubmission)
def store_old_status(sender, instance, **kwargs):
    if not instance.pk:
        instance._old_status = None
        return

    try:
        old_instance = ParticipantSubmission.objects.get(pk=instance.pk)
        instance._old_status = old_instance.status
    except ParticipantSubmission.DoesNotExist:
        instance._old_status = None


@receiver(post_save, sender=ParticipantSubmission)
def send_submission_published_email(sender, instance, created, **kwargs):
    old_status = getattr(instance, "_old_status", None)

    if instance.status == "approved" and old_status != "approved" and instance.email:
        send_mail(
            subject="Your submission has been published",
            message=(
                f"Hello {instance.name},\n\n"
                f'Your submission "{instance.abstract_title or "Untitled submission"}" '
                f"has been published successfully.\n\n"
                f"Thank you for your participation."
            ),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[instance.email],
            fail_silently=False,
        )
