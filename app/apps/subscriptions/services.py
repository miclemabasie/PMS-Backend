# apps/subscriptions/services.py

from typing import Any, Optional
from apps.properties.models import Owner
from apps.subscriptions.models import SubscriptionPlan, SubscriptionInvoice
from django.db import models
from .repositories import SubscriptionInvoiceRepository
from datetime import timedelta

from apps.core.base_service import BaseService
from django.utils import timezone


class SubscriptionService:
    """
    Service for checking subscription features and quotas.
    """

    @staticmethod
    def get_current_plan(owner: Owner) -> Optional[SubscriptionPlan]:
        """Get the owner's current subscription plan (or None)."""
        return owner.subscription_plan

    @staticmethod
    def has_feature(owner: Owner, feature_key: str) -> bool:
        """Check if the owner's current plan includes a feature."""
        plan = SubscriptionService.get_current_plan(owner)
        if not plan:
            return False
        return plan.has_feature(feature_key)

    @staticmethod
    def get_quota(owner: Owner, quota_key: str, default=None) -> Any:
        """Get a numeric quota from the plan (e.g., max_properties)."""
        plan = SubscriptionService.get_current_plan(owner)
        if not plan:
            return default
        return plan.get_quota(quota_key, default)

    @staticmethod
    def can_create_property(owner: Owner) -> tuple[bool, str]:
        """Check if owner can add a new property; returns (allowed, reason)."""
        if not SubscriptionService.has_feature(owner, "can_create_properties"):
            return False, "Your plan does not allow creating properties."
        max_props = SubscriptionService.get_quota(owner, "max_properties")
        if max_props is not None:
            current_count = owner.properties.count()
            if current_count >= max_props:
                return False, f"Your plan allows a maximum of {max_props} properties."
        return True, ""

    @staticmethod
    def can_create_unit(owner: Owner, property_obj) -> tuple[bool, str]:
        """Check if owner can add a new unit to a given property."""
        if not SubscriptionService.has_feature(owner, "can_create_units"):
            return False, "Your plan does not allow creating units."
        max_total = SubscriptionService.get_quota(owner, "max_units_total")
        if max_total is not None:
            total_units = (
                owner.properties.aggregate(total=models.Sum("units__id"))["total"] or 0
            )
            if total_units >= max_total:
                return False, f"Your plan allows a maximum of {max_total} units total."
        max_per_property = SubscriptionService.get_quota(
            owner, "max_units_per_property"
        )
        if max_per_property is not None:
            units_in_property = property_obj.units.count()
            if units_in_property >= max_per_property:
                return (
                    False,
                    f"Your plan allows a maximum of {max_per_property} units per property.",
                )
        return True, ""

    # Additional checks for manual payments, advanced reports, etc.
    @staticmethod
    def can_use_manual_payments(owner: Owner) -> bool:
        return SubscriptionService.has_feature(owner, "can_use_manual_payments")


class SubscriptionInvoiceService(BaseService[SubscriptionInvoice]):
    def __init__(self):
        super().__init__(SubscriptionInvoiceRepository())

    def generate_invoices_for_month(self):
        owners = Owner.objects.filter(
            subscription_status__in=["active", "trial"],
            subscription_plan__isnull=False,
            subscription_end_date__gte=timezone.now().date(),
        )
        created = []
        for owner in owners:
            # avoid duplicates for this month
            start_of_month = timezone.now().replace(
                day=1, hour=0, minute=0, second=0, microsecond=0
            )
            if self.repository.exists_for_owner_in_period(
                owner, start_of_month, start_of_month + timedelta(days=32)
            ):
                continue
            invoice = self.repository.create(
                owner=owner,
                plan=owner.subscription_plan,
                amount=owner.subscription_plan.monthly_price,
                due_date=timezone.now().date() + timedelta(days=7),
                status="pending",
            )
            created.append(invoice)
        return created

    def charge_invoice(self, invoice_id):
        invoice = self.get_by_id(invoice_id)
        if not invoice or invoice.status != "pending":
            return
        # Use a dedicated PaymentService for subscription payments
        from apps.payments.services import PaymentService

        payment_service = PaymentService()
        try:
            payment = payment_service.create_subscription_payment(invoice)
            # Mark invoice paid if payment completed immediately
            if payment.status == "completed":
                self._finalize_invoice(invoice, payment)
        except Exception as e:
            invoice.retry_count += 1
            invoice.error_message = str(e)
            if invoice.retry_count >= 3:
                invoice.status = "failed"
            invoice.save()
            raise
