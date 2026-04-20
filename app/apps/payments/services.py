import logging
from decimal import Decimal
from datetime import date, timedelta
from dateutil.relativedelta import relativedelta
from django.db import transaction
from django.utils import timezone
from .models import PaymentPlan, Installment, RentalAgreement, Payment
from .dummy_payment_processor import DummyPaymentProcessor
import uuid

logger = logging.getLogger(__name__)


class PaymentPlanService:
    """CRUD and business logic for PaymentPlan."""

    @staticmethod
    def create_plan(data):
        plan = PaymentPlan.objects.create(**data)
        return plan

    @staticmethod
    def add_installment(plan_id, percent, due_date=None, order_index=None):
        plan = PaymentPlan.objects.get(id=plan_id)
        if order_index is None:
            order_index = plan.installments.count()
        installment = Installment.objects.create(
            payment_plan=plan,
            percent=percent,
            due_date=due_date,
            order_index=order_index,
        )
        return installment


class RentalAgreementService:
    """Handles creation and payment logic for agreements."""

    @staticmethod
    def create_agreement(unit, tenant, payment_plan):
        """
        Create a new rental agreement.
        For monthly mode: coverage_end_date initially = start_date (no coverage until first payment).
        For yearly mode: initialize installment_status JSON.
        """
        if payment_plan.mode == "monthly":
            agreement = RentalAgreement.objects.create(
                unit=unit,
                tenant=tenant,
                payment_plan=payment_plan,
                start_date=timezone.now().date(),
                coverage_end_date=timezone.now().date(),  # no coverage yet
                is_active=True,
            )
        else:  # yearly
            # Build installment_status from the plan's installments
            installments_list = []
            for inst in payment_plan.installments.all().order_by("order_index"):
                amount = (unit.yearly_rent * inst.percent / 100).quantize(Decimal("1"))
                installments_list.append(
                    {
                        "percent": float(inst.percent),
                        "amount": str(amount),
                        "paid_amount": "0",
                        "remaining": str(amount),
                        "status": "pending",
                        "due_date": (
                            inst.due_date.isoformat() if inst.due_date else None
                        ),
                    }
                )
            status = {
                "installments": installments_list,
                "total_paid": "0",
                "total_remaining": str(unit.yearly_rent),
                "next_installment_index": 0,
            }
            agreement = RentalAgreement.objects.create(
                unit=unit,
                tenant=tenant,
                payment_plan=payment_plan,
                start_date=timezone.now().date(),
                installment_status=status,
                is_active=True,
            )
        return agreement

    @staticmethod
    def get_available_payment_options(agreement):
        """
        Return a list of payment options for the agreement based on its plan.
        For monthly: list of (months, amount) from allowed_monthly_terms.
        For yearly: list of (label, amount, installment_index) for pending installments,
        plus optionally a full payment option.
        """
        plan = agreement.payment_plan
        if plan.mode == "monthly":
            options = []
            terms = (
                plan.allowed_monthly_terms
                if plan.allowed_monthly_terms
                else range(1, plan.max_months + 1)
            )
            for months in terms:
                amount = agreement.unit.monthly_rent * months
                options.append(
                    {
                        "type": "monthly",
                        "months": months,
                        "amount": str(amount),
                    }
                )
            if plan.allow_custom_amount:
                options.append(
                    {
                        "type": "custom",
                        "label": "Other amount",
                    }
                )
            return options
        else:  # yearly
            options = []
            status = agreement.installment_status
            next_idx = status.get("next_installment_index", 0)
            installments = status.get("installments", [])
            for idx, inst in enumerate(installments):
                if inst["status"] == "pending":
                    # Show only if it's the next due or plan does not enforce order
                    if not plan.enforce_installment_order or idx == next_idx:
                        options.append(
                            {
                                "type": "installment",
                                "label": f"Pay {inst['percent']}% ({inst['amount']} XAF)",
                                "amount": inst["amount"],
                                "installment_index": idx,
                            }
                        )
            if plan.show_full_payment_option:
                total_remaining = Decimal(status.get("total_remaining", "0"))
                if total_remaining > 0:
                    options.append(
                        {
                            "type": "full",
                            "label": f"Pay full year ({total_remaining} XAF)",
                            "amount": str(total_remaining),
                        }
                    )
            if plan.allow_custom_amount:
                options.append(
                    {
                        "type": "custom",
                        "label": "Other amount",
                    }
                )
            return options

    @staticmethod
    @transaction.atomic
    def make_payment(
        agreement, amount, payment_method, phone_number=None, provider=None
    ):
        """
        Process a payment for the agreement.
        - Validate amount against allowed options.
        - Update agreement status (coverage or installments).
        - Call dummy payment processor.
        - Create Payment record.
        """
        plan = agreement.payment_plan
        amount = Decimal(str(amount))

        # Step validation
        if amount % plan.amount_step != 0:
            raise ValueError(f"Amount must be a multiple of {plan.amount_step} XAF.")

        # Dummy payment processing
        processor = DummyPaymentProcessor()
        if payment_method in ["mtn_momo", "orange_money"] and phone_number and provider:
            result = processor.initiate_payment(amount, phone_number, provider)
        else:
            # For cash/bank, simulate success
            result = {
                "success": True,
                "transaction_id": str(uuid.uuid4()),
                "status": "completed",
            }

        if not result["success"]:
            raise Exception("Payment failed: " + result.get("message", "Unknown error"))

        # Update agreement based on mode
        period_start = None
        period_end = None
        months_covered = None

        if plan.mode == "monthly":
            # Determine how many months are covered
            if amount == agreement.unit.monthly_rent * 1:  # exact one month
                months_covered = 1
            else:
                # For simplicity, if custom amount, compute fractional months
                months_covered = amount / agreement.unit.monthly_rent
            # Update coverage_end_date
            if (
                agreement.coverage_end_date
                and agreement.coverage_end_date >= timezone.now().date()
            ):
                new_end = agreement.coverage_end_date + relativedelta(
                    months=+months_covered
                )
            else:
                new_end = timezone.now().date() + relativedelta(months=+months_covered)
            agreement.coverage_end_date = new_end
            period_start = timezone.now().date()
            period_end = new_end
            agreement.save()

        else:  # yearly
            # Apply amount to installments in order
            status = agreement.installment_status
            installments = status["installments"]
            remaining = amount
            total_paid = Decimal(status["total_paid"])
            total_remaining = Decimal(status["total_remaining"])

            for idx, inst in enumerate(installments):
                if remaining <= 0:
                    break
                if inst["status"] != "pending":
                    continue
                # If enforce order and idx != next, skip? Already filtered in options.
                due = Decimal(inst["remaining"])
                if remaining >= due:
                    # Pay full installment
                    paid_this = due
                    inst["paid_amount"] = str(Decimal(inst["paid_amount"]) + due)
                    inst["remaining"] = "0"
                    inst["status"] = "paid"
                    remaining -= due
                    total_paid += due
                    total_remaining -= due
                else:
                    # Partial payment
                    paid_this = remaining
                    inst["paid_amount"] = str(Decimal(inst["paid_amount"]) + remaining)
                    inst["remaining"] = str(due - remaining)
                    # status stays pending
                    remaining = 0
                    total_paid += paid_this
                    total_remaining -= paid_this
                    # Optionally break if plan does not allow splitting across installments? We'll allow.

            # Update next_installment_index
            next_idx = 0
            for idx, inst in enumerate(installments):
                if inst["status"] == "pending":
                    next_idx = idx
                    break
            else:
                next_idx = None

            status["total_paid"] = str(total_paid)
            status["total_remaining"] = str(total_remaining)
            status["next_installment_index"] = next_idx
            agreement.installment_status = status
            agreement.save()

            # Set period_start/end for this payment (simplified: today to next due or end of year)
            period_start = timezone.now().date()
            # For yearly, period_end could be agreement start_date + 1 year, but we'll keep simple
            period_end = agreement.start_date + relativedelta(years=1)

        # Create Payment record
        payment = Payment.objects.create(
            agreement=agreement,
            amount=amount,
            months_covered=months_covered,
            period_start=period_start,
            period_end=period_end,
            payment_method=payment_method,
            status="completed",
            transaction_id=result.get("transaction_id", ""),
            mobile_phone=phone_number or "",
            mobile_provider=provider or "",
            gateway_response=result,
        )

        # If yearly and fully paid, optionally mark agreement as fully paid (but still active until end_date)
        if plan.mode == "yearly" and Decimal(status["total_remaining"]) == 0:
            # Could set a flag, but we keep is_active True until end_date
            pass

        return payment
