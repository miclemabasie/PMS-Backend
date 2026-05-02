from .models import Owner, Manager, Property, PropertyOwnership, Unit
from apps.core.base_repository import DjangoRepository
from datetime import timedelta
from django.utils import timezone

# apps/properties/repositories.py
# apps/properties/repositories.py
from django.utils import timezone
from datetime import timedelta


class OwnerRepository(DjangoRepository[Owner]):
    def __init__(self):
        super().__init__(Owner)

    def update_subscription(
        self, owner, subscription_plan, status="active", start_date=None, end_date=None
    ):
        """
        Update owner's subscription details.
        If start_date/end_date not provided, default to today and today+30 days.
        """
        if start_date is None:
            start_date = timezone.now().date()
        if end_date is None:
            end_date = start_date + timedelta(days=30)

        owner.subscription_plan = subscription_plan
        owner.subscription_status = status
        owner.subscription_start_date = start_date
        owner.subscription_end_date = end_date
        owner.save(
            update_fields=[
                "subscription_plan",
                "subscription_status",
                "subscription_start_date",
                "subscription_end_date",
            ]
        )
        return owner


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

    def get_all(self):
        return self.model_class.objects.all()


class PropertyRepository(DjangoRepository[Property]):
    def __init__(self):
        super().__init__(Property)

    def find_by_owner(self, owner_id):
        return self.model_class.objects.filter(ownership_records__owner_id=owner_id)

    def find_by_manager(self, manager_id):
        # return self.model_class.objects.filter(managers__id=manager_id)
        print("running find by manager")
        return Property.objects.filter(managers__id=manager_id)


class PropertyOwnershipRepository(DjangoRepository[PropertyOwnership]):
    def __init__(self):
        super().__init__(PropertyOwnership)


class UnitRepository(DjangoRepository[Unit]):
    def __init__(self):
        super().__init__(Unit)

    def find_by_property(self, property_id):
        return self.model_class.objects.filter(property_id=property_id)

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
            return qs.filter(
                managed_properties__ownership_records__owner=user.owner_profile
            ).distinct()

        # Manager → only themselves
        if hasattr(user, "manager_profile"):
            return qs.filter(pkid=user.manager_profile.pkid)

        # All other roles (tenant, etc.) get no access
        return qs.none()


class PropertyOwnershipRepository(DjangoRepository[PropertyOwnership]):
    def __init__(self):
        super().__init__(PropertyOwnership)


class UnitRepository(DjangoRepository[Unit]):
    def __init__(self):
        super().__init__(Unit)

    def find_by_property(self, property_id):
        return self.model_class.objects.filter(property_id=property_id)

    def find_by_user(self, user, status=None):
        """
        Return units that the user has access to based on property ownership/management.

        Rules:
        - Superuser: all units
        - Owner: units from properties they own
        - Manager: units from properties they manage
        - Others: empty queryset
        """
        qs = self.model_class.objects.all().select_related("property")

        if user.is_superuser:
            return qs

        # Owner → units from owned properties
        if hasattr(user, "owner_profile"):
            if status:
                return qs.filter(
                    property__ownership_records__owner=user.owner_profile,
                    status=status,
                ).distinct()
            return qs.filter(
                property__ownership_records__owner=user.owner_profile
            ).distinct()

        # Manager → units from managed properties
        if hasattr(user, "manager_profile"):
            if status:
                return qs.filter(
                    property__managers=user.manager_profile, status=status
                ).distinct()
            return qs.filter(property__managers=user.manager_profile).distinct()

        # All other roles get no access
        return qs.none()
