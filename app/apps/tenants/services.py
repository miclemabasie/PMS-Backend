from typing import List, Optional, Dict, Any
from django.db import transaction
from django.utils import timezone
import logging
import random
from .models import Tenant
from .repositories import TenantRepository
from apps.core.base_service import BaseService
from apps.rentals.models import Lease, Payment
from apps.properties.models import Property, PropertyOwnership

logger = logging.getLogger(__name__)


class TenantService(BaseService[Tenant]):
    def __init__(self):
        super().__init__(TenantRepository())

    def get_tenants_for_property(self, property_id):
        logger.info("Get tenants for property with id %s", property_id)
        return self.repository.find_by_property(property_id)

    def get_tenants_for_landlord(self, user):
        """
        Get all tenants associated with a landlord's properties.

        Rules:
        - Superuser: all tenants
        - Landlord: tenants from properties they own
        - Manager: tenants from properties they manage
        """
        if user.is_superuser:
            return self.get_all()

        # Landlord - get tenants from owned properties
        if hasattr(user, "owner_profile"):
            owned_property_ids = Property.objects.filter(
                ownership_records__owner=user.owner_profile
            ).values_list("id", flat=True)

            return Tenant.objects.filter(
                leases__unit__property__id__in=owned_property_ids
            ).distinct()

        # Manager - get tenants from managed properties
        if hasattr(user, "manager_profile"):
            managed_property_ids = Property.objects.filter(
                managers=user.manager_profile
            ).values_list("id", flat=True)

            return Tenant.objects.filter(
                leases__unit__property__id__in=managed_property_ids
            ).distinct()

        # Tenant or other - return empty
        return Tenant.objects.none()

    def get_tenant_details(self, tenant_id, user):
        """
        Get detailed tenant information including lease history and payments.
        Includes permission check to ensure user can view this tenant.
        """
        tenant = self.get_by_id(tenant_id)
        if not tenant:
            return None

        # Permission check
        if not user.is_superuser:
            if hasattr(user, "owner_profile"):
                # Check if tenant is in landlord's properties
                has_access = Lease.objects.filter(
                    lease_tenants__tenant=tenant,
                    unit__property__ownership_records__owner=user.owner_profile,
                ).exists()
                if not has_access:
                    return None
            elif hasattr(user, "manager_profile"):
                # Check if tenant is in managed properties
                has_access = Lease.objects.filter(
                    lease_tenants__tenant=tenant,
                    unit__property__managers=user.manager_profile,
                ).exists()
                if not has_access:
                    return None
            else:
                # Tenant can only view themselves
                if hasattr(user, "tenant_profile"):
                    if user.tenant_profile.id != tenant.id:
                        return None
                else:
                    return None

        # Build detailed response
        return {
            "tenant": tenant,
            "active_lease": self._get_active_lease(tenant),
            "lease_history": self._get_lease_history(tenant),
            "payment_history": self._get_payment_history(tenant),
            "maintenance_requests": self._get_maintenance_requests(tenant),
        }

    def _get_active_lease(self, tenant):
        """Get tenant's current active lease"""
        from apps.rentals.models import LeaseTenant

        lease_tenant = (
            LeaseTenant.objects.filter(tenant=tenant, lease__status="active")
            .select_related("lease__unit__property", "lease__payment_term")
            .first()
        )

        if lease_tenant:
            return lease_tenant.lease
        return None

    def _get_lease_history(self, tenant):
        """Get all leases for this tenant"""
        from apps.rentals.models import LeaseTenant

        lease_tenants = (
            LeaseTenant.objects.filter(tenant=tenant)
            .select_related("lease__unit__property", "lease__payment_term")
            .order_by("-lease__created_at")
        )

        return [lt.lease for lt in lease_tenants]

    def _get_payment_history(self, tenant):
        """Get all payments made by this tenant"""
        return (
            Payment.objects.filter(tenant=tenant)
            .select_related("lease")
            .order_by("-payment_date")[:20]
        )  # Last 20 payments

    def _get_maintenance_requests(self, tenant):
        """Get maintenance requests submitted by this tenant"""
        from apps.rentals.models import MaintenanceRequest

        return MaintenanceRequest.objects.filter(tenant=tenant).order_by("-created_at")[
            :10
        ]  # Last 10 requests

    def search_tenant_by_id(self, id_number: str, user) -> Optional[Dict[str, Any]]:
        """
        Search for a tenant by ID number.
        RESPECTS: is_discoverable flag.
        """
        tenant = self.repository.find_by_id_number(id_number)

        if not tenant:
            return None

        if not tenant.is_discoverable and not user.is_superuser:
            logger.warning(
                f"User {user.email} attempted to search non-discoverable tenant {tenant.id}"
            )
            return None

        reputation_summary = self._get_reputation_summary(tenant)

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
            "is_discoverable": tenant.is_discoverable,
            "is_verified": tenant.is_verified,
            "reputation": reputation_summary,
        }

    def _get_reputation_summary(self, tenant: Tenant) -> Dict[str, Any]:
        """Calculate tenant reputation based on payment history"""
        total_leases = Lease.objects.filter(lease_tenants__tenant=tenant).count()
        total_payments = Payment.objects.filter(tenant=tenant).count()
        completed_payments = Payment.objects.filter(
            tenant=tenant, status="completed"
        ).count()

        score = 50
        if total_payments > 0:
            score = int((completed_payments / total_payments) * 100)

        has_eviction = Lease.objects.filter(
            lease_tenants__tenant=tenant,
            status="terminated",
            termination_reason__icontains="eviction",
        ).exists()

        return {
            "score": score,
            "max_score": 100,
            "level": "Gold" if score > 80 else "Silver" if score > 60 else "Bronze",
            "total_leases": total_leases,
            "total_payments": total_payments,
            "completed_payments": completed_payments,
            "late_payments": total_payments - completed_payments,
            "flags": {
                "has_eviction_history": has_eviction,
                "has_lease_violations": False,
                "is_verified": tenant.is_verified,
            },
            "last_updated": timezone.now().isoformat(),
            "is_mock": False,
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
        tenant = self.get_by_id(tenant_pkid)
        if not tenant:
            raise ValueError("Tenant not found")

        if "is_discoverable" in updates:
            tenant.is_discoverable = updates["is_discoverable"]
        if "is_verified" in updates:
            tenant.is_verified = updates["is_verified"]

        tenant.save(update_fields=["is_discoverable", "is_verified", "updated_at"])

        logger.info(f"Admin updated tenant {tenant.pkid} status: {updates}")
        return tenant
