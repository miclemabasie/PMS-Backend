from celery import shared_task
from .services import NotificationDispatcher

@shared_task
def send_notification(channel, recipient, subject, template_name, context, **kwargs):
    dispatcher = NotificationDispatcher()
    dispatcher.send(channel, recipient, subject, template_name, context, **kwargs)