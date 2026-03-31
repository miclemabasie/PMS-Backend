from typing import List, Optional, Dict, Any
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
from apps.rentals.models import Lease, Payment

logger = logging.getLogger(__name__)


class TenantService(BaseService[Tenant]):
    def __init__(self):
        super().__init__(TenantRepository())

    def get_tenants_for_property(self, property_id):
        logger.info("Get tenants for property with id %s", property_id)
        return self.repository.find_by_property(property_id)

    # ✅ NEW: Search Tenant by ID Number
    def search_tenant_by_id(self, id_number: str, user) -> Optional[Dict[str, Any]]:
        """
        Search for a tenant by ID number.
        Returns masked data suitable for search results (privacy protection).
        """
        # 1. Find Tenant
        tenant = self.repository.find_by_id_number(id_number)

        if not tenant:
            return None

        # 2. Calculate Basic Reputation (Placeholder for Task 1.3)
        # We will enhance this in Task 1.3 with a dedicated Reputation Service
        reputation_summary = self._get_basic_reputation_summary(tenant)

        # 3. Construct Safe Response
        return {
            "id": str(tenant.id),
            "pkid": str(tenant.pkid),
            "full_name": tenant.user.get_full_name(),
            "email": tenant.user.email,
            "phone": (
                str(tenant.user.phone_number)
                if hasattr(tenant.user, "phone_number")
                else None
            ),
            "id_number_masked": self._mask_id_number(tenant.id_number),
            "current_status": self._get_tenant_status(tenant),
            "reputation": reputation_summary,
        }

    def _mask_id_number(self, id_number: str) -> str:
        """
        Mask ID number for privacy (e.g., CNI123456789 -> CNI***6789)
        """
        if len(id_number) <= 4:
            return "***"
        return f"{id_number[:-4]}***{id_number[-4:]}"

    def _get_tenant_status(self, tenant: Tenant) -> str:
        """
        Check if tenant currently has an active lease.
        """
        has_active_lease = Lease.objects.filter(
            lease_tenants__tenant=tenant, status="active"
        ).exists()
        return "occupied" if has_active_lease else "available"

    def _get_basic_reputation_summary(self, tenant: Tenant) -> Dict[str, Any]:
        """
        Basic reputation metrics.
        TODO: Move to dedicated ReputationService in Task 1.3
        """
        total_leases = Lease.objects.filter(lease_tenants__tenant=tenant).count()
        total_payments = Payment.objects.filter(tenant=tenant).count()
        completed_payments = Payment.objects.filter(
            tenant=tenant, status="completed"
        ).count()

        # Simple score calculation
        score = 50  # Neutral default
        if total_payments > 0:
            score = int((completed_payments / total_payments) * 100)

        return {
            "score": score,
            "total_leases": total_leases,
            "total_payments": total_payments,
            "completed_payments": completed_payments,
        }
