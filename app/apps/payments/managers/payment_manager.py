import logging
import uuid
from decimal import Decimal, ROUND_HALF_UP
from typing import Dict, Any, Optional, Tuple
from datetime import date, datetime, timedelta
from django.db import transaction
from django.utils import timezone
from django.conf import settings
from dateutil.relativedelta import relativedelta

from apps.payments.models import Payment, RentalAgreement
from apps.payments.utils.rent_calculator import RentCalculator
from apps.properties.models import PaymentOwnerSplit

logger = logging.getLogger(__name__)


def make_json_serializable(obj: Any) -> Any:
    """
    Recursively convert Decimal to string (or float) and handle other non‑serializable types.
    """
    if isinstance(obj, Decimal):
        return str(obj)
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
        self.property = self.unit.property
        self.owner = self.property.get_payout_owner()
        self.is_staging = getattr(settings, "STAGING_MODE", False) or getattr(
            settings, "DEBUG", False
        )

        if not self.owner:
            logger.warning(
                f"Property {self.property.id} has no owner; fee calculation will fallback to defaults."
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
        months: int = None,
        installment_index: int = None,
    ) -> Payment:
        """
        Step 1: Create pending payment record and call gateway execute.
        Returns Payment object with status='pending'.
        """
        amount = Decimal(str(amount))

        if not self.agreement.is_active:
            raise ValueError("Agreement is not active.")

        # --------------------------------------------------
        # 1. Validate amount and determine net_rent
        # --------------------------------------------------
        if self.plan.mode == "monthly":
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

        # --------------------------------------------------
        # 2. Calculate fees and expected total
        # --------------------------------------------------
        calculator = RentCalculator(net_rent, self.property, self.owner)
        fee_breakdown = calculator.get_breakdown()
        expected_total = fee_breakdown["tenant_total"]

        if amount != expected_total:
            if amount == net_rent:
                # Legacy fallback: accept net rent without fees (risky, but allowed)
                pass
            else:
                raise ValueError(
                    f"Amount mismatch after fee calculation. Expected {expected_total}, got {amount}."
                )

        # --------------------------------------------------
        # 3. Execute gateway
        # --------------------------------------------------
        gateway_result = self._execute_gateway(
            expected_total, payment_method, phone_number, provider
        )
        if not gateway_result.get("success"):
            raise ValueError(
                f"Gateway initiation failed: {gateway_result.get('error')}"
            )

        # --------------------------------------------------
        # 4. Create payment record (pending)
        # --------------------------------------------------
        raw_response = make_json_serializable(gateway_result.get("raw_response", {}))
        fee_breakdown_serializable = make_json_serializable(fee_breakdown)
        today = timezone.now().date()

        payment = Payment.objects.create(
            agreement=self.agreement,
            amount=amount,
            months_covered=None,
            period_start=today,  # placeholder, will be updated on completion
            period_end=today,
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

        if self.plan.mode == "monthly":
            payment.months_covered = months
            payment.save(update_fields=["months_covered"])
        else:
            payment.notes = f"installment_index:{installment_index}"
            payment.save(update_fields=["notes"])

        return payment

    def _get_tenant_total_for_net_rent(self, net_rent: Decimal) -> Decimal:
        calculator = RentCalculator(net_rent, self.property, self.owner)
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
        try:
            payment = (
                Payment.objects.select_for_update()
                .select_related("agreement")
                .get(pk=payment.pk)
            )
        except Payment.DoesNotExist:
            raise ValueError("Payment not found.")

        if payment.status != "pending":
            return {"status": payment.status, "message": "Already processed"}

        verification = self._verify_gateway_payment(payment.gateway_reference)
        if not verification["success"]:
            if verification.get("status") == "failed":
                payment.status = "failed"
                payment.save(update_fields=["status"])
                return {"status": "failed", "message": verification.get("error")}
            return {"status": "pending", "message": "Waiting for user confirmation"}

        # SUCCESS: finalize
        stored_breakdown = payment.fee_breakdown
        if not stored_breakdown:
            net_rent = self._compute_net_rent(payment)
            calculator = RentCalculator(net_rent, self.property, self.owner)
            stored_breakdown = calculator.get_breakdown()

        net_rent = self._compute_net_rent(payment)
        landlord_net = Decimal(stored_breakdown.get("landlord_net", 0))
        tenant_total_from_breakdown = Decimal(stored_breakdown.get("tenant_total", 0))
        if (
            self.plan.allow_custom_amount
            and payment.amount != tenant_total_from_breakdown
        ):
            landlord_net = self._recalculate_landlord_net(
                payment.amount, stored_breakdown, tenant_total_from_breakdown
            )

        period_start, period_end, months_covered = self._update_agreement(
            payment.amount, net_rent, payment
        )

        payment.status = "completed"
        payment.period_start = period_start
        payment.period_end = period_end
        payment.months_covered = months_covered
        payment.net_landlord_amount = landlord_net
        payment.save()

        # Create owner splits
        property_obj = self.agreement.unit.property
        ownership_records = property_obj.ownership_records.filter(percentage__gt=0)
        total_percent = sum(r.percentage for r in ownership_records)
        net_landlord_amount = payment.net_landlord_amount
        for record in ownership_records:
            share = (record.percentage / total_percent) * net_landlord_amount
            share = share.quantize(Decimal("1."), rounding=ROUND_HALF_UP)
            PaymentOwnerSplit.objects.create(
                payment=payment,
                owner=record.owner,
                amount=share,
                percentage=record.percentage,
            )

        logger.info(
            f"Payment {payment.id} completed and agreement {self.agreement.id} updated"
        )
        from apps.payments.tasks import generate_receipt_task
        generate_receipt_task.delay(str(payment.id))
        return {"status": "completed", "payment_id": str(payment.id)}

    # --------------------------------------------------
    # Internal helpers
    # --------------------------------------------------

    def _compute_net_rent(self, payment: Payment) -> Decimal:
        if self.plan.mode == "monthly":
            months = payment.months_covered
            if months is None:
                months = round(payment.amount / self.unit.monthly_rent)
            return self.unit.monthly_rent * Decimal(months)
        else:
            status = self.agreement.installment_status
            next_idx = status.get("next_installment_index")
            if next_idx is not None:
                return Decimal(status["installments"][next_idx]["remaining"])
            return Decimal(0)

    def _get_landlord_payout_method(self) -> str:
        owner = self.unit.property.get_payout_owner()
        if owner and owner.preferred_payout_method:
            return owner.preferred_payout_method
        return "bank_transfer"

    def _recalculate_landlord_net(
        self, amount: Decimal, breakdown: Dict, original_tenant_total: Decimal
    ) -> Decimal:
        original_landlord_net = Decimal(breakdown.get("landlord_net", 0))
        if original_tenant_total == 0:
            return amount
        return (amount * original_landlord_net / original_tenant_total).quantize(
            Decimal("1.")
        )

    def _execute_gateway(
        self, amount: Decimal, method: str, phone: str, provider: str
    ) -> Dict:
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
                    "gateway_reference": execution.get("gateway_transaction_id"),
                    "raw_response": execution,
                }
            else:
                return {"success": False, "error": execution.get("error")}

        except Exception as e:
            logger.exception("Gateway execution failed")
            return {"success": False, "error": str(e)}

    def _verify_gateway_payment(self, ptn: str) -> Dict:
        try:
            from django.conf import settings
            from apps.payments.gateway_SDKs.gateway_factory import gateway_factory

            gateway_config = getattr(settings, "SMOBILPAY_CONFIG", {})
            gateway = gateway_factory.create_gateway("smobilpay", gateway_config)

            status_response = gateway.verify_payment(gateway_reference=ptn)
            logger.debug(
                "Gateway verify_payment response for ptn=%s: %s", ptn, status_response
            )

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
        self, amount: Decimal, net_rent: Decimal, payment: Payment = None
    ) -> Tuple[date, date, Optional[Decimal]]:
        """
        Update agreement coverage or installments based on payment.
        Returns (period_start, period_end, months_covered).
        """
        if self.plan.mode == "monthly":
            months_override = payment.months_covered if payment else None
            return self._update_monthly_coverage(amount, net_rent, months_override)
        else:
            return self._update_yearly_installments(amount, net_rent)

    
    def _update_monthly_coverage(
        self, amount: Decimal, net_rent: Decimal, months_override: Decimal = None
    ) -> Tuple[date, date, Decimal]:
        """
        Extend coverage by a given number of calendar months.
        Uses relativedelta to handle month‑end and leap years correctly.

        Returns:
            period_start: first day of coverage (day after previous end or today)
            period_end: last day of coverage (exactly months later minus one day)
            months_covered: number of months paid for
        """
        # 1. Determine number of months
        if months_override is not None:
            months = int(months_override)
        else:
            monthly_rent = self.unit.monthly_rent
            if not monthly_rent or monthly_rent <= 0:
                raise ValueError("Monthly rent must be set and positive.")
            months_raw = amount / monthly_rent
            if months_raw % 1 != 0:
                raise ValueError(
                    f"Amount must be exact multiple of monthly rent ({monthly_rent} XAF). "
                    f"Got {amount} XAF which is {months_raw} months."
                )
            months = int(months_raw)

        # 2. Validate allowed terms
        allowed_terms = (
            self.plan.allowed_monthly_terms
            if self.plan.allowed_monthly_terms
            else list(range(1, self.plan.max_months + 1))
        )
        if months not in allowed_terms:
            raise ValueError(
                f"Payment of {months} month(s) not allowed. Allowed: {allowed_terms}"
            )

        # 3. Calculate period start
        today = timezone.now().date()
        current_coverage = self.agreement.coverage_end_date

        if current_coverage and current_coverage >= today:
            period_start = current_coverage + timedelta(days=1)
        else:
            period_start = today

        # 4. Calculate period end (exactly months later minus one day)
        period_end = period_start + relativedelta(months=months) - timedelta(days=1)

        # 5. Update agreement
        repo = self._get_repository()
        repo.update_coverage_end_date(self.agreement.id, period_end)

        return period_start, period_end, Decimal(months)
    def _update_yearly_installments(
        self, amount: Decimal, net_rent: Decimal
    ) -> Tuple[date, date, None]:
        """
        Apply payment to yearly installments.
        
        Returns:
            period_start: the first day of the current year of the agreement
            period_end: the last day of that year
            months_covered: None
        """
        status = self.agreement.installment_status
        installments = status.get("installments", [])
        next_idx = status.get("next_installment_index")

        if next_idx is None:
            raise ValueError("Agreement already fully paid.")
        if next_idx >= len(installments):
            raise ValueError("Invalid installment index.")

        due = Decimal(installments[next_idx]["remaining"])
        if not self.plan.allow_custom_amount and amount != due:
            raise ValueError(
                f"Must pay full due amount {due} XAF for installment {next_idx + 1}."
            )
        if amount > Decimal(status.get("total_remaining", "0")):
            raise ValueError(
                f"Amount exceeds total remaining {status.get('total_remaining', 0)} XAF."
            )

        # Apply payment to installments
        remaining = amount
        total_paid = Decimal(status.get("total_paid", "0"))
        total_remaining = Decimal(status.get("total_remaining", "0"))

        for idx, inst in enumerate(installments):
            if remaining <= 0:
                break
            if inst["status"] != "pending":
                continue
            inst_due = Decimal(inst["remaining"])
            if remaining >= inst_due:
                inst["paid_amount"] = str(Decimal(inst["paid_amount"]) + inst_due)
                inst["remaining"] = "0"
                inst["status"] = "paid"
                remaining -= inst_due
                total_paid += inst_due
                total_remaining -= inst_due
            else:
                inst["paid_amount"] = str(Decimal(inst["paid_amount"]) + remaining)
                inst["remaining"] = str(inst_due - remaining)
                total_paid += remaining
                total_remaining -= remaining
                remaining = 0

        # Find next pending installment
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

        # Calculate the current yearly period
        start_date = self.agreement.start_date
        today = timezone.now().date()
        
        # Compute number of full years elapsed
        years = relativedelta(today, start_date).years
        # If today is before the anniversary in the current year, subtract 1
        # We'll use the same logic as relativedelta: if the month/day is earlier, subtract 1
        if today < start_date + relativedelta(years=years):
            years -= 1
        
        period_start = start_date + relativedelta(years=years)
        period_end = period_start + relativedelta(years=1) - timedelta(days=1)

        return period_start, period_end, None

    def _get_repository(self):
        from apps.payments.repositories import RentalAgreementRepository
        return RentalAgreementRepository()

    @transaction.atomic
    def complete_from_webhook(
        self, payment: Payment, event: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Complete a payment based on a webhook event (no gateway polling).
        """
        payment = (
            Payment.objects.select_for_update()
            .select_related("agreement")
            .get(pk=payment.pk)
        )
        if payment.status != "pending":
            return {"status": payment.status, "message": "Already processed"}

        gateway_amount = event.get("amount")
        if gateway_amount and gateway_amount != payment.amount:
            payment.status = "failed"
            payment.notes += f"\nWebhook amount mismatch: expected {payment.amount}, got {gateway_amount}"
            payment.save(update_fields=["status", "notes"])
            return {"status": "failed", "message": "Amount mismatch"}

        return self._finalize_payment(payment, event)

    def _finalize_payment(self, payment: Payment, event: Dict) -> Dict:
        """Common finalisation logic used by verify_and_complete and complete_from_webhook."""
        stored_breakdown = payment.fee_breakdown
        if not stored_breakdown:
            net_rent = self._compute_net_rent(payment)
            calculator = RentCalculator(net_rent, self.property, self.owner)
            stored_breakdown = calculator.get_breakdown()

        net_rent = self._compute_net_rent(payment)
        landlord_net = Decimal(stored_breakdown.get("landlord_net", 0))
        tenant_total_from_breakdown = Decimal(stored_breakdown.get("tenant_total", 0))
        if (
            self.plan.allow_custom_amount
            and payment.amount != tenant_total_from_breakdown
        ):
            landlord_net = self._recalculate_landlord_net(
                payment.amount, stored_breakdown, tenant_total_from_breakdown
            )

        period_start, period_end, months_covered = self._update_agreement(
            payment.amount, net_rent, payment
        )

        payment.status = "completed"
        payment.period_start = period_start
        payment.period_end = period_end
        payment.months_covered = months_covered
        payment.net_landlord_amount = landlord_net
        payment.gateway_response = event.get("raw", {})
        payment.save()

        # Create owner splits
        property_obj = self.agreement.unit.property
        ownership_records = property_obj.ownership_records.filter(percentage__gt=0)
        total_percent = sum(r.percentage for r in ownership_records)
        net_landlord_amount = payment.net_landlord_amount
        for record in ownership_records:
            share = (record.percentage / total_percent) * net_landlord_amount
            share = share.quantize(Decimal("1."), rounding=ROUND_HALF_UP)
            PaymentOwnerSplit.objects.create(
                payment=payment,
                owner=record.owner,
                amount=share,
                percentage=record.percentage,
            )

        from apps.payments.services import LedgerService
        LedgerService().record_payment_ledger(payment)

        logger.info(f"Payment {payment.id} completed via webhook")
        from apps.payments.tasks import generate_receipt_task
        generate_receipt_task.delay(str(payment.id))
        return {"status": "completed", "payment_id": str(payment.id)}