from typing import List, Optional
from django.db import transaction
from django.utils import timezone
import logging
from .models import (
    Property,
    Owner,
    Manager,
    PropertyOwnership,
    Unit,
)
from .repositories import (
    PropertyRepository,
    OwnerRepository,
    ManagerRepository,
    PropertyOwnershipRepository,
    UnitRepository,
)
from apps.core.base_service import BaseService

logger = logging.getLogger(__name__)


# ----------------------------------------------------------------------
# Owner Service
# ----------------------------------------------------------------------
class OwnerService(BaseService[Owner]):
    def __init__(self):
        super().__init__(OwnerRepository())

    def create(self, **data):
        owner = self.repository.create(**data)
        owner.user.role = "landlord"
        owner.user.save()
        return owner

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
        # self.lease_repo = LeaseRepository()

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


class PropertyOwnershipService(BaseService[PropertyOwnership]):
    def __init__(self):
        super().__init__(PropertyOwnershipRepository())
