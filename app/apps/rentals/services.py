from typing import List, Optional
from django.db import transaction
from django.utils import timezone
import logging
from .models import (
    Property,
    Unit,
    Lease,
    Tenant,
    Payment,
    MaintenanceRequest,
    Vendor,
    Expense,
    Document,
    Owner,
    Manager,
    PaymentTerm,
    PropertyOwnership,
    LeaseTenant,
)
from .repositories import (
    PropertyRepository,
    UnitRepository,
    LeaseRepository,
    TenantRepository,
    PaymentRepository,
    MaintenanceRequestRepository,
    VendorRepository,
    ExpenseRepository,
    DocumentRepository,
    OwnerRepository,
    ManagerRepository,
    PaymentTermRepository,
    PropertyOwnershipRepository,
    LeaseTenantRepository,
)
from apps.core.base_service import BaseService

logger = logging.getLogger(__name__)


# ----------------------------------------------------------------------
# PaymentTerm Service
# ----------------------------------------------------------------------
class PaymentTermService(BaseService[PaymentTerm]):
    def __init__(self):
        super().__init__(PaymentTermRepository())


# ----------------------------------------------------------------------
# Owner Service
# ----------------------------------------------------------------------
class OwnerService(BaseService[Owner]):
    def __init__(self):
        super().__init__(OwnerRepository())

    def get_or_create_for_user(self, user):
        """Ensure an owner profile exists for the user."""
        try:
            return user.owner_profile
        except Owner.DoesNotExist:
            return self.create(user=user)


# ----------------------------------------------------------------------
# Manager Service
# ----------------------------------------------------------------------
class ManagerService(BaseService[Manager]):
    def __init__(self):
        super().__init__(ManagerRepository())

    def get_or_create_for_user(self, user):
        try:
            return user.manager_profile
        except Manager.DoesNotExist:
            return self.create(user=user)


# ----------------------------------------------------------------------
# Property Service
# ----------------------------------------------------------------------
class PropertyService(BaseService[Property]):
    def __init__(self):
        super().__init__(PropertyRepository())
        self.owner_repo = OwnerRepository()
        self.manager_repo = ManagerRepository()
        self.ownership_repo = PropertyOwnershipRepository()

    def create_property(
        self, data: dict, owner: Owner, manager_ids: List[str] = None
    ) -> Property:
        with transaction.atomic():
            # Remove many-to-many fields from data
            manager_ids = manager_ids or []
            property = self.repository.create(**data)
            # Create ownership record
            self.ownership_repo.create(
                property=property, owner=owner, percentage=100, is_primary=True
            )
            if manager_ids:
                managers = self.manager_repo.filter(id__in=manager_ids)
                property.managers.set(managers)
            return property

    def update_property(
        self, id: str, data: dict, manager_ids: List[str] = None
    ) -> Optional[Property]:
        with transaction.atomic():
            property = self.get_by_id(id)
            if not property:
                return None
            # Update scalar fields
            property = self.repository.update(property, **data)
            if manager_ids is not None:
                managers = self.manager_repo.filter(id__in=manager_ids)
                property.managers.set(managers)
            return property

    def get_properties_for_user(self, user):
        if user.is_superuser:
            return self.get_all()
        elif hasattr(user, "owner_profile"):
            return self.repository.find_by_owner(user.owner_profile.id)
        elif hasattr(user, "manager_profile"):
            return self.repository.find_by_manager(user.manager_profile.id)
        else:
            return []


# ----------------------------------------------------------------------
# Unit Service
# ----------------------------------------------------------------------
class UnitService(BaseService[Unit]):
    def __init__(self):
        super().__init__(UnitRepository())
        self.lease_repo = LeaseRepository()

    def get_units_for_property(self, property_id):
        return self.repository.find_by_property(property_id)

    def get_available_units(self, property_id=None):
        filters = {"status": "vacant"}
        if property_id:
            filters["property_id"] = property_id
        return self.repository.filter(**filters)

    def update_unit_status(self, unit_id, status):
        unit = self.get_by_id(unit_id)
        if unit:
            unit.status = status
            unit.save()
            return unit
        return None


# ----------------------------------------------------------------------
# Lease Service
# ----------------------------------------------------------------------
class LeaseService(BaseService[Lease]):
    def __init__(self):
        super().__init__(LeaseRepository())
        self.tenant_repo = TenantRepository()
        self.unit_service = UnitService()
        self.lease_tenant_repo = LeaseTenantRepository()

    @transaction.atomic
    def create_lease(self, data: dict, tenant_ids: List[str]) -> Lease:
        unit = data.get("unit")
        # unit = self.unit_service.get_by_id(unit_id.id)
        if not unit:
            raise ValueError("Unit not found")
        if unit.status != "vacant":
            raise ValueError("Unit is not vacant")

        # Remove tenant_ids from data
        data.pop("tenant_ids", None)

        # Create lease
        lease = self.repository.create(**data)
        # Add tenants
        added_tenants = []
        for tenant_id in tenant_ids:
            tenant = self.tenant_repo.get_by_pkid(tenant_id)
            if tenant:
                logger.debug("Adding tenant %s to lease %s", tenant_id, lease.id)
                self.lease_tenant_repo.create(
                    lease=lease, tenant=tenant, is_primary=(tenant_id == tenant_ids[0])
                )
                added_tenants.append(tenant_id)
            else:
                logger.warning("Tenant not found: %s", tenant_id)
        if not added_tenants:
            raise ValueError("No valid tenants found for the provided tenant_ids")
        # Update unit status
        self.unit_service.update_unit_status(unit.id, "occupied")
        return lease

    @transaction.atomic
    def terminate_lease(self, lease_id: str, termination_date, reason: str = ""):
        lease = self.get_by_id(lease_id)
        if not lease or lease.status != "active":
            return None
        lease.status = "terminated"
        lease.termination_reason = reason
        lease.end_date = termination_date
        lease.save()
        # Update unit status
        self.unit_service.update_unit_status(lease.unit.id, "vacant")
        return lease

    @transaction.atomic
    def renew_lease(self, lease_id: str, new_end_date: str, new_rent_amount=None):
        old_lease = self.get_by_id(lease_id)
        if not old_lease or old_lease.status not in ["active", "expired"]:
            return None
        # Create new lease based on old one
        new_lease_data = {
            "unit": old_lease.unit,
            "payment_term": old_lease.payment_term,
            "rent_amount": new_rent_amount or old_lease.rent_amount,
            "due_day": old_lease.due_day,
            "start_date": old_lease.end_date + timezone.timedelta(days=1),
            "end_date": new_end_date,
            "security_deposit": old_lease.security_deposit,
            "late_fee_type": old_lease.late_fee_type,
            "late_fee_value": old_lease.late_fee_value,
            "utilities_included": old_lease.utilities_included,
            "documents": old_lease.documents,
            "renewed_from": old_lease,
        }
        new_lease = self.repository.create(**new_lease_data)
        # Copy tenants
        for lt in old_lease.lease_tenants.all():
            self.lease_tenant_repo.create(
                lease=new_lease, tenant=lt.tenant, is_primary=lt.is_primary
            )
        # Update old lease status
        old_lease.status = "renewed"
        old_lease.save()
        return new_lease

    def get_active_leases_for_tenant(self, tenant_id):
        return self.repository.filter(
            lease_tenants__tenant_id=tenant_id, status="active"
        )


# ----------------------------------------------------------------------
# Payment Service
# ----------------------------------------------------------------------
class PaymentService(BaseService[Payment]):
    def __init__(self):
        super().__init__(PaymentRepository())
        self.lease_service = LeaseService()

    def record_payment(self, lease_id: str, data: dict) -> Payment:
        # Validate period does not overlap existing payments? (simplified)
        lease = self.lease_service.get_by_id(lease_id)
        if not lease:
            raise ValueError("Lease not found")
        # Ensure period is within lease dates
        if (
            data["period_start"] < lease.start_date
            or data["period_end"] > lease.end_date
        ):
            raise ValueError("Payment period outside lease dates")
        # Create payment
        data["lease"] = lease
        return self.repository.create(**data)

    def get_payments_for_lease(self, lease_id):
        return self.repository.filter(lease_id=lease_id)

    def get_outstanding_balance(self, lease_id):
        lease = self.lease_service.get_by_id(lease_id)
        if not lease:
            return 0
        # Total expected rent for the lease duration (simplified: per period)
        # This is complex; we'll compute based on periods.
        # For now, return sum of rent amounts for unpaid periods.
        # We'll need a proper method later.
        pass


# ----------------------------------------------------------------------
# Vendor Service
# ----------------------------------------------------------------------
class VendorService(BaseService[Vendor]):
    def __init__(self):
        super().__init__(VendorRepository())


# ----------------------------------------------------------------------
# MaintenanceRequest Service
# ----------------------------------------------------------------------
class MaintenanceRequestService(BaseService[MaintenanceRequest]):
    def __init__(self):
        super().__init__(MaintenanceRequestRepository())

    def assign_vendor(self, request_id, vendor_id, estimated_cost=None):
        req = self.get_by_id(request_id)
        if req:
            req.assigned_vendor_id = vendor_id
            req.estimated_cost = estimated_cost
            req.status = "assigned"
            req.save()
            return req
        return None

    def complete_request(self, request_id, actual_cost, notes=""):
        req = self.get_by_id(request_id)
        if req:
            req.actual_cost = actual_cost
            req.notes = notes
            req.status = "completed"
            req.completed_at = timezone.now()
            req.save()
            return req
        return None


# ----------------------------------------------------------------------
# Expense Service
# ----------------------------------------------------------------------
class ExpenseService(BaseService[Expense]):
    def __init__(self):
        super().__init__(ExpenseRepository())


# ----------------------------------------------------------------------
# Document Service
# ----------------------------------------------------------------------
class DocumentService(BaseService[Document]):
    def __init__(self):
        super().__init__(DocumentRepository())
