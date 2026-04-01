from typing import List, Optional, Dict, Any
from django.db import transaction
from django.utils import timezone
import logging
import random  # ✅ For mock data
from .models import Tenant
from .repositories import TenantRepository
from apps.core.base_service import BaseService
from apps.rentals.models import Lease, Payment  # ✅ Imported for future use

logger = logging.getLogger(__name__)


class TenantService(BaseService[Tenant]):
    def __init__(self):
        super().__init__(TenantRepository())

    def get_tenants_for_property(self, property_id):
        logger.info("Get tenants for property with id %s", property_id)
        return self.repository.find_by_property(property_id)

    def search_tenant_by_id(self, id_number: str, user) -> Optional[Dict[str, Any]]:
        """
        Search for a tenant by ID number.
        RESPECTS: is_discoverable flag.
        """
        # 1. Find Tenant
        tenant = self.repository.find_by_id_number(id_number)

        if not tenant:
            return None

        # 2. ✅ Check Discovery Permission
        # If tenant is not discoverable AND user is not Admin, hide them
        if not tenant.is_discoverable and not user.is_superuser:
            # Log attempt for security auditing
            logger.warning(
                f"User {user.email} attempted to search non-discoverable tenant {tenant.id}"
            )
            return None

        # 3. Calculate Reputation (Mock for now)
        reputation_summary = ReputationService.get_mock_reputation(tenant)

        # 4. Construct Safe Response
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
            "is_discoverable": tenant.is_discoverable,  # ✅ Expose status
            "reputation": reputation_summary,
        }

    def _mask_id_number(self, id_number: str) -> str:
        if len(id_number) <= 4:
            return "***"
        return f"{id_number[:-4]}***{id_number[-4:]}"

    def _get_tenant_status(self, tenant: Tenant) -> str:
        has_active_lease = Lease.objects.filter(
            lease_tenants__tenant=tenant, status="active"
        ).exists()
        return "occupied" if has_active_lease else "available"

    @transaction.atomic
    def update_discovery_status(
        self, tenant_pkid: str, is_discoverable: bool
    ) -> Tenant:
        """
        Update tenant's discoverability status.
        Only called by the tenant themselves.
        """
        tenant = self.get_by_id(tenant_pkid)
        if not tenant:
            raise ValueError("Tenant not found")

        tenant.is_discoverable = is_discoverable
        tenant.save(update_fields=["is_discoverable", "updated_at"])

        logger.info(
            f"Tenant {tenant.pkid} updated discovery status to {is_discoverable}"
        )

        return tenant

    @transaction.atomic
    def admin_update_tenant_status(
        self, tenant_pkid: str, updates: Dict[str, Any]
    ) -> Tenant:
        """
        Admin can update is_discoverable and is_verified flags.
        Includes audit logging.
        """
        tenant = self.get_by_id(tenant_pkid)
        if not tenant:
            raise ValueError("Tenant not found")

        # Update fields
        if "is_discoverable" in updates:
            tenant.is_discoverable = updates["is_discoverable"]
        if "is_verified" in updates:
            tenant.is_verified = updates["is_verified"]

        tenant.save(update_fields=["is_discoverable", "is_verified", "updated_at"])

        logger.info(f"Admin updated tenant {tenant.pkid} status: {updates}")

        return tenant


# ✅ NEW: Dedicated Reputation Service
class ReputationService:
    """
    Handles tenant reputation calculation.
    CURRENTLY: Returns mock data for frontend development.
    FUTURE: Will calculate based on Payment & Lease history.
    """

    @staticmethod
    def get_mock_reputation(tenant: Tenant) -> Dict[str, Any]:
        """
        Returns a structured reputation object with mock data.
        Structure is designed to match future real implementation.
        """

        # ✅ Mock Logic: Generate consistent random data based on tenant ID
        # This ensures the same tenant gets the same mock score during testing
        seed = sum(ord(c) for c in str(tenant.pkid))
        random.seed(seed)

        score = random.randint(40, 100)
        total_leases = random.randint(0, 5)
        total_payments = total_leases * random.randint(1, 12)
        on_time_payments = int(total_payments * (score / 100))

        return {
            "score": score,
            "max_score": 100,
            "level": "Gold" if score > 80 else "Silver" if score > 60 else "Bronze",
            "total_leases": total_leases,
            "total_payments": total_payments,
            "on_time_payments": on_time_payments,
            "late_payments": total_payments - on_time_payments,
            "flags": {
                "has_eviction_history": False,  # Mock
                "has_lease_violations": False,  # Mock
                "is_verified": tenant.is_verified,
            },
            "last_updated": timezone.now().isoformat(),
            "is_mock": True,  # ✅ Flag for frontend debugging
        }

    @staticmethod
    def get_real_reputation(tenant: Tenant) -> Dict[str, Any]:
        """
        TODO: Implement this when Payment/Lease modules are live.
        """
        pass
