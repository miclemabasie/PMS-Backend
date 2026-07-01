from abc import ABC, abstractmethod
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings

class BaseNotificationService(ABC):
    @abstractmethod
    def send(self, recipient, subject, template_name, context, **kwargs):
        pass

class EmailService(BaseNotificationService):
    def send(self, recipient, subject, template_name, context, from_email=None, **kwargs):
        html_body = render_to_string(template_name, context)
        # Try to load plain text version if exists
        try:
            plain_body = render_to_string(template_name.replace('.html', '.txt'), context)
        except:
            plain_body = html_body  # fallback
        send_mail(
            subject=subject,
            message=plain_body,
            from_email=from_email or settings.DEFAULT_FROM_EMAIL,
            recipient_list=[recipient],
            html_message=html_body,
            fail_silently=False,
        )

class SmsService(BaseNotificationService):
    def send(self, recipient, subject, template_name, context, **kwargs):
        # Stub – implement later
        pass

class WhatsAppService(BaseNotificationService):
    def send(self, recipient, subject, template_name, context, **kwargs):
        # Stub – implement later
        pass

class NotificationDispatcher:
    _services = {
        "email": EmailService,
        "sms": SmsService,
        "whatsapp": WhatsAppService,
    }

    def send(self, channel, recipient, subject, template_name, context, **kwargs):
        service_class = self._services.get(channel)
        if not service_class:
            raise ValueError(f"Unsupported channel: {channel}")
        service = service_class()
        service.send(recipient, subject, template_name, context, **kwargs)