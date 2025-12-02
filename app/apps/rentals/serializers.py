from rest_framework import serializers
from django.utils.translation import gettext_lazy as _
from .models import (
    PaymentTerm,
    Owner,
    Manager,
    Tenant,
    Property,
    PropertyOwnership,
    Unit,
    Lease,
    LeaseTenant,
    Payment,
    Vendor,
    MaintenanceRequest,
    Expense,
    Document,
    # Notification,
)
from apps.users.models import User  # adjust import as needed
from django.contrib.contenttypes.models import ContentType

# ----------------------------------------------------------------------
# Helper serializers for nested relations (minimal representations)
# ----------------------------------------------------------------------


class UserMinimalSerializer(serializers.ModelSerializer):
    """Minimal user info for nested relations."""

    phone = serializers.CharField(source="profile.phone", read_only=True)

    class Meta:
        model = User
        fields = ["id", "email", "first_name", "last_name", "phone"]


class PaymentTermSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentTerm
        fields = ["id", "name", "interval_months", "description"]


class OwnerSerializer(serializers.ModelSerializer):
    user = UserMinimalSerializer(read_only=True)
    user_id = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(), source="user", write_only=True
    )

    class Meta:
        model = Owner
        fields = [
            "id",
            "user",
            "user_id",
            "preferred_payout_method",
            "mobile_money_number",
            "bank_account_name",
            "bank_name",
            "bank_account_number",
            "bank_code",
            "tax_id",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["created_at", "updated_at"]


class ManagerSerializer(serializers.ModelSerializer):
    user = UserMinimalSerializer(read_only=True)
    user_id = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(), source="user", write_only=True
    )
    managed_properties = serializers.PrimaryKeyRelatedField(
        many=True, read_only=True  # or use a nested representation if needed
    )

    class Meta:
        model = Manager
        fields = [
            "id",
            "user",
            "user_id",
            "commission_rate",
            "managed_properties",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["created_at", "updated_at"]


class TenantSerializer(serializers.ModelSerializer):
    user = UserMinimalSerializer(read_only=True)
    user_id = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(), source="user", write_only=True
    )

    class Meta:
        model = Tenant
        fields = [
            "id",
            "user",
            "user_id",
            "id_number",
            "id_document",
            "emergency_contact_name",
            "emergency_contact_phone",
            "emergency_contact_relation",
            "employer",
            "job_title",
            "monthly_income",
            "guarantor_name",
            "guarantor_phone",
            "guarantor_email",
            "guarantor_id_document",
            "notes",
            "language",  # added for bilingual support
            "emergency_contact_name_fr",
            "employer_fr",
            "job_title_fr",
            "notes_fr",
            "guarantor_name_fr",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["created_at", "updated_at"]


# ----------------------------------------------------------------------
# Property and related serializers
# ----------------------------------------------------------------------


class PropertyOwnershipSerializer(serializers.ModelSerializer):
    owner = OwnerSerializer(read_only=True)
    owner_id = serializers.PrimaryKeyRelatedField(
        queryset=Owner.objects.all(), source="owner", write_only=True
    )

    class Meta:
        model = PropertyOwnership
        fields = ["id", "owner", "owner_id", "percentage", "is_primary"]


class PropertySerializer(serializers.ModelSerializer):
    owners = PropertyOwnershipSerializer(
        source="ownership_records", many=True, read_only=True
    )
    managers = ManagerSerializer(many=True, read_only=True)
    manager_ids = serializers.PrimaryKeyRelatedField(
        many=True,
        queryset=Manager.objects.all(),
        source="managers",
        write_only=True,
        required=False,
    )
    units = serializers.PrimaryKeyRelatedField(
        many=True, read_only=True
    )  # or use UnitSerializer with depth

    class Meta:
        model = Property
        fields = [
            "id",
            "name",
            "property_type",
            "description",
            "language",
            "name_fr",
            "description_fr",
            "amenities",
            "amenities_fr",
            "address_line1",
            "address_line2",
            "city",
            "state",
            "country",
            "postal_code",
            "has_generator",
            "has_water_tank",
            "images",
            "owners",
            "managers",
            "manager_ids",
            "units",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["created_at", "updated_at"]

    def create(self, validated_data):
        managers = validated_data.pop("managers", [])
        property = super().create(validated_data)
        if managers:
            property.managers.set(managers)
        return property

    def update(self, instance, validated_data):
        managers = validated_data.pop("managers", None)
        property = super().update(instance, validated_data)
        if managers is not None:
            property.managers.set(managers)
        return property


# ----------------------------------------------------------------------
# Unit serializers
# ----------------------------------------------------------------------


class UnitSerializer(serializers.ModelSerializer):
    property_detail = PropertySerializer(source="property", read_only=True)
    property_id = serializers.PrimaryKeyRelatedField(
        queryset=Property.objects.all(), source="property", write_only=True
    )
    default_payment_term_detail = PaymentTermSerializer(
        source="default_payment_term", read_only=True
    )
    default_payment_term_id = serializers.PrimaryKeyRelatedField(
        queryset=PaymentTerm.objects.all(),
        source="default_payment_term",
        write_only=True,
        required=False,
        allow_null=True,
    )

    class Meta:
        model = Unit
        fields = [
            "id",
            "property",
            "property_detail",
            "property_id",
            "unit_number",
            "unit_type",
            "floor",
            "size_m2",
            "bedrooms",
            "bathrooms",
            "default_rent_amount",
            "default_payment_term",
            "default_payment_term_detail",
            "default_payment_term_id",
            "default_security_deposit",
            "status",
            "amenities",
            "amenities_fr",
            "images",
            "water_meter_number",
            "electricity_meter_number",
            "has_prepaid_meter",
            "custom_fields",
            "language",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["created_at", "updated_at"]


# ----------------------------------------------------------------------
# Lease serializers
# ----------------------------------------------------------------------


\class LeaseTenantSerializer(serializers.ModelSerializer):
    tenant = TenantSerializer(read_only=True)
    tenant_id = serializers.PrimaryKeyRelatedField(
        queryset=Tenant.objects.all(), source="tenant", write_only=True
    )

    class Meta:
        model = LeaseTenant
        fields = ["id", "tenant", "tenant_id", "is_primary", "signed_at"]


class LeaseSerializer(serializers.ModelSerializer):
    unit_detail = UnitSerializer(source="unit", read_only=True)
    unit_id = serializers.PrimaryKeyRelatedField(
        queryset=Unit.objects.all(), source="unit", write_only=True
    )   
    
    tenants = LeaseTenantSerializer(source="lease_tenants", many=True, read_only=True)
    tenant_ids = serializers.PrimaryKeyRelatedField(
        many=True, queryset=Tenant.objects.all(), write_only=True, required=False
    )
    payment_term_detail = PaymentTermSerializer(source="payment_term", read_only=True)
    payment_term_id = serializers.PrimaryKeyRelatedField(
        queryset=PaymentTerm.objects.all(), source="payment_term", write_only=True
    )

    class Meta:
        model = Lease
        fields = [
            "id",
            "unit",
            "unit_detail",
            "unit_id",
            "tenants",
            "tenant_ids",
            "start_date",
            "end_date",
            "payment_term",
            "payment_term_detail",
            "payment_term_id",
            "rent_amount",
            "due_day",
            "security_deposit",
            "deposit_paid",
            "late_fee_type",
            "late_fee_value",
            "utilities_included",
            "documents",
            "status",
            "termination_reason",
            "renewed_from",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["created_at", "updated_at"]

    def create(self, validated_data):
        tenant_ids = validated_data.pop("tenant_ids", [])
        lease = super().create(validated_data)
        if tenant_ids:
            # Create LeaseTenant entries for each tenant (default is_primary=False)
            for tenant in tenant_ids:
                LeaseTenant.objects.create(lease=lease, tenant=tenant)
        return lease

    def update(self, instance, validated_data):
        tenant_ids = validated_data.pop("tenant_ids", None)
        lease = super().update(instance, validated_data)
        if tenant_ids is not None:
            # Replace tenants: remove existing, add new ones
            instance.lease_tenants.all().delete()
            for tenant in tenant_ids:
                LeaseTenant.objects.create(lease=lease, tenant=tenant)
        return lease


# ----------------------------------------------------------------------
# Payment serializers
# ----------------------------------------------------------------------


class PaymentSerializer(serializers.ModelSerializer):
    lease_detail = LeaseSerializer(source="lease", read_only=True)
    lease_id = serializers.PrimaryKeyRelatedField(
        queryset=Lease.objects.all(), source="lease", write_only=True
    )
    tenant_detail = TenantSerializer(source="tenant", read_only=True)
    tenant_id = serializers.PrimaryKeyRelatedField(
        queryset=Tenant.objects.all(),
        source="tenant",
        write_only=True,
        required=False,
        allow_null=True,
    )

    class Meta:
        model = Payment
        fields = [
            "id",
            "lease",
            "lease_detail",
            "lease_id",
            "tenant",
            "tenant_detail",
            "tenant_id",
            "amount",
            "payment_date",
            "payment_method",
            "payment_type",
            "status",
            "period_start",
            "period_end",
            "transaction_id",
            "mobile_provider",
            "mobile_phone",
            "mobile_reference",
            "bank_name",
            "check_number",
            "notes",
            "gateway_response",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["created_at", "updated_at"]

    def validate(self, data):
        # Ensure period_start <= period_end
        if (
            data.get("period_start")
            and data.get("period_end")
            and data["period_start"] > data["period_end"]
        ):
            raise serializers.ValidationError("Period start must be before period end.")
        return data


# ----------------------------------------------------------------------
# Maintenance, Vendor, Expense serializers
# ----------------------------------------------------------------------


class VendorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Vendor
        fields = [
            "id",
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
            "photos",
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
        read_only_fields = ["created_at", "updated_at"]


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


# ----------------------------------------------------------------------
# Document and Notification serializers
# ----------------------------------------------------------------------


class DocumentSerializer(serializers.ModelSerializer):
    uploaded_by_detail = UserMinimalSerializer(source="uploaded_by", read_only=True)
    uploaded_by_id = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(),
        source="uploaded_by",
        write_only=True,
        required=False,
        allow_null=True,
    )
    # For generic relation, we need to accept content_type and object_id
    content_type = serializers.SlugRelatedField(
        slug_field="model", queryset=ContentType.objects.all()
    )
    object_id = serializers.UUIDField()

    class Meta:
        model = Document
        fields = [
            "id",
            "content_type",
            "object_id",
            "name",
            "file",
            "description",
            "uploaded_by",
            "uploaded_by_detail",
            "uploaded_by_id",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["created_at", "updated_at"]


# class NotificationSerializer(serializers.ModelSerializer):
#     recipient_detail = UserMinimalSerializer(source="recipient", read_only=True)
#     recipient_id = serializers.PrimaryKeyRelatedField(
#         queryset=User.objects.all(), source="recipient", write_only=True
#     )

#     class Meta:
#         model = Notification
#         fields = [
#             "id",
#             "recipient",
#             "recipient_detail",
#             "recipient_id",
#             "notification_type",
#             "subject",
#             "body",
#             "status",
#             "sent_at",
#             "provider_message_id",
#             "error_message",
#             "created_at",
#             "updated_at",
#         ]
#         read_only_fields = ["created_at", "updated_at"]
