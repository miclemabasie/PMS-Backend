from rest_framework import serializers
from django.utils.translation import gettext_lazy as _
from apps.rentals.models import (
    PaymentTerm,
    Lease,
    LeaseTenant,
    Payment,
)
from apps.tenants.models import Tenant
from apps.users.models import User  # adjust import as needed
from django.contrib.contenttypes.models import ContentType
from apps.tenants.serializers import TenantSerializer


# ----------------------------------------------------------------------
# Helper serializers for nested relations (minimal representations)
# ----------------------------------------------------------------------


class PaymentTermSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentTerm
        fields = ["id", "name", "interval_months", "description"]


class LeaseTenantSerializer(serializers.ModelSerializer):
    tenant = TenantSerializer(read_only=True)
    tenant_id = serializers.PrimaryKeyRelatedField(
        queryset=Tenant.objects.all(), source="tenant", write_only=True
    )

    class Meta:
        model = LeaseTenant
        fields = ["id", "pkid", "tenant", "tenant_id", "is_primary", "signed_at"]


class LeaseSerializer(serializers.ModelSerializer):
    # unit_detail = UnitSerializer(source="unit", read_only=True)
    # unit_id = serializers.PrimaryKeyRelatedField(
    #     queryset=Unit.objects.all(), source="unit", write_only=True
    # )
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
            "pkid",
            # "unit_detail",
            # "unit_id",
            "tenants",
            "tenant_ids",
            "start_date",
            "end_date",
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
        read_only_fields = [
            "created_at",
            "updated_at",
            "status",
        ]  # status is set automatically

    def create(self, validated_data):
        tenant_ids = validated_data.pop("tenant_ids", [])
        lease = super().create(validated_data)
        for tenant in tenant_ids:
            LeaseTenant.objects.create(lease=lease, tenant=tenant)
        return lease

    def update(self, instance, validated_data):
        tenant_ids = validated_data.pop("tenant_ids", None)
        lease = super().update(instance, validated_data)
        if tenant_ids is not None:
            # instance.lease_tenants.all().delete()
            # for tenant in tenant_ids:
            #     LeaseTenant.objects.create(lease=lease, tenant=tenant)
            # Get current tenant IDs
            current_tenant_ids = set(
                instance.lease_tenants.values_list("tenant_id", flat=True)
            )
            new_tenant_ids = set(t.id for t in tenant_ids)

            # Remove tenants no longer in the list
            instance.lease_tenants.filter(
                tenant_id__in=current_tenant_ids - new_tenant_ids
            ).delete()

            # Add new tenants
            for tenant in tenant_ids:
                if tenant.id not in current_tenant_ids:
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
            "pkid",
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
