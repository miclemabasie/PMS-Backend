from typing import List, Optional
from django.db.models import QuerySet
from apps.core.base_repository import DjangoRepository
from apps.maintenance.models import MaintenanceRequest


class MaintenanceRequestRepository(DjangoRepository[MaintenanceRequest]):
    """Repository for MaintenanceRequest model."""

    def __init__(self):
        super().__init__(MaintenanceRequest)

    def get_by_id(self, request_id: str) -> Optional[MaintenanceRequest]:
        """Get a maintenance request by UUID."""
        try:
            return self.model_class.objects.get(id=request_id)
        except self.model_class.DoesNotExist:
            return None

    def get_queryset_for_user(self, user) -> QuerySet:
        """
        Return maintenance requests accessible to the user.
        
        Rules:
        - Superuser: all requests
        - Owner (landlord): requests for properties they own
        - Manager: requests for properties they manage
        - Tenant: only their own requests
        - Others: empty queryset
        """
        if user.is_superuser:
            return self.model_class.objects.all()

        # Owner (landlord)
        if hasattr(user, 'owner_profile'):
            return self.model_class.objects.filter(
                unit__property__ownership_records__owner=user.owner_profile
            ).distinct()

        # Manager
        if hasattr(user, 'manager_profile'):
            return self.model_class.objects.filter(
                unit__property__managers=user.manager_profile
            ).distinct()

        # Tenant
        if hasattr(user, 'tenant_profile'):
            return self.model_class.objects.filter(tenant=user.tenant_profile)

        return self.model_class.objects.none()

    def filter_by_status(self, queryset: QuerySet, status: str) -> QuerySet:
        """Filter queryset by status."""
        return queryset.filter(status=status)

    def filter_by_priority(self, queryset: QuerySet, priority: str) -> QuerySet:
        """Filter queryset by priority."""
        return queryset.filter(priority=priority)

    def filter_by_property(self, queryset: QuerySet, property_id: str) -> QuerySet:
        """Filter queryset by property ID."""
        return queryset.filter(unit__property__id=property_id)

    def count_pending_for_owner(self, owner_id) -> int:
        """Count pending maintenance requests for a property owner."""
        return self.model_class.objects.filter(
            unit__property__ownership_records__owner_id=owner_id
        ).exclude(status__in=['completed', 'cancelled']).count()