import logging
import uuid
from decimal import Decimal
from datetime import timedelta
from typing import Dict, Any, Optional, Tuple
from django.db import transaction
from datetime import datetime
from django.utils import timezone
from django.conf import settings

from apps.payments.models import Payment, RentalAgreement
from apps.payments.dummy_payment_processor import DummyPaymentProcessor
from apps.payments.utils.rent_calculator import RentCalculator
from apps.properties.models import PaymentConfiguration

logger = logging.getLogger(__name__)


def make_json_serializable(obj: Any) -> Any:
    """
    Recursively convert Decimal to string (or float) and handle other non‑serializable types.
    """
    if isinstance(obj, Decimal):
        return str(obj)  # store as string to preserve precision
    elif isinstance(obj, dict):
        return {k: make_json_serializable(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [make_json_serializable(v) for v in obj]
    elif isinstance(obj, tuple):
        return tuple(make_json_serializable(v) for v in obj)
    elif isinstance(obj, (datetime, timezone.datetime)):
        return obj.isoformat()
    return obj


class PaymentManager:
    """
    Two-phase payment processor for mobile money:
    1. initiate_payment() – creates pending payment, calls gateway execute → returns ptn
    2. verify_payment() – polls gateway, if success updates agreement & payment
    """

    def __init__(self, agreement: RentalAgreement):
        self.agreement = agreement
        self.plan = agreement.payment_plan
        self.unit = agreement.unit
        self.config = self._get_payment_config()
        self.is_staging = getattr(settings, "STAGING_MODE", False) or getattr(
            settings, "DEBUG", False
        )

    # --------------------------------------------------
    # Phase 1: Initiate payment (no agreement changes)
    # --------------------------------------------------
    @transaction.atomic
    def initiate_payment(
        self,
        amount: Decimal,
        payment_method: str,
        phone_number: str = None,
        provider: str = None,
        months: int = None,  # for monthly
        installment_index: int = None,  # for yearly
    ) -> Payment:
        """
        Step 1: Create pending payment record and call gateway execute.
        Returns Payment object with status='pending'.
        """
        amount = Decimal(str(amount))

        if not self.agreement.is_active:
            raise ValueError("Agreement is not active.")

        if self.plan.mode == "monthly":
            # Validate monthly payment
            monthly_rent = self.unit.monthly_rent
            if not monthly_rent:
                raise ValueError("Monthly rent not set for this unit.")

            if months is None:
                single_month_total = self._get_tenant_total_for_net_rent(monthly_rent)
                months = round(amount / single_month_total)
                if months < 1 or months != amount / single_month_total:
                    raise ValueError(
                        "Unable to determine number of months from amount. Please provide 'months' field."
                    )

            allowed_terms = (
                self.plan.allowed_monthly_terms
                if self.plan.allowed_monthly_terms
                else list(range(1, self.plan.max_months + 1))
            )
            if months not in allowed_terms:
                raise ValueError(
                    f"Payment for {months} month(s) not allowed. Allowed terms: {allowed_terms}"
                )

            net_rent = monthly_rent * months
            expected_total = self._get_tenant_total_for_net_rent(net_rent)
            if amount != expected_total:
                raise ValueError(
                    f"Amount must be exactly {expected_total} XAF for {months} month(s). You entered {amount} XAF."
                )
            self._pending_months = months

        else:  # yearly mode
            status = self.agreement.installment_status
            installments = status.get("installments", [])
            if installment_index is None:
                installment_index = status.get("next_installment_index")
            if installment_index is None or installment_index >= len(installments):
                raise ValueError("No pending installment found or invalid index.")

            inst = installments[installment_index]
            if inst["status"] != "pending":
                raise ValueError(f"Installment {installment_index} is already paid.")

            due_amount = Decimal(inst["remaining"])
            if not self.plan.allow_custom_amount and amount != due_amount:
                raise ValueError(
                    f"Must pay exactly {due_amount} XAF for this installment."
                )
            if amount > due_amount and not self.plan.allow_custom_amount:
                raise ValueError(f"Amount exceeds installment due ({due_amount} XAF).")

            net_rent = due_amount
            self._pending_installment_index = installment_index

        # Get config and calculate fees
        config = self._get_payment_config()
        if not config and not self.is_staging:
            raise ValueError("Payment configuration missing for this property.")
        if not config and self.is_staging:
            config = PaymentConfiguration.objects.create(property=self.unit.property)

        payout_method = self._get_landlord_payout_method()
        calculator = RentCalculator(net_rent, config, payout_method)
        fee_breakdown = calculator.get_breakdown()
        expected_total = fee_breakdown["tenant_total"]

        if amount != expected_total:
            raise ValueError(
                f"Amount mismatch after fee calculation. Expected {expected_total}, got {amount}."
            )

        # Execute gateway
        gateway_result = self._execute_gateway(
            amount, payment_method, phone_number, provider
        )
        if not gateway_result.get("success"):
            raise ValueError(
                f"Gateway initiation failed: {gateway_result.get('error')}"
            )

        # Convert to JSON‑serializable (no Decimal)
        raw_response = make_json_serializable(gateway_result.get("raw_response", {}))
        fee_breakdown_serializable = make_json_serializable(fee_breakdown)

        # 🔥 FIX: Use today’s date as placeholder for period_start/end (non‑null constraint)
        today = timezone.now().date()

        # Create pending payment
        payment = Payment.objects.create(
            agreement=self.agreement,
            amount=amount,
            months_covered=None,
            period_start=today,  # placeholder, will be overwritten on completion
            period_end=today,  # placeholder, will be overwritten on completion
            payment_method=payment_method,
            status="pending",
            transaction_id=gateway_result.get("transaction_id", str(uuid.uuid4())),
            mobile_phone=phone_number or "",
            mobile_provider=provider or "",
            gateway_response=raw_response,
            gateway_reference=gateway_result.get("gateway_reference", ""),
            net_landlord_amount=None,
            fee_breakdown=fee_breakdown_serializable,
        )

        # Store months or installment index (optional)
        if self.plan.mode == "monthly":
            payment.months_covered = months
            payment.save(update_fields=["months_covered"])
        else:
            payment.notes = f"installment_index:{installment_index}"
            payment.save(update_fields=["notes"])

        return payment

    def _get_tenant_total_for_net_rent(self, net_rent: Decimal) -> Decimal:
        """Helper to compute tenant total including fees"""
        config = self._get_payment_config()
        payout_method = self._get_landlord_payout_method()
        if not config and not self.is_staging:
            return net_rent
        if not config and self.is_staging:
            config = PaymentConfiguration.objects.create(property=self.unit.property)
        calculator = RentCalculator(net_rent, config, payout_method)
        return calculator.get_tenant_total()

    # --------------------------------------------------
    # Phase 2: Verify and complete payment
    # --------------------------------------------------
    @transaction.atomic
    def verify_and_complete(self, payment: Payment) -> Dict[str, Any]:
        """
        Step 2: Poll gateway using payment.gateway_reference (ptn).
        If success, update agreement coverage/installments and mark payment completed.
        Returns status dict.
        """
        if payment.status != "pending":
            return {"status": payment.status, "message": "Already processed"}

        # Call gateway verification
        verification = self._verify_gateway_payment(payment.gateway_reference)
        if not verification["success"]:
            # Payment still pending or failed
            if verification.get("status") == "failed":
                payment.status = "failed"
                payment.save(update_fields=["status"])
                return {"status": "failed", "message": verification.get("error")}
            return {"status": "pending", "message": "Waiting for user confirmation"}

        # ----- SUCCESS: now update agreement and payment -----
        # Re‑fetch net_rent and fee breakdown
        net_rent = self._get_net_rent()
        if net_rent is None:
            raise ValueError("Cannot determine net rent for this payment.")

        config = self._get_payment_config()
        payout_method = self._get_landlord_payout_method()
        calculator = RentCalculator(net_rent, config, payout_method)
        fee_breakdown = calculator.get_breakdown()
        landlord_net = fee_breakdown["landlord_net"]

        # If custom amount was used, recalculate landlord_net proportionally
        if (
            self.plan.allow_custom_amount
            and payment.amount != fee_breakdown["tenant_total"]
        ):
            landlord_net = self._recalculate_landlord_net(
                payment.amount, fee_breakdown, net_rent
            )

        # Update agreement coverage or installments
        period_start, period_end, months_covered = self._update_agreement(
            payment.amount, net_rent
        )

        # Update payment record with completed info
        payment.status = "completed"
        payment.period_start = period_start
        payment.period_end = period_end
        payment.months_covered = months_covered
        payment.net_landlord_amount = landlord_net
        # Store fee breakdown as JSON-serializable
        payment.fee_breakdown = make_json_serializable(fee_breakdown)
        payment.save()

        logger.info(
            f"Payment {payment.id} completed and agreement {self.agreement.id} updated"
        )
        return {"status": "completed", "payment_id": str(payment.id)}

    # --------------------------------------------------
    # Internal helpers
    # --------------------------------------------------

    def _get_payment_config(self) -> Optional[PaymentConfiguration]:
        return getattr(self.unit.property, "payment_config", None)

    def _get_net_rent(self) -> Optional[Decimal]:
        if self.plan.mode == "monthly":
            return self.unit.monthly_rent
        else:
            status = self.agreement.installment_status
            next_idx = status.get("next_installment_index")
            if next_idx is not None:
                return Decimal(status["installments"][next_idx]["remaining"])
            return None

    def _get_landlord_payout_method(self) -> str:
        owner = self.unit.property.get_payout_owner()
        if owner and owner.preferred_payout_method:
            return owner.preferred_payout_method
        return "bank_transfer"

    def _recalculate_landlord_net(
        self, amount: Decimal, breakdown: Dict, net_rent: Decimal
    ) -> Decimal:
        original_total = breakdown["tenant_total"]
        original_landlord_net = breakdown["landlord_net"]
        if original_total == 0:
            return amount
        return (amount * original_landlord_net / original_total).quantize(Decimal("1."))

    def _execute_gateway(
        self, amount: Decimal, method: str, phone: str, provider: str
    ) -> Dict:
        """Call SmobilPay gateway to execute payment, returns ptn (gateway_reference)."""
        try:
            from django.conf import settings
            from apps.payments.gateway_SDKs.gateway_factory import gateway_factory

            gateway_config = getattr(settings, "SMOBILPAY_CONFIG", {})
            if not gateway_config.get("api_url") or not gateway_config.get(
                "public_token"
            ):
                logger.error("Missing SmobilPay configuration")
                return {"success": False, "error": "Payment gateway not configured"}

            gateway = gateway_factory.create_gateway("smobilpay", gateway_config)

            intent = gateway.create_payment_intent(
                amount=amount,
                currency="XAF",
                payment_method=method,
                customer_data={"phone_number": phone},
                metadata={"agreement_id": str(self.agreement.id)},
            )
            intent = make_json_serializable(intent)
            if intent.get("status") == "failed":
                return {"success": False, "error": intent.get("error")}

            execution = gateway.execute_payment(
                gateway_reference=intent["gateway_reference"],
                customer_authorization={"phone_number": phone},
            )
            execution = make_json_serializable(execution)

            if execution.get("status") in ["pending", "completed"]:
                return {
                    "success": True,
                    "transaction_id": execution.get("gateway_transaction_id"),
                    "gateway_reference": execution.get("gateway_transaction_id"),  # ptn
                    "raw_response": execution,
                }
            else:
                return {"success": False, "error": execution.get("error")}

        except Exception as e:
            logger.exception("Gateway execution failed")
            return {"success": False, "error": str(e)}

    def _verify_gateway_payment(self, ptn: str) -> Dict:
        """Poll SmobilPay gateway for payment status using ptn."""
        try:
            from django.conf import settings
            from apps.payments.gateway_SDKs.gateway_factory import gateway_factory

            gateway_config = getattr(settings, "SMOBILPAY_CONFIG", {})
            gateway = gateway_factory.create_gateway("smobilpay", gateway_config)

            status_response = gateway.verify_payment(gateway_reference=ptn)
            status_response = make_json_serializable(status_response)

            if status_response.get("status") in ["success", "completed"]:
                return {"success": True, "status": "success"}
            elif status_response.get("status") in ["failed", "error"]:
                return {
                    "success": False,
                    "status": "failed",
                    "error": status_response.get("error"),
                }
            else:
                return {"success": False, "status": "pending"}

        except Exception as e:
            logger.exception("Verification failed")
            return {"success": False, "error": str(e)}

    def _update_agreement(
        self, amount: Decimal, net_rent: Decimal
    ) -> Tuple[datetime.date, datetime.date, Optional[Decimal]]:
        if self.plan.mode == "monthly":
            return self._update_monthly_coverage(amount, net_rent)
        else:
            return self._update_yearly_installments(amount, net_rent)

    def _update_monthly_coverage(
        self, amount: Decimal, net_rent: Decimal
    ) -> Tuple[datetime.date, datetime.date, Decimal]:
        monthly_rent = self.unit.monthly_rent
        months_raw = amount / monthly_rent
        if months_raw % 1 != 0:
            raise ValueError(
                f"Amount must be exact multiple of monthly rent ({monthly_rent} XAF)."
            )
        months = int(months_raw)

        allowed_terms = (
            self.plan.allowed_monthly_terms
            if self.plan.allowed_monthly_terms
            else list(range(1, self.plan.max_months + 1))
        )
        if months not in allowed_terms:
            raise ValueError(
                f"Payment of {months} month(s) not allowed. Allowed: {allowed_terms}"
            )

        days_covered = months * 30
        current_coverage = self.agreement.coverage_end_date
        if current_coverage and current_coverage >= timezone.now().date():
            period_start = current_coverage
            new_end = current_coverage + timedelta(days=days_covered)
        else:
            period_start = timezone.now().date()
            new_end = period_start + timedelta(days=days_covered)

        repo = self._get_repository()
        repo.update_coverage_end_date(self.agreement.id, new_end)
        return period_start, new_end, Decimal(months)

    def _update_yearly_installments(
        self, amount: Decimal, net_rent: Decimal
    ) -> Tuple[datetime.date, datetime.date, None]:
        status = self.agreement.installment_status
        installments = status["installments"]
        next_idx = status.get("next_installment_index")
        if next_idx is None:
            raise ValueError("Agreement already fully paid.")

        due = Decimal(installments[next_idx]["remaining"])
        if not self.plan.allow_custom_amount and amount != due:
            raise ValueError(f"Must pay full due amount {due} XAF.")
        if amount > Decimal(status["total_remaining"]):
            raise ValueError(
                f"Amount exceeds total remaining {status['total_remaining']} XAF."
            )

        remaining = amount
        total_paid = Decimal(status["total_paid"])
        total_remaining = Decimal(status["total_remaining"])

        for idx, inst in enumerate(installments):
            if remaining <= 0:
                break
            if inst["status"] != "pending":
                continue
            due = Decimal(inst["remaining"])
            if remaining >= due:
                inst["paid_amount"] = str(Decimal(inst["paid_amount"]) + due)
                inst["remaining"] = "0"
                inst["status"] = "paid"
                remaining -= due
                total_paid += due
                total_remaining -= due
            else:
                inst["paid_amount"] = str(Decimal(inst["paid_amount"]) + remaining)
                inst["remaining"] = str(due - remaining)
                total_paid += remaining
                total_remaining -= remaining
                remaining = 0

        next_idx = None
        for idx, inst in enumerate(installments):
            if inst["status"] == "pending":
                next_idx = idx
                break

        status["total_paid"] = str(total_paid)
        status["total_remaining"] = str(total_remaining)
        status["next_installment_index"] = next_idx
        repo = self._get_repository()
        repo.update_installment_status(self.agreement.id, status)

        period_start = self.agreement.start_date
        period_end = self.agreement.start_date + timedelta(days=365)
        return period_start, period_end, None

    def _get_repository(self):
        from apps.payments.repositories import RentalAgreementRepository

        return RentalAgreementRepository()
