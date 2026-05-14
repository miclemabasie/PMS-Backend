from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from django.utils import timezone

from apps.maintenance.models import MaintenanceRequest, Vendor
from apps.maintenance.serializers import MaintenanceRequestSerializer, VendorSerializer
from apps.maintenance.services import MaintenanceService
from apps.properties.permissions import IsOwnerOrManagerOrSuperAdmin


class MaintenanceRequestViewSet(viewsets.ModelViewSet):
    serializer_class = MaintenanceRequestSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["title", "description", "unit__unit_number"]
    ordering_fields = ["created_at", "status", "priority"]
    ordering = ["-created_at"]

    def get_queryset(self):
        user = self.request.user
        qs = MaintenanceRequest.objects.select_related(
            "unit__property", "tenant", "assigned_vendor"
        )
        # Apply manual filtering from query params
        status_param = self.request.query_params.get("status")
        if status_param:
            qs = qs.filter(status=status_param)
        priority_param = self.request.query_params.get("priority")
        if priority_param:
            qs = qs.filter(priority=priority_param)
        property_param = self.request.query_params.get("property")
        if property_param:
            qs = qs.filter(unit__property__id=property_param)
        unit_param = self.request.query_params.get("unit")
        if unit_param:
            qs = qs.filter(unit__id=unit_param)

        if user.is_superuser:
            return qs
        if hasattr(user, "owner_profile"):
            return qs.filter(unit__property__owners=user.owner_profile)
        if hasattr(user, "manager_profile"):
            return qs.filter(unit__property__managers=user.manager_profile)
        if hasattr(user, "tenant_profile"):
            return qs.filter(tenant=user.tenant_profile)
        return qs.none()

    def perform_create(self, serializer):

        user = self.request.user
        tenant = getattr(user, "tenant_profile", None)
        if tenant:
            serializer.save(tenant=tenant)
        else:
            serializer.save()

    @action(detail=True, methods=["patch"])
    def assign_vendor(self, request, pk=None):
        req = self.get_object()
        vendor_id = request.data.get("vendor_id")
        if not vendor_id:
            return Response({"error": "vendor_id required"}, status=400)
        vendor = get_object_or_404(Vendor, pkid=vendor_id)
        req.assigned_vendor = vendor
        req.status = "assigned"
        req.save(update_fields=["assigned_vendor", "status"])
        return Response(MaintenanceRequestSerializer(req).data)

    @action(detail=True, methods=["patch"])
    def change_status(self, request, pk=None):
        req = self.get_object()
        new_status = request.data.get("status")
        allowed = ["submitted", "assigned", "in_progress", "completed", "cancelled"]
        if new_status not in allowed:
            return Response(
                {"error": f"Invalid status. Choose from {allowed}"}, status=400
            )
        req.status = new_status
        if new_status == "completed":
            req.completed_at = timezone.now()
        req.save()
        return Response(MaintenanceRequestSerializer(req).data)

    @action(
        detail=True, methods=["post"], permission_classes=[IsOwnerOrManagerOrSuperAdmin]
    )
    def approve(self, request, pk=None):
        service = MaintenanceService()
        try:
            req = service.approve_request(
                pk,
                (
                    request.user.manager_profile.id
                    if hasattr(request.user, "manager_profile")
                    else None
                ),
            )
            return Response(MaintenanceRequestSerializer(req).data)
        except ValueError as e:
            return Response({"error": str(e)}, status=400)

    @action(
        detail=True, methods=["post"], permission_classes=[IsOwnerOrManagerOrSuperAdmin]
    )
    def complete(self, request, pk=None):
        service = MaintenanceService()
        actual_cost = request.data.get("actual_cost")
        if not actual_cost:
            return Response({"error": "actual_cost required"}, status=400)
        try:
            expense = service.complete_request(
                pk, actual_cost, request.data.get("notes", "")
            )
            return Response(
                {
                    "expense_id": str(expense.id),
                    "message": "Request completed and expense recorded",
                }
            )
        except ValueError as e:
            return Response({"error": str(e)}, status=400)


class VendorViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Vendor.objects.filter(is_active=True)
    serializer_class = VendorSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter]
    search_fields = ["company_name", "contact_name", "specialties"]
