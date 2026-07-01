import logging
from decimal import Decimal
from typing import Dict, Any, Optional
from django.utils import timezone
from django.core.exceptions import ObjectDoesNotExist

from apps.payments.models import Payment, Receipt
from apps.payments.utils import generate_receipt_number
from apps.reports.models import TemplateConfig

logger = logging.getLogger(__name__)


class ReceiptService:
    """Service to generate and retrieve receipt data."""

    def generate_receipt_data(self, payment: Payment) -> Dict[str, Any]:
        """
        Build the complete receipt data snapshot.
        Includes payment, agreement, tenant, property, unit, fee breakdown,
        and the landlord's template configuration.
        """
        agreement = payment.agreement
        unit = agreement.unit
        property_obj = unit.property
        tenant = agreement.tenant
        owner = property_obj.get_payout_owner()  # primary owner

        # Get template config (fallback to defaults if none)
        template_config = TemplateConfig.objects.filter(
            landlord=owner,
            template_type="receipt",
            is_default=True,
        ).first()

        # Build receipt data
        data = {
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
                "fee_breakdown": payment.fee_breakdown,  # already JSON
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
        return data

    def create_receipt(self, payment: Payment) -> Receipt:
        """
        Generate receipt data, create Receipt record, and return it.
        May be called synchronously or asynchronously.
        """
        data = self.generate_receipt_data(payment)
        receipt_number = data["receipt_number"]

        receipt, created = Receipt.objects.get_or_create(
            payment=payment,
            defaults={
                "receipt_number": receipt_number,
                "data": data,
                "status": "generated",
                "generated_at": timezone.now(),
            }
        )
        if not created:
            # Update existing receipt (e.g., if regenerating)
            receipt.receipt_number = receipt_number
            receipt.data = data
            receipt.status = "generated"
            receipt.generated_at = timezone.now()
            receipt.save(update_fields=["receipt_number", "data", "status", "generated_at"])

        return receipt

    def get_receipt_data(self, payment_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve receipt data for a payment, if exists."""
        try:
            receipt = Receipt.objects.get(payment__id=payment_id)
            return receipt.data
        except Receipt.DoesNotExist:
            return None