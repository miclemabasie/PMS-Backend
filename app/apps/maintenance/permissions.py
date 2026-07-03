from rest_framework.permissions import BasePermission


class CanManageMaintenanceRequest(BasePermission):
    """
    Custom permission for maintenance requests.
    
    - Tenant: can create, view own requests, update only if status is 'submitted'
    - Landlord/Manager: can view and update all requests for their properties
    - Superuser: everything
    """

    def has_permission(self, request, view):
        """View-level permission."""
        # Superuser has full access
        if request.user.is_superuser:
            return True

        # All authenticated users can list and retrieve
        if view.action in ['list', 'retrieve']:
            return request.user.is_authenticated

        # Create requires tenant, landlord, or manager
        if view.action == 'create':
            return (
                hasattr(request.user, 'tenant_profile') or
                hasattr(request.user, 'owner_profile') or
                hasattr(request.user, 'manager_profile')
            )

        # Status updates and completion require landlord/manager/superuser
        if view.action in ['update', 'partial_update', 'status', 'complete']:
            return (
                hasattr(request.user, 'owner_profile') or
                hasattr(request.user, 'manager_profile') or
                request.user.is_superuser
            )

        return False

    def has_object_permission(self, request, view, obj):
        """Object-level permission."""
        # Superuser has full access
        if request.user.is_superuser:
            return True

        # Tenant: can view their own, update only if status is 'submitted'
        if hasattr(request.user, 'tenant_profile'):
            if view.action == 'retrieve':
                return obj.tenant == request.user.tenant_profile
            if view.action in ['update', 'partial_update']:
                return obj.tenant == request.user.tenant_profile and obj.status == 'submitted'
            return False

        # Landlord: can manage if they own the property
        if hasattr(request.user, 'owner_profile'):
            return obj.unit.property.ownership_records.filter(
                owner=request.user.owner_profile
            ).exists()

        # Manager: can manage if they manage the property
        if hasattr(request.user, 'manager_profile'):
            return obj.unit.property.managers.filter(
                pkid=request.user.manager_profile.pkid
            ).exists()

        return False