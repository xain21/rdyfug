# signals.py
import logging

from django.conf import settings
from django.core.mail import send_mail
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from .models import BodMeeting, ActionLog, UserViewPermission

logger = logging.getLogger(__name__)

@receiver(post_save, sender=BodMeeting)
def log_bod_meeting_save(sender, instance, created, **kwargs):
    action = 'create' if created else 'update'
    ActionLog.objects.create(
        user=instance.updated_by,
        action=action,
        instance_id=str(instance.id),
        model_name=sender.__name__,  # Corrected here
    )


@receiver(post_save, sender=BodMeeting)
def notify_committee_on_new_meeting(sender, instance, created, **kwargs):
    """
    Emails everyone with view access to this meeting's category when a new
    meeting/document is uploaded. Uses the existing UserViewPermission table
    ('list:<category-slug>') so no separate "who's on this committee" list
    needs to be maintained.

    Never raises - a misconfigured or unreachable mail server should never
    block saving a meeting. In dev, EMAIL_BACKEND defaults to printing to
    the console, so this is safe to leave on without any mail setup.
    """
    if not created or not instance.category_id:
        return

    recipients = list(
        UserViewPermission.objects.filter(
            view_name=f'list:{instance.category.slug}', can_view=True,
        ).exclude(user__email='').values_list('user__email', flat=True).distinct()
    )
    if not recipients:
        return

    try:
        send_mail(
            subject=f'[BOD Portal] New document in {instance.category.name}: {instance.title}',
            message=(
                f'A new meeting/document was added to {instance.category.name}.\n\n'
                f'Title: {instance.title}\n'
                f'Date: {instance.date or "Not set"}\n\n'
                f'Log in to the portal to view it.'
            ),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=recipients,
            fail_silently=True,
        )
    except Exception:
        logger.exception('Failed to send new-meeting notification email for meeting %s', instance.id)

@receiver(post_delete, sender=BodMeeting)
def log_bod_meeting_delete(sender, instance, **kwargs):
    ActionLog.objects.create(
        user=instance.updated_by,
        action='delete',
        instance_id=str(instance.id),
        model_name=sender.__name__,  # Corrected here
    )
