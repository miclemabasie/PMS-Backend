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

    def get_queryset_for_user(self, user):
        """
        Return a QuerySet of leases that the given user is allowed to see.
        Rules:
        - Superuser: all leases
        - Owner: leases from properties they own
        - Manager: leases from properties they manage
        - Tenant: leases they are part of (through LeaseTenant)
        """
        qs = (
            self.model_class.objects.all()
            .select_related("unit__property")
            .prefetch_related("lease_tenants__tenant__user", "payments")
        )

        if user.is_superuser:
            return qs

        # Owners
        if hasattr(user, "owner_profile"):
            return qs.filter(
                unit__property__ownership_records__owner=user.owner_profile
            )

        # Managers
        if hasattr(user, "manager_profile"):
            return qs.filter(unit__property__managers=user.manager_profile)

        # Tenants
        if hasattr(user, "tenant_profile"):
            return qs.filter(lease_tenants__tenant=user.tenant_profile)

        # No relevant role → return empty queryset
        return qs.none()


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
