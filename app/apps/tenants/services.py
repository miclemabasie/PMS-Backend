from typing import List, Optional
from django.db import transaction
from django.utils import timezone
import logging
from .models import (
    Tenant,
)
from .repositories import (
    TenantRepository,
    LeaseTenantRepository,
)
from apps.core.base_service import BaseService

logger = logging.getLogger(__name__)


class TenantService(BaseService[Tenant]):
    def __init__(self):
        super().__init__(TenantRepository())

    def get_tenants_for_property(self, property_id):
        logger.info("Get tenants for property with id %s", property_id)
        return self.repository.find_by_property(property_id)
