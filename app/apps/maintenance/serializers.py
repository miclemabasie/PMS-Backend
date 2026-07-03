from rest_framework import serializers
from django.utils.translation import gettext_lazy as _

from apps.maintenance.models import (
    MaintenanceRequest, 
    MaintenanceRequestImage, 
    Vendor,
    MaintenanceStatus
)
from apps.properties.models import Unit
from apps.tenants.models import Tenant
from apps.properties.serializers import UnitSerializer
from apps.tenants.serializers import TenantMinimalSerializer


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


class MaintenanceRequestImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = MaintenanceRequestImage
        fields = ['id', 'image', 'created_at']
        read_only_fields = ['id', 'created_at']


class MaintenanceRequestSerializer(serializers.ModelSerializer):
    unit_detail = UnitSerializer(source='unit', read_only=True)
    tenant_detail = TenantMinimalSerializer(source='tenant', read_only=True)
    images = MaintenanceRequestImageSerializer(many=True, read_only=True)

    class Meta:
        model = MaintenanceRequest
        fields = [
            'id', 'pkid', 'unit', 'unit_detail', 'tenant', 'tenant_detail',
            'title', 'description', 'priority', 'status',
            'assigned_vendor', 'estimated_cost', 'actual_cost',
            'approved_by', 'approved_at', 'completed_at', 'notes',
            'images', 'language', 'title_fr', 'description_fr',
            'created_at', 'updated_at', 'status',
        ]
        read_only_fields = [
            'id', 'pkid', 'tenant','approved_by',
            'approved_at', 'completed_at', 'created_at', 'updated_at'
        ]


class MaintenanceRequestCreateSerializer(serializers.ModelSerializer):
    images = serializers.ListField(
        child=serializers.ImageField(),
        required=False,
        max_length=5,
        write_only=True,
        help_text="Maximum 5 images"
    )
    unit_id = serializers.UUIDField(write_only=True, required=True)

    class Meta:
        model = MaintenanceRequest
        fields = [
            'unit_id', 'title', 'description', 'priority',
            'notes', 'images', 'language', 'title_fr', 'description_fr'
        ]

    def validate_unit_id(self, value):
        try:
            Unit.objects.get(id=value)
        except Unit.DoesNotExist:
            raise serializers.ValidationError("Unit does not exist")
        return value

    def validate_priority(self, value):
        valid_priorities = ['low', 'medium', 'high', 'emergency']
        if value not in valid_priorities:
            raise serializers.ValidationError(
                f"Priority must be one of: {', '.join(valid_priorities)}"
            )
        return value

    # We do NOT override create() – the view uses the service directly.
    # This serializer only validates input.


class MaintenanceRequestStatusSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=MaintenanceStatus.choices, required=True)

    def validate_status(self, value):
        if value not in dict(MaintenanceStatus.choices):
            raise serializers.ValidationError(f"Invalid status: {value}")
        return value