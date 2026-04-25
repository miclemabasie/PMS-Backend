import logging
import uuid
from decimal import Decimal
from datetime import timedelta
from django.utils import timezone
from django.db import transaction
from apps.core.base_service import BaseService
from .repositories import (
    PaymentPlanRepository,
    InstallmentRepository,
    RentalAgreementRepository,
    PaymentRepository,
)
from .dummy_payment_processor import DummyPaymentProcessor
from .models import PaymentPlan, Installment, RentalAgreement, Payment
from typing import Optional, List
from .permissions import CanManageRentalAgreement
from django.core.exceptions import PermissionDenied
from .permissions import user_can_manage_agreement


logger = logging.getLogger(__name__)


class PaymentPlanService(BaseService[PaymentPlan]):
    def __init__(self):
        super().__init__(PaymentPlanRepository())
        self.installment_repo = InstallmentRepository()

    # def add_installment(
    #     self, plan_id: str, percent: Decimal, due_date=None, order_index=None
    # ) -> Installment:
    #     plan = self.get_by_id(plan_id)
    #     if not plan:
    #         raise ValueError("Payment plan not found")
    #     if order_index is None:
    #         order_index = len(self.installment_repo.filter_by_plan(plan_id))
    #     return self.installment_repo.create(
    #         payment_plan=plan,
    #         percent=percent,
    #         due_date=due_date,
    #         order_index=order_index,
    #     )

    def get_plan_with_installments(self, plan_id: str):
        return self.repository.get_with_installments(plan_id)

    def create_payment_plan(self, user, data):
        print("This is the user:", user.__dict__, user.email)
        if user.role == "landlord":
            return self.create(**data)
        elif user.role == "manager":
            return self.create(**data)
        else:
            print("did not create anything")
            return None

    def get_installments(self, plan_id: str) -> List[Installment]:
        # No need to fetch plan first; repository filter will return empty if plan missing.
        return self.installment_repo.filter_by_plan(plan_id)

    def add_installment(
        self, plan_id: str, percent: Decimal, due_date=None, order_index=None
    ) -> Installment:
        plan = self.get_by_id(plan_id)
        if not plan:
            raise ValueError("Payment plan not found")

        if order_index is None:
            order_index = len(self.installment_repo.filter_by_plan(plan_id))

        # ✅ Correct existence check
        existing = self.installment_repo.get_by_plan_and_order(plan_id, order_index)
        if existing:
            raise ValueError(
                f"Installment with order_index {order_index} already exists"
            )

        return self.installment_repo.create(
            payment_plan=plan,
            percent=percent,
            due_date=due_date,
            order_index=order_index,
        )

    def get_payments_for_agreement(self, agreement_id: str) -> List[Payment]:

        return self.repository.find_by_agreement(agreement_id)

    def get_active_plans(self) -> List[PaymentPlan]:
        return self.repository.find_active()


class PaymentService(BaseService[Payment]):
    def __init__(self):
        super().__init__(PaymentRepository())

    def get_payments_for_agreement(self, agreement_id: str) -> List[Payment]:
        return self.repository.find_by_agreement(agreement_id)


class RentalAgreementService(BaseService[RentalAgreement]):
    def __init__(self):
        super().__init__(RentalAgreementRepository())
        self.payment_repo = PaymentRepository()
        self.payment_plan_repo = PaymentPlanRepository()

    def create_agreement(self, unit, tenant, payment_plan) -> RentalAgreement:
        if payment_plan.mode == "monthly":
            agreement = self.repository.create(
                unit=unit,
                tenant=tenant,
                payment_plan=payment_plan,
                start_date=timezone.now().date(),
                coverage_end_date=timezone.now().date(),
                is_active=True,
            )
        else:  # yearly
            # Build installment_status from the plan's installments
            installments = (
                self.payment_plan_repo.get_with_installments(payment_plan.id)
                .installments.all()
                .order_by("order_index")
            )
            installments_list = []
            for inst in installments:
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
            status_data = {
                "installments": installments_list,
                "total_paid": "0",
                "total_remaining": str(unit.yearly_rent),
                "next_installment_index": 0,
            }
            agreement = self.repository.create(
                unit=unit,
                tenant=tenant,
                payment_plan=payment_plan,
                start_date=timezone.now().date(),
                installment_status=status_data,
                is_active=True,
            )
        return agreement

    def get_available_payment_options(self, agreement: RentalAgreement) -> list:
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
                options.append({"type": "custom", "label": "Other amount"})
            return options
        else:  # yearly
            options = []
            status = agreement.installment_status
            next_idx = status.get("next_installment_index", 0)
            installments = status.get("installments", [])
            for idx, inst in enumerate(installments):
                if inst["status"] == "pending":
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
                options.append({"type": "custom", "label": "Other amount"})
            return options

    @transaction.atomic
    def make_payment(
        self,
        agreement: RentalAgreement,
        amount: Decimal,
        payment_method: str,
        phone_number: str = None,
        provider: str = None,
    ) -> Payment:
        plan = agreement.payment_plan
        amount = Decimal(str(amount))

        # # Validate amount step
        # if amount % plan.amount_step != 0:
        #     raise ValueError(f"Amount must be a multiple of {plan.amount_step} XAF.")

        # Dummy payment processing
        processor = DummyPaymentProcessor()
        if payment_method in ["mtn_momo", "orange_money"] and phone_number and provider:
            result = processor.initiate_payment(amount, phone_number, provider)
        else:
            result = {
                "success": True,
                "transaction_id": str(uuid.uuid4()),
                "status": "completed",
            }

        if not result["success"]:
            raise Exception("Payment failed: " + result.get("message", "Unknown error"))

        period_start = timezone.now().date()
        period_end = None
        months_covered = None

        if plan.mode == "monthly":
            monthly_rent = agreement.unit.monthly_rent
            # Calculate exact months from amount (must be whole number)
            months_raw = amount / monthly_rent
            if months_raw % 1 != 0:
                raise ValueError(
                    f"Amount must be an exact multiple of monthly rent ({monthly_rent} XAF)."
                )
            months = int(months_raw)

            # Check if this month count is allowed
            allowed_terms = (
                plan.allowed_monthly_terms
                if plan.allowed_monthly_terms
                else list(range(1, plan.max_months + 1))
            )
            if months not in allowed_terms:
                raise ValueError(
                    f"Payment of {months} month(s) not allowed. Allowed: {allowed_terms}"
                )

            # Update coverage
            days_covered = months * 30
            current_coverage = agreement.coverage_end_date
            if current_coverage and current_coverage >= timezone.now().date():
                new_end = current_coverage + timedelta(days=days_covered)
            else:
                new_end = timezone.now().date() + timedelta(days=days_covered)
            self.repository.update_coverage_end_date(agreement.id, new_end)
            months_covered = months
            period_end = new_end
        else:  # yearly
            status = agreement.installment_status
            installments = status["installments"]
            next_idx = status.get("next_installment_index")
            if next_idx is None:
                raise ValueError("This agreement is already fully paid.")

            print("@@@@ starting payments", installments)

            current_installment = installments[next_idx]
            due = Decimal(current_installment["remaining"])

            # If custom amounts are not allowed, amount must be exactly the due amount
            if not plan.allow_custom_amount and amount != due:
                raise ValueError(
                    f"Custom amounts not allowed. You must pay the full due amount of {due} XAF."
                )
            print("@@@@ starting payments")

            # Also, if custom allowed, ensure amount does not exceed total remaining
            total_remaining = Decimal(status["total_remaining"])
            if amount > total_remaining:
                raise ValueError(
                    f"Amount exceeds total remaining due ({total_remaining} XAF)."
                )

            # Then apply payment (the existing logic works, but we already validated)
            remaining = amount
            total_paid = Decimal(status["total_paid"])
            total_remaining = Decimal(status["total_remaining"])

            print("@@@@ starting payments")

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
                    # Partial payment (only reached if allow_custom_amount is true)
                    inst["paid_amount"] = str(Decimal(inst["paid_amount"]) + remaining)
                    inst["remaining"] = str(due - remaining)
                    total_paid += remaining
                    total_remaining -= remaining
                    remaining = 0

            # Determine next pending index
            next_idx = None
            for idx, inst in enumerate(installments):
                if inst["status"] == "pending":
                    next_idx = idx
                    break

            status["total_paid"] = str(total_paid)
            status["total_remaining"] = str(total_remaining)
            status["next_installment_index"] = next_idx
            self.repository.update_installment_status(agreement.id, status)
            period_end = agreement.start_date + timedelta(days=365)
        # Create payment record
        payment = self.payment_repo.create(
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
        return payment

    def get_active_agreement_for_unit(self, unit_id: str) -> Optional[RentalAgreement]:
        return self.repository.find_active_by_unit(unit_id)

    def get_agreement_for_user(self, agreement_id: str, user) -> RentalAgreement:
        agreement = self.get_by_id(agreement_id)
        if not agreement:
            raise ValueError("Agreement not found")
        if not user_can_manage_agreement(user, agreement):
            raise PermissionDenied(
                "You do not have permission to access this agreement."
            )
        return agreement
