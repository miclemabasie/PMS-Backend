from apps.core.base_repository import DjangoRepository
from apps.maintenance.models import MaintenanceRequest


class MaintenanceRequestRepository(DjangoRepository[MaintenanceRequest]):
    def __init__(self):
        super().__init__(MaintenanceRequest)
