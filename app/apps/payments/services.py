import logging
import uuid
import re
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
    IdempotencyKeyRepository,
)
from apps.subscriptions.repositories import SubscriptionPlanRepository
from .managers.payment_manager import make_json_serializable
from .models import (
    PaymentPlan,
    Installment,
    RentalAgreement,
    Payment,
    Disbursement,
    LedgerEntry,
    AuditLog,
)

from apps.properties.services import TermTemplateService
from apps.notifications.tasks import send_notification

# New subscription models (from the new app)
from apps.subscriptions.models import SubscriptionPlan
from typing import Optional, List, Dict, Any
from .permissions import CanManageRentalAgreement
from django.core.exceptions import PermissionDenied
from .permissions import user_can_manage_agreement
from .utils.rent_calculator import RentCalculator
from apps.payments.managers.payment_manager import PaymentManager

logger = logging.getLogger(__name__)


class PaymentPlanService(BaseService[PaymentPlan]):
    def __init__(self):
        super().__init__(PaymentPlanRepository())
        self.installment_repo = InstallmentRepository()

    def get_plan_with_installments(self, plan_id: str):
        return self.repository.get_with_installments(plan_id)

    def create_payment_plan(self, user, data):
        if user.role in ("landlord", "manager"):
            return self.create(**data)
        logger.info(
            "create_payment_plan denied for user %s (role=%s)",
            getattr(user, "id", None),
            getattr(user, "role", None),
        )
        return None

    def get_installments(self, plan_id: str) -> List[Installment]:
        return self.installment_repo.filter_by_plan(plan_id)

    def add_installment(
        self, plan_id: str, percent: Decimal, due_date=None, order_index=None
    ) -> Installment:
        plan = self.get_by_id(plan_id)
        if not plan:
            raise ValueError("Payment plan not found")

        if order_index is None:
            order_index = len(self.installment_repo.filter_by_plan(plan_id))

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


from apps.payments.gateway_SDKs.gateway_factory import gateway_factory
from apps.payments.repositories import PaymentRepository
from apps.payments.managers.payment_manager import PaymentManager
from django.conf import settings


class PaymentService(BaseService[Payment]):
    def __init__(self):
        super().__init__(PaymentRepository())

    def process_webhook(
        self, gateway_name: str, payload: dict, headers: dict, raw_body: bytes
    ) -> dict:
        config = getattr(settings, "SMOBILPAY_CONFIG", {})
        gateway = gateway_factory.create_gateway(gateway_name, config)
        # We need to pass raw_body for signature verification; we'll modify process_webhook to accept raw_body
        event = gateway.process_webhook(
            payload, headers, raw_body
        )  # we'll extend signature
        gateway_ref = event.get("gateway_reference")
        if not gateway_ref:
            raise ValueError("Missing gateway_reference")
        payment_repo = PaymentRepository()
        payment = payment_repo.find_by_gateway_reference(gateway_ref)
        if not payment:
            return {"status": "ignored"}
        manager = PaymentManager(payment.agreement)
        result = manager.complete_from_webhook(payment, event)
        return result

    def get_payments_for_agreement(self, agreement_id: str) -> List[Payment]:
        return self.repository.find_by_agreement(agreement_id)


class RentalAgreementService(BaseService[RentalAgreement]):
    def __init__(self):
        super().__init__(RentalAgreementRepository())
        self.payment_repo = PaymentRepository()
        self.payment_plan_repo = PaymentPlanRepository()
        self.template_service = TermTemplateService()

    @staticmethod
    def _sanitize_phone_and_method(phone: str, method: str) -> str:
        """
        Validate and sanitize phone number for the given payment method.
        Strips +237 or 237 prefix if present, then validates exactly 9 digits.
        Returns the raw 9‑digit string.
        Raises ValueError if invalid.
        """
        if not phone:
            raise ValueError("Phone number is required for mobile money payments.")

        # Remove spaces, dashes, parentheses, etc.
        phone = re.sub(r"[\s\-\(\)]+", "", phone)

        # Remove '+' and any country code if present
        if phone.startswith("+237"):
            digits = phone[4:]  # after '+237'
        elif phone.startswith("237"):
            digits = phone[3:]  # after '237'
        else:
            digits = phone

        # Ensure we have exactly 9 digits
        if len(digits) != 9 or not digits.isdigit():
            raise ValueError(
                "Invalid phone number. Please provide a valid 9‑digit number, optionally with +237 or 237 prefix."
            )

        # Validate based on payment method
        if method == "mtn_momo":
            # MTN: 650-654, 670-679, 680-686
            if not re.match(r"^(65[0-4]|67\d|68[0-6])\d{6}$", digits):
                raise ValueError(
                    "Invalid MTN MoMo number. Must start with: "
                    "650-654, 670-679, or 680-686."
                )
        elif method == "orange_money":
            # Orange: 655-659, 687-689, 690-699
            if not re.match(r"^(65[5-9]|687|688|689|69\d)\d{6}$", digits):
                raise ValueError(
                    "Invalid Orange Money number. Must start with: "
                    "655-659, 687-689, or 690-699."
                )
        else:
            # Non‑mobile money – no validation
            return digits

        return digits


    def create_agreement(self, unit, tenant, payment_plan, terms_template_id=None, custom_terms=None, **kwargs):
        """Create a rental agreement with terms, coverage/installments, and inactive state."""
        # -- Terms --
        if terms_template_id:
            terms_template = self.template_service.get_by_id(terms_template_id)
            if not terms_template or terms_template.property != unit.property:
                raise ValueError("Invalid terms template for this property")
            terms_text = terms_template.content
        elif custom_terms:
            terms_text = custom_terms
        else:
            raise ValueError("Terms are required. Please provide a template or custom terms.")

        # -- Existing logic --
        if payment_plan.mode == "monthly":
            if unit.rent_duration_type != "monthly":
                raise ValueError("PaymentPlan mode does not match Unit rent_duration_type.")
            agreement = self.repository.create(
                unit=unit,
                tenant=tenant,
                payment_plan=payment_plan,
                start_date=timezone.now().date(),
                coverage_end_date=timezone.now().date(),
                terms_text=terms_text,
                terms_template=terms_template,
                is_active=False,
                **kwargs
            )
        else:  # yearly
            if unit.rent_duration_type != "yearly":
                raise ValueError("PaymentPlan mode does not match Unit rent_duration_type.")
            installments = self.payment_plan_repo.get_with_installments(payment_plan.id).installments.all().order_by("order_index")
            installments_list = []
            for inst in installments:
                amount = (unit.yearly_rent * inst.percent / 100).quantize(Decimal("1"))
                installments_list.append({
                    "percent": float(inst.percent),
                    "amount": str(amount),
                    "paid_amount": "0",
                    "remaining": str(amount),
                    "status": "pending",
                    "due_date": inst.due_date.isoformat() if inst.due_date else None,
                })
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
                terms_text=terms_text,
                terms_template=terms_template,
                is_active=False,
                **kwargs
            )

        # -- Mark unit occupied --
        unit.status = "occupied"
        unit.save(update_fields=["status"])

        # -- Send email --
        self._send_agreement_creation_email(agreement)

        return agreement


    def _send_agreement_creation_email(self, agreement):
        frontend_url = getattr(settings, "FRONTEND_URL", "http://localhost:5734")
        accept_url = f"{frontend_url}/agreement/accept/{agreement.acceptance_token}"

        tenant_email = agreement.tenant.user.email
        tenant_name = agreement.tenant.user.get_full_name()

        property_obj = agreement.unit.property
        primary_owner = property_obj.get_payout_owner()
        landlord_name = primary_owner.user.get_full_name() if primary_owner else "Landlord"

        # Send to tenant
        send_notification.delay(
            channel="email",
            recipient=tenant_email,
            subject="Please accept your rental agreement",
            template_name="emails/payments/agreement_accept.html",
            context={
                "tenant_name": tenant_name,
                "accept_url": accept_url,
                "property_name": property_obj.name,
                "unit_number": agreement.unit.unit_number,
                "landlord_name": landlord_name,
            }
        )

    def accept_agreement(self, token, user, ip_address, user_agent):
        agreement = self.repository.get_by_acceptance_token(token)
        if not agreement:
            raise ValueError("Agreement not found or invalid token")
        if agreement.tenant.user != user:
            raise PermissionError("You are not the tenant of this agreement")

        agreement, acceptance = self.repository.accept_agreement(
            agreement.id, user, ip_address, user_agent
        )

        self._send_agreement_accepted_email(agreement)
        return agreement, acceptance

    def _send_agreement_accepted_email(self, agreement):
        property_obj = agreement.unit.property
        primary_owner = property_obj.get_payout_owner()
        landlord_email = primary_owner.user.email if primary_owner else None

        if landlord_email:
            frontend_url = getattr(settings, "FRONTEND_URL", "http://localhost:5734")
            send_notification.delay(
                channel="email",
                recipient=landlord_email,
                subject="Tenant accepted the rental agreement",
                template_name="emails/payments/agreement_accepted.html",
                context={
                    "tenant_name": agreement.tenant.user.get_full_name(),
                    "property_name": property_obj.name,
                    "unit_number": agreement.unit.unit_number,
                    "agreement_id": agreement.id,
                    "frontend_url": frontend_url,
                    "landlord_name": primary_owner.user.get_full_name(),
                }
            )

    def get_acceptance_data(self, agreement_id):
        agreement = self.get_by_id(agreement_id)
        if not agreement:
            raise ValueError("Agreement not found")
        if not agreement.is_active:
            raise ValueError("Agreement has not been accepted yet")
        acceptance = getattr(agreement, "acceptance_record", None)
        if not acceptance:
            raise ValueError("No acceptance record found (agreement accepted but record missing)")
        return acceptance


    # def create_agreement(self, unit, tenant, payment_plan) -> RentalAgreement:
    #     if (
    #         payment_plan.mode == "monthly" and unit.rent_duration_type != "monthly"
    #     ) or (payment_plan.mode == "yearly" and unit.rent_duration_type != "yearly"):
    #         logger.warning(
    #             f"PaymentPlan mode '{payment_plan.mode}' does not match Unit rent_duration_type '{unit.rent_duration_type}'. "
    #             "Proceeding anyway, but amounts may be unexpected."
    #         )
    #         raise ValueError("PaymentPlan mode does not match Unit rent_duration_type.")
    #     if payment_plan.mode == "monthly":
    #         agreement = self.repository.create(
    #             unit=unit,
    #             tenant=tenant,
    #             payment_plan=payment_plan,
    #             start_date=timezone.now().date(),
    #             coverage_end_date=timezone.now().date(),
    #             is_active=True,
    #         )
    #     else:  # yearly
    #         installments = (
    #             self.payment_plan_repo.get_with_installments(payment_plan.id)
    #             .installments.all()
    #             .order_by("order_index")
    #         )
    #         installments_list = []
    #         for inst in installments:
    #             amount = (unit.yearly_rent * inst.percent / 100).quantize(Decimal("1"))
    #             installments_list.append(
    #                 {
    #                     "percent": float(inst.percent),
    #                     "amount": str(amount),
    #                     "paid_amount": "0",
    #                     "remaining": str(amount),
    #                     "status": "pending",
    #                     "due_date": (
    #                         inst.due_date.isoformat() if inst.due_date else None
    #                     ),
    #                 }
    #             )
    #         status_data = {
    #             "installments": installments_list,
    #             "total_paid": "0",
    #             "total_remaining": str(unit.yearly_rent),
    #             "next_installment_index": 0,
    #         }
    #         agreement = self.repository.create(
    #             unit=unit,
    #             tenant=tenant,
    #             payment_plan=payment_plan,
    #             start_date=timezone.now().date(),
    #             installment_status=status_data,
    #             is_active=True,
    #         )
    #     unit.status = "occupied"
    #     unit.save()
    #     return agreement

    def get_available_payment_options(self, agreement: RentalAgreement) -> list:
        plan = agreement.payment_plan
        property_obj = agreement.unit.property
        owner = property_obj.get_payout_owner()  # Primary owner

        if plan.mode == "monthly":
            options = []
            terms = plan.allowed_monthly_terms or range(1, plan.max_months + 1)
            for months in terms:
                net_rent = agreement.unit.monthly_rent * months
                calc = RentCalculator(net_rent, property_obj, owner)
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

    def make_payment_with_idempotency(
        self,
        agreement: RentalAgreement,
        amount: Decimal,
        payment_method: str,
        phone_number: Optional[str] = None,
        provider: Optional[str] = None,
        months: Optional[int] = None,
        installment_index: Optional[int] = None,
        idempotency_key: Optional[str] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Initiate a payment with idempotency support.
        If idempotency_key is provided and already processed, returns cached response.
        """
        if idempotency_key:
            repo = IdempotencyKeyRepository()
            cached = repo.get_by_key(idempotency_key, "payment")
            if cached:
                # Return the cached serialized response
                return cached.response_data

        # Call the existing make_payment method (which returns a Payment instance)
        payment = self.make_payment(
            agreement=agreement,
            amount=amount,
            payment_method=payment_method,
            phone_number=phone_number,
            provider=provider,
            months=months,
            installment_index=installment_index,
            **kwargs,
        )

        # Serialize the payment for response caching
        from .serializers import PaymentSerializer

        response_data = PaymentSerializer(payment).data

        if idempotency_key:
            repo.save_response(idempotency_key, "payment", response_data)

        return response_data

    @transaction.atomic
    def make_payment(
        self,
        agreement: RentalAgreement,
        amount: Decimal,
        payment_method: str,
        phone_number: str = None,
        provider: str = None,
        months: int = None,
        installment_index: int = None,
    ) -> Payment:

        if payment_method in ["mtn_momo", "orange_money"]:
            phone_number = self._sanitize_phone_and_method(phone_number, payment_method)

        manager = PaymentManager(agreement)
        return manager.initiate_payment(
            amount, payment_method, phone_number, provider, months, installment_index
        )

    def verify_payment(self, payment_id: str) -> Dict[str, Any]:
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
        return self.repository.find_all_by_tenant(tenant_id)

    @transaction.atomic
    def terminate_agreement(
        self,
        agreement_id: str,
        requested_by_user,
        reason: str = "",
        mutual_agreement: bool = False,
    ) -> RentalAgreement:
        agreement = self.get_by_id(agreement_id)
        if not agreement:
            raise ValueError("Agreement not found.")
        if not agreement.is_active:
            raise ValueError("Agreement is already terminated or inactive.")

        unit = agreement.unit
        plan = agreement.payment_plan
        is_outstanding = False
        today = timezone.now().date()

        if plan.mode == "monthly":
            if (
                agreement.coverage_end_date is None
                or agreement.coverage_end_date < today
            ):
                is_outstanding = True
        else:  # yearly
            remaining = Decimal(
                agreement.installment_status.get("total_remaining", "0")
            )
            if remaining > 0:
                is_outstanding = True

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

        unit.status = "vacant"
        unit.save(update_fields=["status"])
        return agreement

    def get_agreements_for_user(self, user) -> List[RentalAgreement]:
        return self.repository.find_all_by_user(user)

    @transaction.atomic
    def record_manual_payment(
        self,
        agreement_id,
        amount,
        payment_method,
        payment_date=None,
        notes="",
        recorded_by_user=None,
    ):
        agreement = self.get_agreement_for_user(agreement_id, recorded_by_user)
        if not agreement.is_active:
            raise ValueError("Cannot record payment for inactive agreement")

        property_obj = agreement.unit.property
        owner = property_obj.get_payout_owner()
        if not owner:
            raise ValueError("Property has no primary owner; cannot calculate fees.")

        # Determine net rent based on plan mode
        if agreement.payment_plan.mode == "monthly":
            net_rent = agreement.unit.monthly_rent
        else:
            status = agreement.installment_status
            next_idx = status.get("next_installment_index")
            if next_idx is None:
                raise ValueError("Agreement is already fully paid")
            net_rent = Decimal(status["installments"][next_idx]["remaining"])

        calculator = RentCalculator(net_rent, property_obj, owner)
        fee_breakdown = calculator.get_breakdown()
        expected_total = fee_breakdown["tenant_total"]

        # Validate amount
        if amount != expected_total:
            if not agreement.payment_plan.allow_custom_amount:
                raise ValueError(
                    f"Amount must be exactly {expected_total} XAF for this plan."
                )
            # Recalculate landlord net proportionally
            landlord_net = (
                amount * fee_breakdown["landlord_net"] / expected_total
            ).quantize(Decimal("1."))
        else:
            landlord_net = fee_breakdown["landlord_net"]

        payment_repo = PaymentRepository()
        payment = payment_repo.create(
            agreement=agreement,
            amount=amount,
            payment_method=payment_method,
            status="completed",
            payment_date=payment_date or timezone.now().date(),
            period_start=timezone.now().date(),
            period_end=timezone.now().date(),
            net_landlord_amount=landlord_net,
            fee_breakdown=make_json_serializable(fee_breakdown),
            notes=notes,
        )

        # Use PaymentManager to update agreement coverage/installments
        manager = PaymentManager(agreement)
        period_start, period_end, months_covered = manager._update_agreement(
            amount, net_rent, payment
        )
        payment.period_start = period_start
        payment.period_end = period_end
        payment.months_covered = months_covered
        payment.save(update_fields=["period_start", "period_end", "months_covered"])

        return payment


# apps/payments/services.py (excerpt)

from apps.subscriptions.repositories import (
    SubscriptionPlanRepository as NewSubscriptionPlanRepository,
)
from apps.subscriptions.models import SubscriptionPlan as NewSubscriptionPlan


class SubscriptionPlanService(BaseService[NewSubscriptionPlan]):
    """
    Service for managing subscription plans using the new subscription models
    (from apps.subscriptions.models).
    """

    def __init__(self):
        super().__init__(NewSubscriptionPlanRepository())  # ✅ Use new repository

    def get_active_plans(self):
        """Public list of active plans."""
        return self.repository.find_active()

    def get_default_plan(self):
        """Return the default (cheapest) active plan."""
        return self.repository.get_default_plan()

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

    """
    Service for managing subscription plans using the new subscription models
    (from apps.subscriptions.models).
    """

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


class DisbursementService:
    def process_pending_disbursements(self):
        from apps.payments.models import PaymentOwnerSplit

        splits = PaymentOwnerSplit.objects.filter(
            payment__status="completed", disbursement__isnull=True
        ).select_related("owner")
        for split in splits:
            # Check if already exists
            if Disbursement.objects.filter(
                payment_split=split, status__in=["pending", "processing", "completed"]
            ).exists():
                continue
            disbursement = Disbursement.objects.create(
                payment_split=split, status="pending"
            )
            try:
                self._disburse_split(disbursement)
            except Exception as e:
                disbursement.status = "failed"
                disbursement.error_message = str(e)
                disbursement.save()

    def _disburse_split(self, disbursement):
        split = disbursement.payment_split
        owner = split.owner
        gateway = gateway_factory.create_gateway("smobilpay", settings.SMOBILPAY_CONFIG)
        result = gateway.cashout(
            amount=split.amount,
            currency="XAF",
            recipient_data={
                "phone_number": str(owner.mobile_money_number),
                "payment_method": owner.preferred_payout_method,
            },
            metadata={"disbursement_id": str(disbursement.id)},
        )
        if result.get("status") == "completed":
            disbursement.status = "completed"
            disbursement.gateway_reference = result.get("gateway_transaction_id")
            disbursement.processed_at = timezone.now()
        else:
            disbursement.status = "failed"
            disbursement.error_message = result.get("error", "Unknown error")
        disbursement.save()


class LedgerService:
    def record_payment_ledger(self, payment):
        breakdown = payment.fee_breakdown
        if breakdown.get("platform_fee", 0) > 0:
            LedgerEntry.objects.create(
                payment=payment,
                amount=breakdown["platform_fee"],
                entry_type="platform_fee",
                description=f"Platform fee for payment {payment.id}",
            )
        if breakdown.get("gateway_fee", 0) > 0:
            LedgerEntry.objects.create(
                payment=payment,
                amount=breakdown["gateway_fee"],
                entry_type="gateway_fee",
                description=f"Gateway fee for payment {payment.id}",
            )
        # For landlord net, we can create per owner split entries or a total entry
        for split in payment.owner_splits.all():
            LedgerEntry.objects.create(
                payment=payment,
                owner=split.owner,
                amount=split.amount,
                entry_type="landlord_payout",
                description=f"Payout to {split.owner.user.email}",
            )


class AuditService:
    @staticmethod
    def log(actor, action, target, changes=None):
        AuditLog.objects.create(
            actor=actor,
            action=action,
            target_model=target._meta.model_name,
            target_id=str(target.pk),
            changes=changes or {},
        )
