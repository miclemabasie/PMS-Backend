from celery import shared_task
from apps.payments.services import DisbursementService
import logging

logger = logging.getLogger(__name__)


@shared_task
def send_notification():
    pass