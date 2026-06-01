from apps.core.base_repository import DjangoRepository
from apps.maintenance.models import MaintenanceRequest


class MaintenanceRequestRepository(DjangoRepository[MaintenanceRequest]):
    def __init__(self):
        super().__init__(MaintenanceRequest)

    def count_pending_for_owner(self, owner_id):
        return (
            self.model_class.objects.filter(
                unit__property__ownership_records__owner_id=owner_id
            )
            .exclude(status__in=["completed", "cancelled"])
            .count()
        )
