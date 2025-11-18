import re
import logging
from django.template import Template, Context
from django.utils import timezone

from .choices import NotificationChannel, NotificationStatus
from .models import Notification, UserNotificationSetting
from .backends import DjangoSMTPBackend, ConsoleSMSBackend, TwilioSMSBackend
from django.conf import settings


logger = logging.getLogger(__name__)


def get_email_backend():
    backend_class = getattr(settings, "EMAIL_BACKEND_CLASS", DjangoSMTPBackend)
    return backend_class()


def get_sms_backend():
    backend_name = getattr(settings, "SMS_BACKEND", "console")
    if backend_name == "twilio":
        return TwilioSMSBackend()
    return ConsoleSMSBackend()


def render_template(template_str, context):
    """Render a string template with Django template language."""
    t = Template(template_str)
    return t.render(Context(context))


def send_notification(
    *,
    user=None,
    recipient_email=None,
    phone_number=None,
    channel,
    subject="",
    body="",
    html_body=None,
    template=None,
    context=None,
    broadcast=None,
):
    """
    Core sending function.
    - Creates a Notification log record.
    - Checks user notification preferences.
    - Calls the appropriate backend asynchronously via Celery task.
    """
    try:
        # Determine recipient
        if user:
            if channel == NotificationChannel.EMAIL:
                recipient_email = user.email
            elif channel == NotificationChannel.SMS:
                phone_number = getattr(user, "phone_number", None) or getattr(
                    getattr(user, "profile", None), "phone_number", None
                )

        # Validate at least one contact method
        if channel == NotificationChannel.EMAIL and not recipient_email:
            raise ValueError("No email recipient provided")
        if channel == NotificationChannel.SMS and not phone_number:
            raise ValueError("No phone number provided")

        # Check user preferences (if user is known)
        if user:
            try:
                prefs = user.notification_settings
                if channel == NotificationChannel.EMAIL and not prefs.email_enabled:
                    logger.info(f"Email disabled for user {user.email}, skipping.")
                    return None
                if channel == NotificationChannel.SMS and not prefs.sms_enabled:
                    logger.info(f"SMS disabled for user {user}, skipping.")
                    return None
            except UserNotificationSetting.DoesNotExist:
                pass  # send anyway if no explicit opt-out

        # --- Template rendering with safe context ---
        if template:
            context = context or {}

            # Add common context variables (primitive values ONLY!)
            if "site_name" not in context:
                context["site_name"] = getattr(settings, "SITE_NAME", "Our Site")
            if "year" not in context:
                context["year"] = timezone.now().year

            # 🟢 SAFE: Convert User object to dictionary
            if user:
                context["user"] = {
                    "id": str(user.id),
                    "pkid": user.pkid,
                    "email": user.email,
                    "username": user.username,
                    "first_name": user.first_name,
                    "last_name": user.last_name,
                    "full_name": user.get_full_name(),
                    "is_active": user.is_active,
                    "role": user.role if hasattr(user, "role") else None,
                }

            if channel == NotificationChannel.EMAIL:
                subject = (
                    render_template(template.subject, context)
                    if template.subject
                    else ""
                )
                body = render_template(template.template, context)
                html_body = (
                    render_template(template.html_template, context)
                    if template.html_template
                    else None
                )
            else:  # SMS
                body = render_template(template.template, context)
                html_body = None
        else:
            # Use provided subject/body (no rendering)
            subject = subject or ""
            body = body or ""
            html_body = html_body

        # Create notification log (status = pending)
        notification = Notification.objects.create(
            user=user,  # 🟢 This is a FK, NOT stored in JSON – it's fine
            recipient=recipient_email,
            phone_number=phone_number,
            channel=channel,
            subject=subject,
            body=body,
            template=template,
            context=context or {},  # 🟢 Now contains ONLY JSON-serializable data
            broadcast=broadcast,
        )

        # Dispatch async task
        from .tasks import send_notification_task

        send_notification_task.delay(str(notification.id))

        return notification
    except Exception as e:
        logger.exception(f"Failed to send notification: {e}")
        raise e


def get_email_backend():
    backend_name = getattr(settings, "EMAIL_BACKEND", "database")
    if backend_name == "database":
        from .backends import DatabaseSMTPBackend

        return DatabaseSMTPBackend()
    elif backend_name == "smtp":
        from .backends import DjangoSMTPBackend

        return DjangoSMTPBackend()
    return DatabaseSMTPBackend()
