from .models import (
    PaymentTerm,
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
