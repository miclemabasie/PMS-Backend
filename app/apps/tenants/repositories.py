from apps.core.base_repository import DjangoRepository
from apps.tenants.models import Tenant


class TenantRepository(DjangoRepository[Tenant]):
    def __init__(self):
        super().__init__(Tenant)

    def find_by_property(self, property_id):
        """
        Find all tenants that have a rental agreement for the given property.
        Uses RentalAgreement from payments app.
        """
        from apps.payments.models import RentalAgreement

        return list(
            self.model_class.objects.filter(
                agreements__unit__property__id=property_id
            ).distinct()
        )

    def find_by_unit(self, unit_id, active_only=True):
        """
        Find all tenants that have a rental agreement for the given unit.
        """
        from apps.payments.models import RentalAgreement

        qs = self.model_class.objects.filter(agreements__unit__id=unit_id)
        if active_only:
            qs = qs.filter(agreements__is_active=True)
        return list(qs.distinct())

    def get_current_tenant_for_unit(self, unit_id):
        """
        Get the active tenant for a specific unit.
        Returns Tenant object or None.
        """
        from apps.payments.models import RentalAgreement

        agreement = (
            RentalAgreement.objects.filter(unit__id=unit_id, is_active=True)
            .select_related("tenant")
            .first()
        )
        return agreement.tenant if agreement else None

    def get_by_pkid(self, pkid):
        """Get tenant by primary key."""
        return self.model_class.objects.get(pkid=pkid)

    def get_by_id(self, id):
        """Get tenant by UUID."""
        return self.model_class.objects.filter(id=id).first()

    def find_by_id_number(self, id_number: str):
        """
        Find a tenant by their unique ID number (CNI/Passport).
        """
        try:
            return self.model_class.objects.get(id_number=id_number)
        except self.model_class.DoesNotExist:
            return None

    def find_by_user(self, user):
        """Get tenant profile for a user."""
        try:
            return self.model_class.objects.get(user=user)
        except self.model_class.DoesNotExist:
            return None

    def find_by_owner(self, owner):
        """
        Find all tenants across all properties owned by a specific owner.
        """
        from apps.payments.models import RentalAgreement

        return list(
            self.model_class.objects.filter(
                agreements__unit__property__ownership_records__owner=owner
            ).distinct()
        )

    def find_by_manager(self, manager):
        """
        Find all tenants across all properties managed by a specific manager.
        """
        from apps.payments.models import RentalAgreement

        return list(
            self.model_class.objects.filter(
                agreements__unit__property__managers=manager
            ).distinct()
        )
