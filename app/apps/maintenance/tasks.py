from celery import shared_task
import logging

from apps.notifications.tasks import send_notification

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def send_maintenance_notification(self, recipient: str, context: dict, template_name: str):
    """
    Send maintenance notification email.
    
    Args:
        recipient: Email address of the recipient
        context: Template context
        template_name: Path to the email template
    """
    try:
        send_notification.delay(
            channel='email',
            recipient=recipient,
            subject=context.get('subject', 'Maintenance Request Update'),
            template_name=template_name,
            context=context
        )
        logger.info(f"Maintenance notification sent to {recipient}")
    except Exception as e:
        logger.error(f"Failed to send maintenance notification to {recipient}: {str(e)}")
        if self.request.retries < self.max_retries:
            raise self.retry(exc=e, countdown=60 * (2 ** self.request.retries))


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def send_maintenance_status_update(
    self, 
    recipient: str, 
    context: dict, 
    status: str,
    is_tenant: bool = False
):
    """
    Send maintenance status update notification.
    
    Args:
        recipient: Email address
        context: Template context
        status: New status (in_progress, completed, cancelled)
        is_tenant: Whether recipient is the tenant
    """
    template_map = {
        'in_progress': 'emails/maintenance/status_in_progress.html',
        'completed': 'emails/maintenance/status_completed.html',
        'cancelled': 'emails/maintenance/status_cancelled.html',
    }
    
    template_name = template_map.get(status)
    if not template_name:
        logger.warning(f"No template found for status: {status}")
        return
    
    subject_map = {
        'in_progress': 'Maintenance Update: Work In Progress',
        'completed': 'Maintenance Complete ✅',
        'cancelled': 'Maintenance Cancelled ❌',
    }
    
    context['subject'] = subject_map.get(status, 'Maintenance Status Update')
    context['is_tenant'] = is_tenant
    
    try:
        send_notification.delay(
            channel='email',
            recipient=recipient,
            subject=context['subject'],
            template_name=template_name,
            context=context
        )
        logger.info(f"Status update notification sent to {recipient} for status: {status}")
    except Exception as e:
        logger.error(f"Failed to send status update to {recipient}: {str(e)}")
        if self.request.retries < self.max_retries:
            raise self.retry(exc=e, countdown=60 * (2 ** self.request.retries))