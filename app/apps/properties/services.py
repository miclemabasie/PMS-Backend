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
    PropertyImage,
    UnitImage,
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
        # Pop non-model fields before creating the property
        images = data.pop("images", [])
        managers = data.pop("managers", [])

        with transaction.atomic():
            property = self.repository.create(
                **data
            )  # now data contains only model fields

            # Create ownership record
            self.ownership_repo.create(
                property=property, owner=owner, percentage=100, is_primary=True
            )

            # Assign managers
            if managers:
                property.managers.set(managers)

            # Create images
            if images:
                for image in images:
                    PropertyImage.objects.create(property=property, image=image)
                image = PropertyImage.objects.filter(property=property).first()
                image.is_primary = True
                image.save()

            return property

    def update_property(self, id: str, data: dict) -> Optional[Property]:
        print("@@@@@@@@@ this is the data", data)
        with transaction.atomic():
            property = self.get_by_id(id)
            if not property:
                return None

            images = data.pop("images", None)
            managers = data.pop("managers", None)

            # Update scalar fields
            property = self.repository.update(property, **data)

            # Update managers
            if managers is not None:
                property.managers.set(managers)

            has_primary_image = PropertyImage.objects.filter(
                property=property, is_primary=True
            ).exists()
            print("$$$$$$$$$$$ these are the images", images)
            # Update images
            if images is not None:
                print(
                    "##### Setting the primary image for the property",
                    has_primary_image,
                )
                property.property_images.all().delete()
                for image in images:
                    PropertyImage.objects.create(property=property, image=image)

                if not has_primary_image:
                    image = PropertyImage.objects.filter(property=property).first()
                    image.is_primary = True
                    image.save()

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

    # ... existing methods ...

    def add_property_image(self, property_id: str, image_file) -> PropertyImage:
        """Add an image to a property."""
        property = self.get_by_id(property_id)
        if not property:
            raise ValueError(f"Property with ID {property_id} not found")

        # check if poeprty does not have a primary image and set the first to be so
        if not property.get_primary_image():
            image = PropertyImage.objects.filter(property=property).first()
            if image:
                image.is_primary = True
                image.save()

        return PropertyImage.objects.create(property=property, image=image_file)

    def remove_property_image(self, image_id: int) -> None:
        """Remove a property image by its ID."""
        try:
            image = PropertyImage.objects.get(id=image_id)
            image.delete()
        except PropertyImage.DoesNotExist:
            raise ValueError(f"Image with ID {image_id} not found")

    def get_property_images(self, property_id: str):
        """Get all images for a property."""
        property = self.get_by_id(property_id)
        if not property:
            raise ValueError(f"Property with ID {property_id} not found")
        return property.property_images.all()

    def ger_property_primary_image(self, property_id: str):
        """Get the primary image for a property."""
        property = self.get_by_id(property_id)
        if not property:
            raise ValueError(f"Property with ID {property_id} not found")
        return property.get_primary_image()


# ----------------------------------------------------------------------
# Unit Service
# ----------------------------------------------------------------------
class UnitService(BaseService[Unit]):
    def __init__(self):
        super().__init__(UnitRepository())
        # self.lease_repo = LeaseRepository()

    def create_unit(self, data: dict) -> Unit:
        """Create a unit with images."""
        images = data.pop("images", [])
        unit = self.repository.create(**data)

        # Create images
        if images:
            for image in images:
                UnitImage.objects.create(unit=unit, image=image)
            image = UnitImage.objects.filter(unit=unit).first()
            image.is_primary = True
            image.save()

        return unit

    def update_unit(self, id: str, data: dict) -> Optional[Unit]:
        """Update a unit with images."""
        with transaction.atomic():
            unit = self.get_by_id(id)
            if not unit:
                return None

            images = data.pop("images", None)

            # Update scalar fields
            unit = self.repository.update(unit, **data)

            # Update images if provided
            if images is not None:
                unit.unit_images.all().delete()
                for image in images:
                    UnitImage.objects.create(unit=unit, image=image)

            return unit

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

    def add_unit_image(self, unit_id: str, image_file) -> UnitImage:
        """Add an image to a unit."""
        unit = self.get_by_id(unit_id)
        if not unit:
            raise ValueError(f"Unit with ID {unit_id} not found")
        return UnitImage.objects.create(unit=unit, image=image_file)

    def remove_unit_image(self, image_id: int) -> None:
        """Remove a unit image by its ID."""
        try:
            image = UnitImage.objects.get(id=image_id)
            image.delete()
        except UnitImage.DoesNotExist:
            raise ValueError(f"Image with ID {image_id} not found")

    def get_unit_images(self, unit_id: str):
        """Get all images for a unit."""
        unit = self.get_by_id(unit_id)
        if not unit:
            raise ValueError(f"Unit with ID {unit_id} not found")
        return unit.unit_images.all()


class PropertyOwnershipService(BaseService[PropertyOwnership]):
    def __init__(self):
        super().__init__(PropertyOwnershipRepository())
