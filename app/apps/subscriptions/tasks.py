from celery import shared_task
from django.utils import timezone
from datetime import timedelta
from apps.subscriptions.services import SubscriptionInvoiceService
from apps.properties.models import Owner
import logging

logger = logging.getLogger(__name__)


@shared_task
def generate_subscription_invoices():
    service = SubscriptionInvoiceService()
    invoices = service.generate_invoices_for_month()
    logger.info(f"Generated {len(invoices)} subscription invoices")


@shared_task(bind=True, max_retries=3)
def charge_subscription_invoice(self, invoice_id):
    service = SubscriptionInvoiceService()
    try:
        service.charge_invoice(invoice_id)
    except Exception as e:
        self.retry(exc=e, countdown=60 * (2**self.request.retries))


@shared_task
def expire_subscriptions():
    """Set expired subscriptions to 'expired' and downgrade if past_due > 15 days."""
    from apps.subscriptions.models import SubscriptionPlan

    # 1. Expire active subscriptions whose end_date has passed
    expired_owners = Owner.objects.filter(
        subscription_status__in=["active", "trial"],
        subscription_end_date__lt=timezone.now().date(),
    )
    for owner in expired_owners:
        owner.subscription_status = "expired"
        owner.save(update_fields=["subscription_status"])

    # 2. Downgrade past_due > 15 days to Free plan
    free_plan = SubscriptionPlan.objects.filter(
        name="Free Plan", is_active=True
    ).first()
    if free_plan:
        downgrade_owners = Owner.objects.filter(
            subscription_status="past_due",
            subscription_end_date__lt=timezone.now().date() - timedelta(days=15),
        )
        for owner in downgrade_owners:
            owner.subscription_plan = free_plan
            owner.subscription_status = "active"
            owner.subscription_end_date = None
            owner.save(
                update_fields=[
                    "subscription_plan",
                    "subscription_status",
                    "subscription_end_date",
                ]
            )
            logger.info(f"Downgraded owner {owner.id} to Free Plan")
