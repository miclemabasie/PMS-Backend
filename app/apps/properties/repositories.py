from .models import Owner, Manager, Property, PropertyOwnership, Unit
from apps.core.base_repository import DjangoRepository


class OwnerRepository(DjangoRepository[Owner]):
    def __init__(self):
        super().__init__(Owner)


class ManagerRepository(DjangoRepository[Manager]):
    def __init__(self):
        super().__init__(Manager)

    def get_queryset_for_user(self, user):
        """
        Return a QuerySet of Manager objects accessible by the given user.

        Rules:
        - Superuser: all managers.
        - Owner (landlord): managers who manage at least one property owned by this user.
        - Manager: only their own profile.
        - Tenant or any other: empty queryset.
        """
        qs = self.model_class.objects.all().select_related("user")

        if user.is_superuser:
            return qs

        # Owner (landlord) → managers through owned properties
        if hasattr(user, "owner_profile"):
            # managed_properties__ownership_records__owner links Manager to Owner via PropertyOwnership
            return qs.filter(
                managed_properties__ownership_records__owner=user.owner_profile
            ).distinct()

        # Manager → only themselves
        if hasattr(user, "manager_profile"):
            return qs.filter(pkid=user.manager_profile.pkid)

        # All other roles (tenant, etc.) get no access
        return qs.none()


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
