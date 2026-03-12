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


class LeaseTenantRepository(DjangoRepository[LeaseTenant]):
    def __init__(self):
        super().__init__(LeaseTenant)
