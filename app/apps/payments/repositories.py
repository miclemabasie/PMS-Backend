from typing import List, Optional, Dict, Any
from django.db.models import Q
from apps.core.base_repository import DjangoRepository
from .models import PaymentPlan, Installment, RentalAgreement, Payment


class PaymentPlanRepository(DjangoRepository[PaymentPlan]):
    def __init__(self):
        super().__init__(PaymentPlan)

    def find_active(self) -> List[PaymentPlan]:
        return list(self.model_class.objects.filter(is_active=True))

    def get_with_installments(self, plan_id: str) -> Optional[PaymentPlan]:
        try:
            return self.model_class.objects.prefetch_related("installments").get(
                id=plan_id
            )
        except self.model_class.DoesNotExist:
            return None


class InstallmentRepository(DjangoRepository[Installment]):
    def __init__(self):
        super().__init__(Installment)

    def filter_by_plan(self, plan_id: str) -> List[Installment]:
        return list(
            self.model_class.objects.filter(payment_plan_id=plan_id).order_by(
                "order_index"
            )
        )


class RentalAgreementRepository(DjangoRepository[RentalAgreement]):
    def __init__(self):
        super().__init__(RentalAgreement)

    def find_active_by_unit(self, unit_id: str) -> Optional[RentalAgreement]:
        try:
            return self.model_class.objects.select_related(
                "unit", "tenant", "payment_plan"
            ).get(unit_id=unit_id, is_active=True)
        except self.model_class.DoesNotExist:
            return None

    def find_active_by_tenant(self, tenant_id: str) -> List[RentalAgreement]:
        return list(
            self.model_class.objects.filter(
                tenant_id=tenant_id, is_active=True
            ).select_related("unit", "payment_plan")
        )

    def update_installment_status(
        self, agreement_id: str, status_data: Dict[str, Any]
    ) -> RentalAgreement:
        agreement = self.get(agreement_id)
        if agreement:
            agreement.installment_status = status_data
            agreement.save(update_fields=["installment_status", "updated_at"])
        return agreement

    def update_coverage_end_date(self, agreement_id: str, new_date) -> RentalAgreement:
        agreement = self.get(agreement_id)
        if agreement:
            agreement.coverage_end_date = new_date
            agreement.save(update_fields=["coverage_end_date", "updated_at"])
        return agreement


class PaymentRepository(DjangoRepository[Payment]):
    def __init__(self):
        super().__init__(Payment)

    def find_by_agreement(self, agreement_id: str) -> List[Payment]:
        return list(
            self.model_class.objects.filter(agreement_id=agreement_id).order_by(
                "-payment_date"
            )
        )

    def find_pending_by_transaction_id(self, transaction_id: str) -> Optional[Payment]:
        try:
            return self.model_class.objects.get(
                transaction_id=transaction_id, status="pending"
            )
        except self.model_class.DoesNotExist:
            return None
