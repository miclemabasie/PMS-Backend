from rest_framework.permissions import BasePermission
from apps.rentals.models import Tenant


class IsOwnerOrManagerOrSuperAdmin(BasePermission):
    def has_object_permission(self, request, view, obj):
        user = request.user
        if user.is_superuser:
            return True
        # For Property objects
        if hasattr(obj, "ownership_records"):
            if (
                hasattr(user, "owner_profile")
                and obj.ownership_records.filter(owner=user.owner_profile).exists()
            ):
                return True
            if (
                hasattr(user, "manager_profile")
                and obj.managers.filter(id=user.manager_profile.id).exists()
            ):
                return True
        # For Unit objects
        if hasattr(obj, "property"):
            return self.has_object_permission(request, view, obj.property)
        # For Lease objects
        if hasattr(obj, "unit"):
            return self.has_object_permission(request, view, obj.unit)
        # For Tenant objects (only owner/manager of their lease?)
        # Simplified: only superadmin or the tenant themselves
        if isinstance(obj, Tenant):
            return user.role == "superadmin" or (
                hasattr(user, "tenant_profile") and user.tenant_profile.id == obj.id
            )
        # For Payment, MaintenanceRequest, etc., check through lease/unit
        if hasattr(obj, "lease"):
            return self.has_object_permission(request, view, obj.lease)
        if hasattr(obj, "unit"):
            return self.has_object_permission(request, view, obj.unit)
        return False


class IsTenantOrReadOnly(BasePermission):
    def has_object_permission(self, request, view, obj):
        if request.method in ["GET", "HEAD", "OPTIONS"]:
            return True
        return (
            hasattr(request.user, "tenant_profile")
            and obj.tenant == request.user.tenant_profile
        )


class CanManageProperty(BasePermission):
    def has_permission(self, request, view):
        user = request.user
        if user.is_superuser:
            return True
        return user.role in ["superadmin", "landlord", "propertymanager"]
