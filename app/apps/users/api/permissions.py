from rest_framework import permissions


class IsOwnerOrAdmin(permissions.BasePermission):
    """
    Allow access only to the owner of the object or an admin user.
    """

    def has_object_permission(self, request, view, obj):
        if request.user.is_staff or request.user.is_superuser:
            return True
        if hasattr(obj, "user"):
            return obj.user == request.user
        return obj == request.user


class IsAdminOrReadOnly(permissions.BasePermission):
    """
    Allow read‑only access to everyone, write access only to admin users.
    """

    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        return request.user.is_staff
