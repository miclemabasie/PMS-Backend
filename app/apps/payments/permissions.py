# apps/agreements/permissions.py

from rest_framework.permissions import BasePermission


class IsLandlordOrManagerOrSuperAdminForUnit(BasePermission):
    """
    Allows only landlords (owners of the property), property managers, or superadmins
    to create a rental agreement for the given unit.
    """

    def has_permission(self, request, view):
        # For POST (create agreement), we need to check the unit_id from request data
        if request.method == "POST":
            unit_id = request.data.get("unit_id")
            if not unit_id:
                return False
            # We'll fetch the unit in the view, but for permission we can do it here
            # However, we don't have access to the unit object yet. So we'll handle in view.
            # Alternatively, defer to has_object_permission? But we don't have object yet.
        return True  # We'll do the actual check in the view by calling helper

    def has_object_permission(self, request, view, obj):
        # obj is a Unit when called from the view's check_object_permissions
        user = request.user
        if user.is_superuser:
            return True
        # Check if user is landlord (owner) of this unit's property
        if hasattr(user, "owner_profile"):
            return obj.property.owners.filter(pkid=user.owner_profile.pkid).exists()
        # Check if user is manager of this unit's property
        if hasattr(user, "manager_profile"):
            return obj.property.managers.filter(pkid=user.manager_profile.pkid).exists()
        return False


class CanManageRentalAgreement(BasePermission):
    """
    For viewing/paying/updating an existing rental agreement.
    - Superadmin: all
    - Landlord: if agreement's unit belongs to a property they own
    - Manager: if agreement's unit belongs to a property they manage
    - Tenant: only if the agreement's tenant is their own tenant profile
    """

    def has_object_permission(self, request, view, obj):
        user = request.user
        if user.is_superuser:
            return True
        # Tenant check
        if hasattr(user, "tenant_profile"):
            return obj.tenant == user.tenant_profile
        # Landlord check
        if hasattr(user, "owner_profile"):
            return obj.unit.property.owners.filter(
                pkid=user.owner_profile.pkid
            ).exists()
        # Manager check
        if hasattr(user, "manager_profile"):
            return obj.unit.property.managers.filter(
                pkid=user.manager_profile.pkid
            ).exists()
        return False


class CanListPayments(BasePermission):
    """
    For listing payments: only users who can see the agreement (same logic as above).
    We'll use the same object check but we need to pass the agreement.
    """

    def has_permission(self, request, view):
        # We'll manually check the agreement in the view
        return True

    def has_object_permission(self, request, view, obj):
        # obj here is the RentalAgreement
        return CanManageRentalAgreement().has_object_permission(request, view, obj)


# apps/agreements/permissions.py


def user_can_manage_agreement(user, agreement) -> bool:
    if user.is_superuser:
        return True
    if hasattr(user, "tenant_profile"):
        return agreement.tenant == user.tenant_profile
    if hasattr(user, "owner_profile"):
        return agreement.unit.property.owners.filter(
            pkid=user.owner_profile.pkid
        ).exists()
    if hasattr(user, "manager_profile"):
        return agreement.unit.property.managers.filter(
            pkid=user.manager_profile.pkid
        ).exists()
    return False
