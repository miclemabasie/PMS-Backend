from celery import shared_task
from apps.payments.services import DisbursementService
from apps.payments.models import Payment
from apps.payments.services.receipt_service import ReceiptService
from apps.payments.models import Receipt
import logging

logger = logging.getLogger(__name__)


@shared_task
def process_disbursements():
    service = DisbursementService()
    service.process_pending_disbursements()
    logger.info("Disbursements processed")


# apps/payments/tasks.py



@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def generate_receipt_task(self, payment_id: str):
    """Generate receipt data for a payment and store it."""
    try:
        payment = Payment.objects.get(id=payment_id)
    except Payment.DoesNotExist:
        logger.error(f"Payment {payment_id} not found for receipt generation.")
        return

    service = ReceiptService()
    try:
        service.create_receipt(payment)
        logger.info(f"Receipt generated for payment {payment_id}")
    except Exception as e:
        logger.exception(f"Failed to generate receipt for payment {payment_id}")
        # Update receipt status to failed if it exists
        try:
            receipt = Receipt.objects.get(payment=payment)
            receipt.status = "failed"
            receipt.error_message = str(e)[:255]
            receipt.save(update_fields=["status", "error_message"])
        except Receipt.DoesNotExist:
            # Create a failed record
            Receipt.objects.create(
                payment=payment,
                receipt_number="",  # will be generated on retry? but we can skip
                status="failed",
                error_message=str(e)[:255],
            )
        # Retry
        if self.request.retries < self.max_retries:
            raise self.retry(exc=e, countdown=60 * (2 ** self.request.retries))