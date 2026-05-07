from rest_framework import serializers
from django.utils.translation import gettext_lazy as _
from .models import Expense
from apps.users.models import User  # adjust import as needed
from django.contrib.contenttypes.models import ContentType
from apps.users.api.serializers import UserMinimalSerializer
from apps.properties.models import Property, Unit
from apps.properties.serializers import (
    PropertySerializer,
    UnitSerializer,
)
from apps.maintenance.models import Vendor
from apps.maintenance.serializers import VendorSerializer

# ----------------------------------------------------------------------
# Maintenance, Vendor, Expense serializers
# ----------------------------------------------------------------------


class ExpenseSerializer(serializers.ModelSerializer):
    property_detail = PropertySerializer(source="property", read_only=True)
    property_id = serializers.PrimaryKeyRelatedField(
        queryset=Property.objects.all(), source="property", write_only=True
    )
    unit_detail = UnitSerializer(source="unit", read_only=True)
    unit_id = serializers.PrimaryKeyRelatedField(
        queryset=Unit.objects.all(),
        source="unit",
        write_only=True,
        required=False,
        allow_null=True,
    )
    vendor_detail = VendorSerializer(source="vendor", read_only=True)
    vendor_id = serializers.PrimaryKeyRelatedField(
        queryset=Vendor.objects.all(),
        source="vendor",
        write_only=True,
        required=False,
        allow_null=True,
    )

    class Meta:
        model = Expense
        fields = [
            "id",
            "pkid",
            "property",
            "property_detail",
            "property_id",
            "unit",
            "unit_detail",
            "unit_id",
            "category",
            "amount",
            "expense_date",
            "description",
            "vendor",
            "vendor_detail",
            "vendor_id",
            "receipt",
            "is_reimbursable",
            "reimbursed",
            "language",
            "description_fr",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["created_at", "updated_at"]
