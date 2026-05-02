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
    SubscriptionPlanRepository,
)
from .dummy_payment_processor import DummyPaymentProcessor
from .models import PaymentPlan, Installment, RentalAgreement, Payment, SubscriptionPlan
from typing import Optional, List, Dict, Any
from .permissions import CanManageRentalAgreement
from django.core.exceptions import PermissionDenied
from .permissions import user_can_manage_agreement
from apps.properties.models import PaymentConfiguration
from .utils.rent_calculator import RentCalculator
from apps.payments.managers.payment_manager import PaymentManager

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
        if (
            payment_plan.mode == "monthly" and unit.rent_duration_type != "monthly"
        ) or (payment_plan.mode == "yearly" and unit.rent_duration_type != "yearly"):
            logger.warning(
                f"PaymentPlan mode '{payment_plan.mode}' does not match Unit rent_duration_type '{unit.rent_duration_type}'. "
                "Proceeding anyway, but amounts may be unexpected."
            )
            raise ValueError("PaymentPlan mode does not match Unit rent_duration_type.")
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
        unit.status = "occupied"
        unit.save()
        return agreement

    def get_available_payment_options(self, agreement: RentalAgreement) -> list:
        plan = agreement.payment_plan
        config = agreement.unit.property.payment_config
        if not config:
            config = PaymentConfiguration.objects.create(
                property=agreement.unit.property
            )  # fallback
        landlord_payout_method = (
            agreement.unit.property.get_payout_owner().preferred_payout_method
        )

        if plan.mode == "monthly":
            options = []
            terms = plan.allowed_monthly_terms or range(1, plan.max_months + 1)
            for months in terms:
                net_rent = agreement.unit.monthly_rent * months
                calc = RentCalculator(net_rent, config, landlord_payout_method)
                tenant_total = calc.get_tenant_total()
                options.append(
                    {
                        "type": "monthly",
                        "months": months,
                        "amount": str(tenant_total),
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

    def get_all_agreements(self):
        return self.repository.find_all()

    @transaction.atomic
    def make_payment(
        self,
        agreement: RentalAgreement,
        amount: Decimal,
        payment_method: str,
        phone_number: str = None,
        provider: str = None,
        months: int = None,  # new
        installment_index: int = None,  # new
    ) -> Payment:
        manager = PaymentManager(agreement)
        return manager.initiate_payment(
            amount, payment_method, phone_number, provider, months, installment_index
        )

    def verify_payment(self, payment_id: str) -> Dict[str, Any]:
        """Phase 2: verify pending payment and complete if successful."""
        from apps.payments.managers.payment_manager import PaymentManager

        payment = self.payment_repo.get(payment_id)
        if not payment:
            raise ValueError("Payment not found")
        manager = PaymentManager(payment.agreement)
        return manager.verify_and_complete(payment)

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

    def get_all_agreements_for_tenant(self, tenant_id: str) -> List[RentalAgreement]:
        print("this is the user id", tenant_id, "in the service")
        return self.repository.find_all_by_tenant(tenant_id)

    @transaction.atomic
    def terminate_agreement(
        self,
        agreement_id: str,
        requested_by_user,
        reason: str = "",
        mutual_agreement: bool = False,
    ) -> RentalAgreement:
        """
        Terminate a rental agreement.
        Rules:
        - If agreement is already inactive → error.
        - If the unit has active coverage (monthly) OR remaining balance (yearly):
            * Landlord MUST have tenant agreement (mutual_agreement=True)
            * Tenant can initiate termination without landlord agreement (but landlord may deny)
            For simplicity: both can initiate but mutual_agreement required if outstanding.
        - If no active coverage (monthly coverage_end_date < today) OR fully paid (yearly total_remaining=0):
            * Landlord can force terminate without mutual agreement.
            * Tenant can also request termination (landlord will be notified separately).
        """
        agreement = self.get_by_id(agreement_id)
        if not agreement:
            raise ValueError("Agreement not found.")
        if not agreement.is_active:
            raise ValueError("Agreement is already terminated or inactive.")

        unit = agreement.unit
        plan = agreement.payment_plan
        is_outstanding = False

        # Determine if there is any outstanding financial obligation
        if plan.mode == "monthly":
            if (
                agreement.coverage_end_date
                and agreement.coverage_end_date >= timezone.now().date()
            ):
                is_outstanding = True
        else:  # yearly
            remaining = Decimal(
                agreement.installment_status.get("total_remaining", "0")
            )
            if remaining > 0:
                is_outstanding = True

        # Determine termination type and permissions
        user_role = getattr(requested_by_user, "role", None)
        is_landlord = (
            hasattr(requested_by_user, "owner_profile") or user_role == "landlord"
        )
        is_tenant = (
            hasattr(requested_by_user, "tenant_profile") or user_role == "tenant"
        )

        if not is_landlord and not is_tenant:
            raise PermissionDenied(
                "Only landlord or tenant can terminate an agreement."
            )

        termination_type = None
        if is_landlord and is_outstanding:
            if not mutual_agreement:
                raise PermissionDenied(
                    "This agreement has outstanding payments. Tenant agreement is required to terminate."
                )
            termination_type = "mutual_agreement"
        elif is_landlord and not is_outstanding:
            termination_type = "landlord_forced"
        elif is_tenant:
            # Tenant can always request termination, but landlord may later approve?
            # For simplicity, we allow tenant to terminate only if no outstanding OR mutual_agreement.
            if is_outstanding:
                if not mutual_agreement:
                    raise PermissionDenied(
                        "You cannot terminate while payments are outstanding. Please contact landlord."
                    )
                termination_type = "mutual_agreement"
            else:
                termination_type = "tenant_initiated"
        else:
            termination_type = (
                "mutual_agreement" if mutual_agreement else "landlord_initiated"
            )

        # Record termination details
        agreement.is_active = False
        agreement.termination_date = timezone.now().date()
        agreement.termination_reason_text = reason
        agreement.termination_type = termination_type
        agreement.terminated_by = requested_by_user
        agreement.save(
            update_fields=[
                "is_active",
                "termination_date",
                "termination_reason_text",
                "termination_type",
                "terminated_by",
            ]
        )

        # Set unit status back to vacant
        unit.status = "vacant"
        unit.save(update_fields=["status"])

        # Optional: create a separate TerminationEvent model for legal logs
        # We'll rely on the fields above.

        return agreement

    def get_agreements_for_user(self, user) -> List[RentalAgreement]:
        """Retrieve all agreements the user has permission to view."""
        return self.repository.find_all_by_user(user)


class SubscriptionPlanService(BaseService[SubscriptionPlan]):
    def __init__(self):
        super().__init__(SubscriptionPlanRepository())

    def get_active_plans(self):
        """Public list of active plans."""
        return self.repository.find_active()

    def create_plan(self, data):
        """Admin only – create new subscription plan."""
        return self.repository.create(**data)

    def update_plan(self, plan_id, data):
        """Admin only – update existing plan."""
        plan = self.get_by_id(plan_id)
        if not plan:
            raise ValueError("Plan not found")
        return self.repository.update(plan, **data)

    def delete_plan(self, plan_id):
        """Soft delete (set is_active=False) – admin only."""
        plan = self.get_by_id(plan_id)
        if plan:
            plan.is_active = False
            plan.save(update_fields=["is_active"])
            return True
        return False
