from rest_framework import serializers
from django.utils.translation import gettext_lazy as _

from apps.maintenance.models import MaintenanceRequest, Vendor
from apps.tenants.models import Tenant
from apps.users.models import User  # adjust import as needed
from django.contrib.contenttypes.models import ContentType
from apps.tenants.serializers import TenantSerializer
from apps.users.api.serializers import UserMinimalSerializer
from apps.properties.models import Manager, Unit
from apps.properties.serializers import (
    ManagerSerializer,
    UnitSerializer,
)


class VendorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Vendor
        fields = [
            "id",
            "pkid",
            "company_name",
            "contact_name",
            "phone",
            "email",
            "address",
            "specialties",
            "notes",
            "is_active",
            "language",
            "company_name_fr",
            "contact_name_fr",
            "address_fr",
            "specialties_fr",
            "notes_fr",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["created_at", "updated_at"]


class MaintenanceRequestSerializer(serializers.ModelSerializer):
    unit_detail = UnitSerializer(source="unit", read_only=True)
    unit_id = serializers.PrimaryKeyRelatedField(
        queryset=Unit.objects.all(), source="unit", write_only=True
    )
    tenant_detail = TenantSerializer(source="tenant", read_only=True)
    tenant_id = serializers.PrimaryKeyRelatedField(
        queryset=Tenant.objects.all(),
        source="tenant",
        write_only=True,
        required=False,
        allow_null=True,
    )
    requested_by_manager_detail = ManagerSerializer(
        source="requested_by_manager", read_only=True
    )
    requested_by_manager_id = serializers.PrimaryKeyRelatedField(
        queryset=Manager.objects.all(),
        source="requested_by_manager",
        write_only=True,
        required=False,
        allow_null=True,
    )
    assigned_vendor_detail = VendorSerializer(source="assigned_vendor", read_only=True)
    assigned_vendor_id = serializers.PrimaryKeyRelatedField(
        queryset=Vendor.objects.all(),
        source="assigned_vendor",
        write_only=True,
        required=False,
        allow_null=True,
    )
    approved_by_detail = ManagerSerializer(source="approved_by", read_only=True)
    approved_by_id = serializers.PrimaryKeyRelatedField(
        queryset=Manager.objects.all(),
        source="approved_by",
        write_only=True,
        required=False,
        allow_null=True,
    )

    class Meta:
        model = MaintenanceRequest
        fields = [
            "id",
            "pkid",
            "unit",
            "unit_detail",
            "unit_id",
            "tenant",
            "tenant_detail",
            "tenant_id",
            "requested_by_manager",
            "requested_by_manager_detail",
            "requested_by_manager_id",
            "title",
            "description",
            "priority",
            "status",
            # "photos",
            "assigned_vendor",
            "assigned_vendor_detail",
            "assigned_vendor_id",
            "estimated_cost",
            "actual_cost",
            "approved_by",
            "approved_by_detail",
            "approved_by_id",
            "approved_at",
            "completed_at",
            "notes",
            "language",
            "title_fr",
            "description_fr",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["created_at", "updated_at", "unit"]
