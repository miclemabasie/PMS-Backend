"""
Unified Payment Manager for Rental Agreements
Orchestrates fee calculation, gateway calls, payment recording, and status verification.
"""

import logging
import hashlib
from decimal import Decimal
from typing import Dict, Any, Optional, Tuple
from django.db import transaction
from django.utils import timezone
from django.conf import settings

from apps.payments.gateway_SDKs.gateway_factory import gateway_factory
from apps.payments.rent_calculator import RentCalculator
from apps.payments.models import Payment, PaymentPlan, RentalAgreement
from apps.properties.models import PaymentConfiguration

logger = logging.getLogger(__name__)


class PaymentManager:
    """
    Orchestrates all payment operations for rental agreements.
    Services should use this class instead of directly calling gateways or calculators.
    """

    def __init__(self, gateway_code: str = None):
        self.gateway_code = gateway_code or self._get_default_gateway_code()
        self.gateway = None
        self._initialize_gateway()
        self.is_staging = self._check_if_staging()

    # ------------------------------------------------------------------
    # Public API – to be used by services
    # ------------------------------------------------------------------

    def process_rent_payment(
        self,
        agreement: RentalAgreement,
        amount: Decimal,
        payment_method: str,
        phone_number: str = None,
        provider: str = None,
        execute_immediately: bool = True,
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Process a rent payment for a rental agreement.
        Handles fee calculation, gateway interaction, and payment recording.

        Returns:
            (success, result_dict)
        """
        with transaction.atomic():
            try:
                # 1. Validate agreement is active
                if not agreement.is_active:
                    return False, {"error": "Agreement is not active"}

                # 2. Get payment configuration for the property
                config = self._get_payment_config(agreement)
                if not config:
                    return False, {
                        "error": "No payment configuration found for this property"
                    }

                # 3. Determine net rent (what landlord expects)
                net_rent = self._get_net_rent_for_payment(agreement, amount)
                if net_rent is None:
                    return False, {
                        "error": "Could not determine net rent for this payment"
                    }

                # 4. Get landlord's preferred payout method
                payout_method = self._get_landlord_payout_method(agreement)

                # 5. Calculate fees and totals
                calculator = RentCalculator(net_rent, config, payout_method)
                breakdown = calculator.get_breakdown()
                expected_total = breakdown["tenant_total"]
                landlord_net = breakdown["landlord_net"]

                # 6. Validate amount against expected total (with custom amount flexibility)
                plan = agreement.payment_plan
                if not plan.allow_custom_amount and amount != expected_total:
                    return False, {
                        "error": f"Payment amount must be exactly {expected_total} XAF (includes fees). "
                        f"You entered {amount} XAF."
                    }
                if plan.allow_custom_amount and amount < net_rent:
                    return False, {
                        "error": f"Payment amount cannot be less than net rent {net_rent} XAF."
                    }

                # If custom amount is allowed but amount differs from expected_total,
                # we need to adjust landlord_net proportionally.
                if plan.allow_custom_amount and amount != expected_total:
                    # Recalculate landlord_net based on actual amount, preserving fee ratios
                    landlord_net = self._recalculate_landlord_net(
                        amount, breakdown, net_rent
                    )

                # 7. Execute payment via gateway (or dummy in staging)
                gateway_result = self._execute_gateway_payment(
                    amount=amount,
                    payment_method=payment_method,
                    phone_number=phone_number,
                    provider=provider,
                    agreement=agreement,
                )
                if not gateway_result["success"]:
                    return False, {
                        "error": gateway_result.get("error", "Gateway payment failed")
                    }

                # 8. Create payment record
                payment = Payment.objects.create(
                    agreement=agreement,
                    amount=amount,
                    months_covered=self._calculate_months_covered(
                        agreement, amount, net_rent
                    ),
                    period_start=timezone.now().date(),
                    period_end=self._calculate_period_end(agreement, amount, net_rent),
                    payment_method=payment_method,
                    status="completed",  # or pending if async
                    transaction_id=gateway_result.get("transaction_id"),
                    mobile_phone=phone_number or "",
                    mobile_provider=provider or "",
                    gateway_response=gateway_result.get("raw_response", {}),
                    net_landlord_amount=landlord_net,
                    fee_breakdown=breakdown,
                    gateway_reference=gateway_result.get("gateway_reference"),
                    gateway_transaction_id=gateway_result.get("gateway_transaction_id"),
                    current_status="completed",
                )

                # 9. Update agreement coverage or installment status
                self._update_agreement_after_payment(
                    agreement, amount, net_rent, payment
                )

                return True, {
                    "payment_id": str(payment.id),
                    "amount": float(payment.amount),
                    "net_landlord_amount": float(landlord_net),
                    "fee_breakdown": breakdown,
                    "transaction_id": payment.transaction_id,
                    "status": payment.current_status,
                    "message": "Payment processed successfully",
                }

            except Exception as e:
                logger.exception(f"Payment processing failed: {e}")
                return False, {"error": str(e), "code": "payment_processing_failed"}

    def get_payment_status(self, payment_id: str) -> Dict[str, Any]:
        """Check payment status, optionally verifying with gateway."""
        try:
            payment = Payment.objects.get(id=payment_id)
            if payment.current_status == "completed":
                return self._build_status_response(payment)

            # If pending, verify with gateway
            if payment.current_status == "pending" and payment.gateway_transaction_id:
                gateway_status = self.gateway.verify_payment(
                    payment.gateway_transaction_id
                )
                if gateway_status.get("status") in ["success", "completed"]:
                    self._complete_payment(payment, gateway_status)
                elif gateway_status.get("status") in ["failed", "error"]:
                    self._fail_payment(payment, gateway_status)

            return self._build_status_response(payment)
        except Payment.DoesNotExist:
            return {"error": "Payment not found", "status": "not_found"}

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _get_default_gateway_code(self) -> str:
        try:
            from apps.payments.models import PaymentGateway

            default = PaymentGateway.objects.filter(
                is_default=True, is_active=True
            ).first()
            return default.code if default else "smobilpay_default"
        except:
            return "smobilpay_default"

    def _initialize_gateway(self):
        try:
            gateway_config = self._get_gateway_config()
            self.gateway = gateway_factory.create_gateway(
                gateway_type=gateway_config["gateway_type"], config=gateway_config
            )
            logger.info(f"Payment gateway initialized: {self.gateway_code}")
        except Exception as e:
            logger.error(f"Failed to initialize gateway: {e}")
            raise

    def _get_gateway_config(self) -> Dict[str, Any]:
        # Try to get from database, fallback to settings
        try:
            from apps.payments.models import PaymentGateway

            gateway = PaymentGateway.objects.get(code=self.gateway_code, is_active=True)
            return {
                "gateway_type": gateway.gateway_type,
                "name": gateway.name,
                "config": gateway.config,
                "supports_cashin": gateway.supports_cashin,
                "supports_cashout": gateway.supports_cashout,
            }
        except:
            return settings.PAYMENT_GATEWAYS.get(self.gateway_code, {})

    def _check_if_staging(self) -> bool:
        return getattr(settings, "STAGING_MODE", False) or getattr(
            settings, "DEBUG", False
        )

    def _get_payment_config(
        self, agreement: RentalAgreement
    ) -> Optional[PaymentConfiguration]:
        """Retrieve or create default config for the property."""
        config = agreement.unit.property.payment_config
        if not config and self.is_staging:
            # Auto-create default config for staging (in prod, should be created via signal)
            config = PaymentConfiguration.objects.create(
                property=agreement.unit.property
            )
        return config

    def _get_net_rent_for_payment(
        self, agreement: RentalAgreement, amount: Decimal
    ) -> Optional[Decimal]:
        """Determine the net rent amount that landlord expects for this payment."""
        plan = agreement.payment_plan
        if plan.mode == "monthly":
            return agreement.unit.monthly_rent
        else:
            # Yearly mode: get current installment due amount
            status = agreement.installment_status
            next_idx = status.get("next_installment_index")
            if next_idx is not None:
                return Decimal(status["installments"][next_idx]["remaining"])
            return None

    def _get_landlord_payout_method(self, agreement: RentalAgreement) -> str:
        """Get landlord's preferred payout method from the primary owner."""
        owner = agreement.unit.property.get_payout_owner()
        if owner and owner.preferred_payout_method:
            return owner.preferred_payout_method
        return "bank_transfer"  # default

    def _recalculate_landlord_net(
        self, amount: Decimal, breakdown: Dict, net_rent: Decimal
    ) -> Decimal:
        """If custom amount used, recalculate landlord net proportionally."""
        # Simple proportional: landlord_net = amount * (original_landlord_net / original_total)
        original_total = breakdown["tenant_total"]
        original_landlord_net = breakdown["landlord_net"]
        if original_total == 0:
            return amount
        return (amount * original_landlord_net / original_total).quantize(Decimal("1."))

    def _execute_gateway_payment(
        self,
        amount: Decimal,
        payment_method: str,
        phone_number: str,
        provider: str,
        agreement: RentalAgreement,
    ) -> Dict[str, Any]:
        """Execute payment via gateway or dummy processor."""
        if self.is_staging:
            # Use dummy processor
            from apps.payments.dummy_payment_processor import DummyPaymentProcessor

            result = DummyPaymentProcessor.initiate_payment(
                amount, phone_number or "", provider or ""
            )
            return {
                "success": result["success"],
                "transaction_id": result.get("transaction_id"),
                "gateway_reference": result.get("reference"),
                "gateway_transaction_id": result.get("transaction_id"),
                "raw_response": result,
            }
        else:
            # Real gateway
            # First create payment intent
            intent = self.gateway.create_payment_intent(
                amount=amount,
                currency="XAF",
                payment_method=payment_method,
                customer_data={
                    "phone_number": phone_number,
                    "email": agreement.tenant.user.email,
                },
                metadata={"agreement_id": str(agreement.id)},
            )
            if intent.get("status") == "failed":
                return {"success": False, "error": intent.get("error")}

            # Then execute
            execution = self.gateway.execute_payment(
                gateway_reference=intent["gateway_reference"],
                customer_authorization={"phone_number": phone_number},
            )
            if execution.get("status") in ["completed", "success", "pending"]:
                return {
                    "success": True,
                    "transaction_id": execution.get("gateway_transaction_id"),
                    "gateway_reference": intent["gateway_reference"],
                    "gateway_transaction_id": execution.get("gateway_transaction_id"),
                    "raw_response": execution,
                }
            else:
                return {"success": False, "error": execution.get("error")}

    def _calculate_months_covered(
        self, agreement: RentalAgreement, amount: Decimal, net_rent: Decimal
    ) -> Optional[Decimal]:
        """For monthly mode, calculate how many months are covered."""
        plan = agreement.payment_plan
        if plan.mode == "monthly":
            if net_rent == 0:
                return Decimal(0)
            return (amount / net_rent).quantize(Decimal("0.01"))
        return None

    def _calculate_period_end(
        self, agreement: RentalAgreement, amount: Decimal, net_rent: Decimal
    ) -> Optional[Decimal]:
        """Calculate coverage end date based on payment."""
        # This is simplified; you can implement full logic as in your original service
        if agreement.payment_plan.mode == "monthly":
            months = self._calculate_months_covered(agreement, amount, net_rent)
            if months:
                return timezone.now().date() + timezone.timedelta(days=int(months * 30))
        return None

    def _update_agreement_after_payment(
        self,
        agreement: RentalAgreement,
        amount: Decimal,
        net_rent: Decimal,
        payment: Payment,
    ):
        """Delegate to existing service logic or implement directly."""
        # You can call the existing service method or replicate logic here.
        # To avoid duplication, you might inject the service or call it.
        # For simplicity, we'll assume the service will update agreement after payment.
        # But the service could call PaymentManager and then update agreement.
        # I'll leave this as a placeholder – you can move the update logic from RentalAgreementService here.
        pass

    def _complete_payment(self, payment: Payment, gateway_response: Dict):
        payment.current_status = "completed"
        payment.status = "completed"
        payment.processed_at = timezone.now()
        payment.save()
        # Optionally update agreement etc.

    def _fail_payment(self, payment: Payment, gateway_response: Dict):
        payment.current_status = "failed"
        payment.status = "failed"
        payment.save()

    def _build_status_response(self, payment: Payment) -> Dict[str, Any]:
        return {
            "payment_id": str(payment.id),
            "status": payment.current_status,
            "amount": float(payment.amount),
            "net_landlord_amount": (
                float(payment.net_landlord_amount)
                if payment.net_landlord_amount
                else None
            ),
            "transaction_id": payment.transaction_id,
            "created_at": payment.created_at.isoformat(),
            "processed_at": (
                payment.processed_at.isoformat() if payment.processed_at else None
            ),
        }
