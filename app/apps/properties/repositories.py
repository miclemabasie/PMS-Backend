from .models import (
    Owner,
    Manager,
    Property,
    PropertyOwnership,
)
from apps.core.base_repository import DjangoRepository


class OwnerRepository(DjangoRepository[Owner]):
    def __init__(self):
        super().__init__(Owner)


class ManagerRepository(DjangoRepository[Manager]):
    def __init__(self):
        super().__init__(Manager)


class PropertyRepository(DjangoRepository[Property]):
    def __init__(self):
        super().__init__(Property)

    def find_by_owner(self, owner_id):
        return self.model_class.objects.filter(ownership_records__owner_id=owner_id)

    def find_by_manager(self, manager_id):
        return self.model_class.objects.filter(managers__id=manager_id)


class PropertyOwnershipRepository(DjangoRepository[PropertyOwnership]):
    def __init__(self):
        super().__init__(PropertyOwnership)
