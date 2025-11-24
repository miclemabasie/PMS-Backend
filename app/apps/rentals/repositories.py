from .models import (
    PaymentTerm,
    Owner,
    Manager,
    Tenant,
    Property,
    PropertyOwnership,
    Unit,
    Lease,
    LeaseTenant,
    Payment,
    Vendor,
    MaintenanceRequest,
    Expense,
    Document,
)
from apps.core.base_repository import DjangoRepository


class PaymentTermRepository(DjangoRepository[PaymentTerm]):
    def __init__(self):
        super().__init__(PaymentTerm)


class OwnerRepository(DjangoRepository[Owner]):
    def __init__(self):
        super().__init__(Owner)


class ManagerRepository(DjangoRepository[Manager]):
    def __init__(self):
        super().__init__(Manager)


class TenantRepository(DjangoRepository[Tenant]):
    def __init__(self):
        super().__init__(Tenant)


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


class UnitRepository(DjangoRepository[Unit]):
    def __init__(self):
        super().__init__(Unit)

    def find_by_property(self, property_id):
        return self.model_class.objects.filter(property_id=property_id)


class LeaseRepository(DjangoRepository[Lease]):
    def __init__(self):
        super().__init__(Lease)

    def find_active_by_unit(self, unit_id):
        return self.model_class.objects.filter(unit_id=unit_id, status="active").first()


class LeaseTenantRepository(DjangoRepository[LeaseTenant]):
    def __init__(self):
        super().__init__(LeaseTenant)


class PaymentRepository(DjangoRepository[Payment]):
    def __init__(self):
        super().__init__(Payment)


class VendorRepository(DjangoRepository[Vendor]):
    def __init__(self):
        super().__init__(Vendor)


class MaintenanceRequestRepository(DjangoRepository[MaintenanceRequest]):
    def __init__(self):
        super().__init__(MaintenanceRequest)


class ExpenseRepository(DjangoRepository[Expense]):
    def __init__(self):
        super().__init__(Expense)


class DocumentRepository(DjangoRepository[Document]):
    def __init__(self):
        super().__init__(Document)
