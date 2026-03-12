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
from .serializers import TenantSerializer
from apps.core.utils import StandardResultsSetPagination

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
            print("there was a property id", property_id)
            tenants = self.service.get_tenants_for_property(property_id)
        else:
            print("there was no property id")
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
