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

    # New method
    def get_all_for_user(self, user):
        """
        Return all managers accessible by the given user.
        """
        return self.repository.get_queryset_for_user(user)


# ----------------------------------------------------------------------
# Property Service
# ----------------------------------------------------------------------
class PropertyService(BaseService[Property]):
    def __init__(self):
        super().__init__(PropertyRepository())
        self.owner_repo = OwnerRepository()
        self.manager_repo = ManagerRepository()
        self.ownership_repo = PropertyOwnershipRepository()

    def create_property(self, data: dict, owner: Owner) -> Property:
        # Extract managers from data before creating the property
        managers = data.pop("managers", [])  # list of Manager instances
        with transaction.atomic():
            property = self.repository.create(**data)
            self.ownership_repo.create(
                property=property, owner=owner, percentage=100, is_primary=True
            )
            if managers:
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
            return self.repository.find_by_owner(user.owner_profile.pkid)
        elif hasattr(user, "manager_profile"):
            return self.repository.find_by_manager(user.manager_profile.id)
        else:
            return []

    def add_managers(self, property_id: str, manager_ids: List[str]) -> Property:
        """
        Add one or more managers to a property.
        """
        with transaction.atomic():
            property = self.get_by_id(property_id)
            if not property:
                raise ValueError(f"Property with ID {property_id} not found")

            managers = Manager.objects.filter(pkid__in=manager_ids)
            property.managers.add(*managers)
            return property

    def remove_managers(self, property_id: str, manager_ids: List[str]) -> Property:
        """
        Remove one or more managers from a property.
        """
        with transaction.atomic():
            property = self.get_by_id(property_id)
            if not property:
                raise ValueError(f"Property with ID {property_id} not found")

            managers = Manager.objects.filter(pkid__in=manager_ids)
            property.managers.remove(*managers)
            return property

    def get_property_managers(self, property_id: str):
        """
        Get all managers assigned to a property.
        """
        property = self.get_by_id(property_id)
        if not property:
            raise ValueError(f"Property with ID {property_id} not found")

        return property.managers.all()

    def replace_managers(self, property_id: str, manager_ids: List[str]) -> Property:
        """
        Replace all managers of a property with a new set.
        """
        with transaction.atomic():
            property = self.get_by_id(property_id)
            if not property:
                raise ValueError(f"Property with ID {property_id} not found")

            managers = Manager.objects.filter(pkid__in=manager_ids)
            property.managers.set(managers)
            return property


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
