# apps/reports/views.py
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, viewsets
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from django.utils import timezone
from datetime import datetime, timedelta

from apps.properties.models import Property, Owner
from apps.properties.services import OwnerService
from apps.payments.models import Payment
from apps.properties.permissions import IsOwnerOrManagerOrSuperAdmin

from .services.financial_service import FinancialReportService
from .models import TemplateConfig, Expense
from .serializers import TemplateConfigSerializer, ExpenseSerializer
from .repositories import TemplateConfigRepository


# ------------------------------------------------------------
# Template Configuration Views
# ------------------------------------------------------------
class TemplateConfigViewSet(viewsets.ModelViewSet):
    """CRUD for landlord's template configurations."""

    permission_classes = [IsAuthenticated]
    serializer_class = TemplateConfigSerializer
    lookup_field = "pk"

    def get_queryset(self):
        # Only return templates owned by the current landlord
        owner_service = OwnerService()
        owner = owner_service.get_owner_for_user(self.request.user)
        if not owner:
            return TemplateConfig.objects.none()
        return TemplateConfig.objects.filter(landlord=owner)

    def perform_create(self, serializer):
        owner_service = OwnerService()
        owner = owner_service.get_or_create_for_user(self.request.user)
        serializer.save(landlord=owner)


# ------------------------------------------------------------
# Financial Reports
# ------------------------------------------------------------
class PropertyFinancialSummaryView(APIView):
    permission_classes = [IsAuthenticated, IsOwnerOrManagerOrSuperAdmin]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.service = FinancialReportService()

    def get(self, request, property_id):
        property_obj = get_object_or_404(Property, id=property_id)
        self.check_object_permissions(request, property_obj)

        start = request.query_params.get("start")
        end = request.query_params.get("end")
        group_by = request.query_params.get("group_by", "month")  # month or day

        if start:
            start_date = timezone.make_aware(datetime.strptime(start, "%Y-%m-%d"))
        else:
            start_date = None

        if end:
            end_date = timezone.make_aware(
                datetime.strptime(end, "%Y-%m-%d")
                + timedelta(days=1)
                - timedelta(seconds=1)
            )
        else:
            end_date = None

        data = self.service.get_property_summary(
            property_id, start_date, end_date, group_by
        )
        return Response(data)


class OwnerOverviewView(APIView):
    permission_classes = [IsAuthenticated]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.service = FinancialReportService()
        self.owner_service = OwnerService()

    def get(self, request):
        owner = self.owner_service.get_owner_for_user(request.user)
        if not owner:
            return Response({"detail": "No landlord profile associated"}, status=404)

        start = request.query_params.get("start")
        end = request.query_params.get("end")

        if start:
            start_date = timezone.make_aware(datetime.strptime(start, "%Y-%m-%d"))
        else:
            start_date = None

        if end:
            end_date = timezone.make_aware(
                datetime.strptime(end, "%Y-%m-%d")
                + timedelta(days=1)
                - timedelta(seconds=1)
            )
        else:
            end_date = None

        data = self.service.get_owner_overview(str(owner.pkid), start_date, end_date)
        return Response(data)


class ReceiptDataView(APIView):
    permission_classes = [IsAuthenticated]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.service = FinancialReportService()

    def get(self, request, payment_id):
        payment = get_object_or_404(Payment, id=payment_id)
        # Check permission: only user involved (tenant, landlord, manager) can view receipt
        user = request.user
        agreement = payment.agreement
        unit = agreement.unit
        property = unit.property
        is_tenant = (
            hasattr(user, "tenant_profile") and agreement.tenant == user.tenant_profile
        )
        is_owner = (
            hasattr(user, "owner_profile")
            and property.owners.filter(pkid=user.owner_profile.pkid).exists()
        )
        is_manager = (
            hasattr(user, "manager_profile")
            and property.managers.filter(pkid=user.manager_profile.pkid).exists()
        )
        if not (user.is_superuser or is_tenant or is_owner or is_manager):
            return Response({"detail": "Permission denied"}, status=403)

        data = self.service.get_receipt_data(str(payment.id))
        return Response(data)


class MaintenanceSummaryView(APIView):
    permission_classes = [IsAuthenticated, IsOwnerOrManagerOrSuperAdmin]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.service = FinancialReportService()

    def get(self, request, property_id):
        property_obj = get_object_or_404(Property, id=property_id)
        self.check_object_permissions(request, property_obj)

        start = request.query_params.get("start")
        end = request.query_params.get("end")

        start_date = datetime.fromisoformat(start) if start else None
        end_date = datetime.fromisoformat(end) if end else None

        data = self.service.get_maintenance_summary(property_id, start_date, end_date)
        return Response(data)


class ExpenseViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, IsOwnerOrManagerOrSuperAdmin]
    serializer_class = ExpenseSerializer

    def get_queryset(self):
        user = self.request.user
        if user.is_superuser:
            return Expense.objects.all()
        # For landlords/managers: filter by properties they own/manage
        if hasattr(user, "owner_profile"):
            return Expense.objects.filter(
                property__owners=user.owner_profile
            ).distinct()
        if hasattr(user, "manager_profile"):
            return Expense.objects.filter(
                property__managers=user.manager_profile
            ).distinct()
        return Expense.objects.none()


class MaintenanceAnalyticsView(APIView):
    """
    GET /api/v1/reports/maintenance/analytics/<property_id>/
    Returns detailed maintenance costs by vendor, priority, and monthly trend.
    """

    permission_classes = [IsAuthenticated, IsOwnerOrManagerOrSuperAdmin]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.service = FinancialReportService()

    def get(self, request, property_id):
        property_obj = get_object_or_404(Property, id=property_id)
        self.check_object_permissions(request, property_obj)

        start = request.query_params.get("start")
        end = request.query_params.get("end")
        start_date = datetime.fromisoformat(start) if start else None
        end_date = datetime.fromisoformat(end) if end else None

        data = self.service.get_maintenance_analytics(property_id, start_date, end_date)
        return Response(data)
