import logging
from celery import shared_task
from django.utils import timezone

from .models import Notification, Broadcast, BroadcastStatus, NotificationStatus
from .utils import (
    get_email_backend,
    get_sms_backend,
    render_template,
    send_notification,
)
from .choices import NotificationChannel
from django.contrib.auth import get_user_model

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def send_notification_task(self, notification_id):
    try:
        notification = Notification.objects.get(id=notification_id)
    except Notification.DoesNotExist:
        logger.error(f"Notification {notification_id} not found")
        return

    if notification.status != NotificationStatus.PENDING:
        logger.warning(f"Notification {notification_id} already {notification.status}")
        return

    try:
        if notification.channel == NotificationChannel.EMAIL:
            backend = get_email_backend()
            backend.send(
                recipient=notification.recipient,
                subject=notification.subject,
                body=notification.body,
                html_body=None,  # you could store HTML separately
            )
        elif notification.channel == NotificationChannel.SMS:
            backend = get_sms_backend()
            backend.send(
                phone_number=notification.phone_number,
                message=notification.body,
            )
        else:
            raise ValueError(f"Unsupported channel: {notification.channel}")

        notification.status = NotificationStatus.SENT
        notification.sent_at = timezone.now()
        notification.save()

        # Update broadcast counters if part of a broadcast
        if notification.broadcast:
            broadcast = notification.broadcast
            broadcast.sent_count += 1
            broadcast.save()

    except Exception as e:
        logger.exception(f"Failed to send notification {notification_id}")
        notification.status = NotificationStatus.FAILED
        notification.error_message = str(e)
        notification.save()

        if notification.broadcast:
            broadcast = notification.broadcast
            broadcast.failed_count += 1
            broadcast.save()

        # Retry with exponential backoff
        self.retry(exc=e, countdown=60 * (2**self.request.retries))


@shared_task
def process_broadcast(broadcast_id):
    try:
        broadcast = Broadcast.objects.get(id=broadcast_id)
    except Broadcast.DoesNotExist:
        logger.error(f"Broadcast {broadcast_id} not found")
        return

    if broadcast.status != BroadcastStatus.SCHEDULED:
        logger.warning(f"Broadcast {broadcast_id} not in SCHEDULED state")
        return

    broadcast.status = BroadcastStatus.SENDING
    broadcast.save()

    User = get_user_model()
    filters = broadcast.recipient_filter
    users = User.objects.filter(**filters)
    broadcast.total_recipients = users.count()
    broadcast.save()

    template = broadcast.template
    context = {}  # Add any broadcast-specific context here (primitive values only!)

    for user in users.iterator():
        try:
            if broadcast.channel == NotificationChannel.EMAIL:
                send_notification(
                    user=user,
                    channel=broadcast.channel,
                    template=template,
                    context=context,  # 🟢 Context will be enhanced inside send_notification
                    broadcast=broadcast,
                )
            elif broadcast.channel == NotificationChannel.SMS:
                send_notification(
                    user=user,
                    channel=broadcast.channel,
                    template=template,
                    context=context,
                    broadcast=broadcast,
                )
        except Exception as e:
            logger.exception(f"Failed to send notification to {user.email}: {e}")
            broadcast.failed_count += 1
            continue

    broadcast.status = BroadcastStatus.SENT
    broadcast.completed_at = timezone.now()
    broadcast.save()
