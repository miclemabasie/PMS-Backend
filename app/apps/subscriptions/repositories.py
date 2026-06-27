from typing import List, Optional
from apps.core.base_repository import DjangoRepository
from apps.subscriptions.models import (
    BaseSubscriptionFeatureGroup,
    SubscriptionPlan,
    SubscriptionInvoice,
)


class BaseSubscriptionFeatureGroupRepository(
    DjangoRepository[BaseSubscriptionFeatureGroup]
):
    def __init__(self):
        super().__init__(BaseSubscriptionFeatureGroup)

    def find_by_name(self, name: str) -> Optional[BaseSubscriptionFeatureGroup]:
        try:
            return self.model_class.objects.get(name=name)
        except self.model_class.DoesNotExist:
            return None

    def find_active(self) -> List[BaseSubscriptionFeatureGroup]:
        return list(self.model_class.objects.filter(is_active=True))


class SubscriptionPlanRepository(DjangoRepository[SubscriptionPlan]):
    def __init__(self):
        super().__init__(SubscriptionPlan)

    def find_active(self) -> List[SubscriptionPlan]:
        return list(self.model_class.objects.filter(is_active=True))

    def find_by_feature_group(self, group_id: str) -> List[SubscriptionPlan]:
        return list(
            self.model_class.objects.filter(feature_group_id=group_id, is_active=True)
        )

    def get_default_plan(self) -> Optional[SubscriptionPlan]:
        """Return the cheapest active plan, or None."""
        return (
            self.model_class.objects.filter(is_active=True)
            .order_by("monthly_price")
            .first()
        )


class SubscriptionInvoiceRepository(DjangoRepository[SubscriptionInvoice]):
    def __init__(self):
        super().__init__(SubscriptionInvoice)

    def find_pending_for_owner(self, owner_id: str) -> List[SubscriptionInvoice]:
        return list(
            self.model_class.objects.filter(owner_id=owner_id, status="pending")
        )

    def find_by_owner_and_status(
        self, owner_id: str, status: str
    ) -> List[SubscriptionInvoice]:
        return list(self.model_class.objects.filter(owner_id=owner_id, status=status))

    def get_latest_for_owner(self, owner_id: str) -> Optional[SubscriptionInvoice]:
        return (
            self.model_class.objects.filter(owner_id=owner_id)
            .order_by("-created_at")
            .first()
        )
