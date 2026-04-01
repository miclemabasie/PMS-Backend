from django.shortcuts import render
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import status
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from .permissions import (
    IsOwnerOrManagerOrSuperAdmin,
    CanManageProperty,
    IsTenantOrReadOnly,
)

from .services import TenantService
from .serializers import TenantSerializer, TenantSearchResultSerializer
from apps.core.utils import StandardResultsSetPagination


from .services import TenantService
from .serializers import TenantSerializer, TenantSearchResultSerializer
from apps.core.utils import StandardResultsSetPagination
from apps.core.logging import CustomLogger

logger = CustomLogger(__name__)


# Create your views here.


# ----------------------------------------------------------------------
# Tenant Views
# ----------------------------------------------------------------------
class TenantListCreateView(APIView):
    permission_classes = [IsAuthenticated, CanManageProperty]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.service = TenantService()
        self.paginator = StandardResultsSetPagination()

    def get(self, request):
        # Filter by property if provided
        property_id = request.query_params.get("property")
        if property_id:
            # Get all tenants with leases in that property
            tenants = self.service.get_tenants_for_property(property_id)
        else:
            tenants = self.service.get_all()
        page = self.paginator.paginate_queryset(tenants, request)
        serializer = TenantSerializer(page, many=True)
        return self.paginator.get_paginated_response(serializer.data)

    def post(self, request):
        serializer = TenantSerializer(data=request.data)
        if serializer.is_valid():
            tenant = self.service.create(**serializer.validated_data)
            output = TenantSerializer(tenant)
            return Response(output.data, status=201)
        return Response(serializer.errors, status=400)


# ✅ NEW: Tenant Search View
class TenantSearchView(APIView):
    """
    Allows Landlords/Managers to search for tenants by National ID.
    Endpoint: GET /api/v1/tenants/search/?id_number=XXX
    """

    permission_classes = [IsAuthenticated, CanManageProperty]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.service = TenantService()

    def get(self, request):
        id_number = request.query_params.get("id_number")

        if not id_number:
            return Response(
                {"detail": "id_number query parameter is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Normalize ID number (uppercase, strip spaces) to match Task 1.1 logic
        normalized_id = id_number.strip().upper()

        # Search
        result = self.service.search_tenant_by_id(normalized_id, request.user)

        if not result:
            return Response(
                {"detail": "Tenant not found with this ID number"},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Serialize
        serializer = TenantSearchResultSerializer(result)
        return Response(serializer.data, status=status.HTTP_200_OK)


class TenantDetailView(APIView):
    permission_classes = [IsAuthenticated, IsOwnerOrManagerOrSuperAdmin]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.service = TenantService()

    def get(self, request, pk):
        tenant = self.service.get_by_id(pk)
        if not tenant:
            return Response({"detail": "Not found"}, status=404)
        self.check_object_permissions(request, tenant)
        serializer = TenantSerializer(tenant)
        return Response(serializer.data)

    def put(self, request, pk):
        tenant = self.service.get_by_id(pk)
        if not tenant:
            return Response({"detail": "Not found"}, status=404)
        self.check_object_permissions(request, tenant)
        serializer = TenantSerializer(tenant, data=request.data, partial=True)
        if serializer.is_valid():
            updated = self.service.update(pk, **serializer.validated_data)
            output = TenantSerializer(updated)
            return Response(output.data)
        return Response(serializer.errors, status=400)

    def delete(self, request, pk):
        tenant = self.service.get_by_id(pk)
        if not tenant:
            return Response({"detail": "Not found"}, status=404)
        self.check_object_permissions(request, tenant)
        # Only allow if no active lease
        if tenant.leases.filter(status="active").exists():
            return Response(
                {"detail": "Cannot delete tenant with active lease"}, status=400
            )
        self.service.delete(pk)
        return Response(status=204)


class TenantDiscoveryToggleView(APIView):
    """
    Allows tenants to toggle their own discoverability status.
    Endpoint: PATCH /api/v1/tenants/discovery-toggle/

    Tenants can only toggle their OWN status.
    """

    permission_classes = [IsAuthenticated]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.service = TenantService()

    def patch(self, request):
        # Get current user's tenant profile
        if not hasattr(request.user, "tenant_profile"):
            return Response(
                {"detail": "User does not have a tenant profile"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        tenant = request.user.tenant_profile
        is_discoverable = request.data.get("is_discoverable")

        if is_discoverable is None:
            return Response(
                {"detail": "is_discoverable field is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not isinstance(is_discoverable, bool):
            return Response(
                {"detail": "is_discoverable must be a boolean value"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Update tenant discoverability
        try:
            updated_tenant = self.service.update_discovery_status(
                tenant.id, is_discoverable
            )

            # Log the action
            # logger.action(
            #     action="tenant_discovery_toggled",
            #     actor=request.user.email,
            #     tenant_id=str(tenant.pkid),
            #     new_status=is_discoverable,
            # )

            return Response(
                {
                    "detail": "Discovery status updated successfully",
                    "is_discoverable": updated_tenant.is_discoverable,
                    "updated_at": updated_tenant.updated_at.isoformat(),
                },
                status=status.HTTP_200_OK,
            )

        except Exception as e:
            logger.error(
                "Failed to update discovery status",
                exc=e,
                tenant_id=str(tenant.pkid),
            )
            return Response(
                {"detail": "Failed to update discovery status"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class AdminTenantControlView(APIView):
    """
    Allows admins to control any tenant's discoverability and verification status.
    Endpoint: PATCH /api/v1/tenants/{id}/admin-control/

    Only superadmins can access this endpoint.
    """

    permission_classes = [IsAuthenticated]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.service = TenantService()

    def patch(self, request, pk):
        # Check if user is superadmin
        if not request.user.is_superuser:
            return Response(
                {"detail": "Only superadmins can access this endpoint"},
                status=status.HTTP_403_FORBIDDEN,
            )

        # Get tenant by pkid
        tenant = self.service.get_by_id(pk)
        if not tenant:
            return Response(
                {"detail": "Tenant not found"}, status=status.HTTP_404_NOT_FOUND
            )

        # Get update fields from request
        is_discoverable = request.data.get("is_discoverable")
        is_verified = request.data.get("is_verified")

        updates = {}
        if is_discoverable is not None:
            if not isinstance(is_discoverable, bool):
                return Response(
                    {"detail": "is_discoverable must be a boolean value"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            updates["is_discoverable"] = is_discoverable

        if is_verified is not None:
            if not isinstance(is_verified, bool):
                return Response(
                    {"detail": "is_verified must be a boolean value"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            updates["is_verified"] = is_verified

        if not updates:
            return Response(
                {
                    "detail": "At least one field (is_discoverable or is_verified) is required"
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Update tenant
        try:
            updated_tenant = self.service.admin_update_tenant_status(tenant.id, updates)

            # Log the action for audit
            # logger.action(
            #     action="admin_tenant_control",
            #     actor=request.user.email,
            #     tenant_id=str(tenant.pkid),
            #     tenant_email=tenant.user.email,
            #     updates=updates,
            # )

            return Response(
                {
                    "detail": "Tenant status updated successfully",
                    "tenant": {
                        "id": str(updated_tenant.pkid),
                        "email": updated_tenant.user.email,
                        "full_name": updated_tenant.user.get_full_name(),
                        "is_discoverable": updated_tenant.is_discoverable,
                        "is_verified": updated_tenant.is_verified,
                        "updated_at": updated_tenant.updated_at.isoformat(),
                    },
                },
                status=status.HTTP_200_OK,
            )

        except Exception as e:
            logger.error(
                "Admin tenant control failed",
                exc=e,
                tenant_id=str(tenant.pkid),
            )
            return Response(
                {"detail": "Failed to update tenant status"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    permission_classes = [IsAuthenticated, IsOwnerOrManagerOrSuperAdmin]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.service = TenantService()

    def get(self, request, pk):
        tenant = self.service.get_by_id(pk)
        if not tenant:
            return Response({"detail": "Not found"}, status=404)
        self.check_object_permissions(request, tenant)
        serializer = TenantSerializer(tenant)
        return Response(serializer.data)

    def put(self, request, pk):
        tenant = self.service.get_by_id(pk)
        if not tenant:
            return Response({"detail": "Not found"}, status=404)
        self.check_object_permissions(request, tenant)
        serializer = TenantSerializer(tenant, data=request.data, partial=True)
        if serializer.is_valid():
            updated = self.service.update(pk, **serializer.validated_data)
            output = TenantSerializer(updated)
            return Response(output.data)
        return Response(serializer.errors, status=400)

    def delete(self, request, pk):
        tenant = self.service.get_by_id(pk)
        if not tenant:
            return Response({"detail": "Not found"}, status=404)
        self.check_object_permissions(request, tenant)
        # Only allow if no active lease
        if tenant.leases.filter(status="active").exists():
            return Response(
                {"detail": "Cannot delete tenant with active lease"}, status=400
            )
        self.service.delete(pk)
        return Response(status=204)
