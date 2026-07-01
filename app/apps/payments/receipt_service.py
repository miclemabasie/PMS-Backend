# apps/payments/receipt_service.py

import logging
from typing import Dict, Any, Optional
from django.utils import timezone
from django.core.exceptions import PermissionDenied
from apps.payments.models import Payment, Receipt
from apps.payments.utils.receipts import generate_receipt_number
from apps.payments.repositories import ReceiptRepository
from apps.reports.models import TemplateConfig
from apps.payments.tasks import send_receipt_email

logger = logging.getLogger(__name__)


class ReceiptService:
    """Service for generating and retrieving receipt data – all business logic here."""

    # Custom exceptions (can be caught by the view)
    class PaymentNotFound(Exception):
        pass

    class PermissionDenied(Exception):
        pass

    def __init__(self):
        self.receipt_repo = ReceiptRepository()

    def get_receipt_for_user(self, payment_id: str, user) -> Dict[str, Any]:
        """
        High-level method: fetch receipt data for a user.
        Handles permission checks, retrieval, and on-demand generation.
        Returns receipt data dict, or raises exceptions.
        """
        # 1. Get payment with permission check
        payment = self._get_payment_with_permission(payment_id, user)

        # 2. Try to get existing receipt data
        data = self.get_receipt_data(payment_id)

        if data is None:
            # 3. Generate receipt on-demand
            receipt = self.create_receipt(payment)
            data = receipt.data
            # 4. Trigger email asynchronously
            send_receipt_email.delay(str(payment.id))

        return data

    def _get_payment_with_permission(self, payment_id: str, user) -> Payment:
        """
        Fetch payment and check if the user has permission to view it.
        Raises PaymentNotFound or PermissionDenied.
        """
        try:
            payment = Payment.objects.select_related(
                "agreement__unit__property",
                "agreement__tenant",
            ).get(id=payment_id)
        except Payment.DoesNotExist:
            raise self.PaymentNotFound("Payment not found.")

        # Permission check
        agreement = payment.agreement

        if user.is_superuser:
            return payment

        if hasattr(user, "tenant_profile") and agreement.tenant == user.tenant_profile:
            return payment

        if hasattr(user, "owner_profile"):
            if agreement.unit.property.owners.filter(pkid=user.owner_profile.pkid).exists():
                return payment

        if hasattr(user, "manager_profile"):
            if agreement.unit.property.managers.filter(pkid=user.manager_profile.pkid).exists():
                return payment

        raise self.PermissionDenied("User does not have permission to view this receipt.")

    def generate_receipt_data(self, payment: Payment) -> Dict[str, Any]:
        """Build complete receipt data snapshot."""
        agreement = payment.agreement
        unit = agreement.unit
        property_obj = unit.property
        tenant = agreement.tenant
        owner = property_obj.get_payout_owner()  # primary owner

        template_config = TemplateConfig.objects.filter(
            landlord=owner,
            template_type="receipt",
            is_default=True,
        ).first()

        return {
            "receipt_number": generate_receipt_number(),
            "payment": {
                "id": str(payment.id),
                "amount": float(payment.amount),
                "payment_date": payment.payment_date.isoformat(),
                "payment_method": payment.get_payment_method_display(),
                "status": payment.status,
                "transaction_id": payment.transaction_id,
                "months_covered": float(payment.months_covered) if payment.months_covered else None,
                "period_start": payment.period_start.isoformat() if payment.period_start else None,
                "period_end": payment.period_end.isoformat() if payment.period_end else None,
                "fee_breakdown": payment.fee_breakdown,
                "net_landlord_amount": float(payment.net_landlord_amount) if payment.net_landlord_amount else None,
            },
            "agreement": {
                "id": str(agreement.id),
                "start_date": agreement.start_date.isoformat(),
                "payment_plan": agreement.payment_plan.name,
                "is_active": agreement.is_active,
            },
            "tenant": {
                "name": tenant.user.get_full_name(),
                "email": tenant.user.email,
                "phone": str(tenant.user.profile.phone_number) if hasattr(tenant.user, "profile") else None,
                "id_number": tenant.id_number,
            },
            "property": {
                "id": str(property_obj.id),
                "name": property_obj.name,
                "address": f"{property_obj.address_line1}, {property_obj.city}, {property_obj.country.name}",
                "phone": str(owner.mobile_money_number) if owner and owner.mobile_money_number else "",
            },
            "unit": {
                "id": str(unit.id),
                "number": unit.unit_number,
                "type": unit.unit_type,
            },
            "landlord": {
                "name": owner.user.get_full_name() if owner else "",
                "email": owner.user.email if owner else "",
                "phone": str(owner.mobile_money_number) if owner and owner.mobile_money_number else "",
            },
            "template": {
                "logo_url": template_config.logo.url if template_config and template_config.logo else None,
                "primary_color": template_config.primary_color if template_config else "#1E3A8A",
                "secondary_color": template_config.secondary_color if template_config else "#F59E0B",
                "agency_name": template_config.agency_name if template_config else (owner.user.get_full_name() if owner else "Blizton"),
                "agency_address": template_config.agency_address if template_config else "",
                "agency_phone": template_config.agency_phone if template_config else (str(owner.mobile_money_number) if owner and owner.mobile_money_number else ""),
                "agency_email": template_config.agency_email if template_config else (owner.user.email if owner else ""),
                "footer_text": template_config.footer_text if template_config else "",
                "show_property_name": template_config.show_property_name if template_config else True,
            },
        }

    def create_receipt(self, payment: Payment) -> Receipt:
        """
        Generate receipt data and persist it.
        Returns the Receipt object. Does NOT send email.
        """
        data = self.generate_receipt_data(payment)
        receipt_number = data["receipt_number"]

        existing = self.receipt_repo.get_by_payment(str(payment.id))
        if existing:
            receipt = self.receipt_repo.update_receipt(
                existing,
                receipt_number=receipt_number,
                data=data,
                status="generated",
                generated_at=timezone.now(),
            )
        else:
            receipt = self.receipt_repo.create_receipt(payment, data, receipt_number)

        logger.info(f"Receipt {receipt.receipt_number} created for payment {payment.id}")
        return receipt

    def get_receipt_data(self, payment_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve receipt data for a payment, or None if not generated."""
        receipt = self.receipt_repo.get_by_payment(payment_id)
        if receipt:
            return receipt.data
        return None