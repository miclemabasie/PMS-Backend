from apps.rentals.models import (
    LeaseTenant,
)
from apps.core.base_repository import DjangoRepository

from apps.tenants.models import Tenant


class TenantRepository(DjangoRepository[Tenant]):
    def __init__(self):
        super().__init__(Tenant)

    def find_by_property(self, property_id):
        return self.model_class.objects.filter(leases__unit__property__id=property_id)

    def get_by_pkid(self, pkid):
        return self.model_class.objects.get(pkid=pkid)

    def find_by_id_number(self, id_number: str):
        """
        Find a tenant by their unique ID number (CNI/Passport).
        Returns a single instance or None.
        """
        try:
            # Use exact match since ID number is unique
            return self.model_class.objects.get(id_number=id_number)
        except self.model_class.DoesNotExist:
            return None


class LeaseTenantRepository(DjangoRepository[LeaseTenant]):
    def __init__(self):
        super().__init__(LeaseTenant)
