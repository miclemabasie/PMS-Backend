# app/apps/tenants/serializers.py
from rest_framework import serializers
from django.utils.translation import gettext_lazy as _
from .models import Tenant
from apps.users.models import User
from apps.users.api.serializers import UserMinimalSerializer


# ============================================================
# ✅ MINIMAL SERIALIZER (No cross-app imports)
# ============================================================
class TenantMinimalSerializer(serializers.ModelSerializer):
    """
    Minimal tenant representation for use in other apps.
    """

    user = UserMinimalSerializer(read_only=True)

    class Meta:
        model = Tenant
        fields = [
            "id",
            "pkid",
            "user",
            "id_number",
            "is_discoverable",
            "is_verified",
        ]
        read_only_fields = ["id", "pkid"]


# ============================================================
# ✅ FULL TENANT SERIALIZER (Using RentalAgreement)
# ============================================================
class TenantSerializer(serializers.ModelSerializer):
    """
    Full tenant serializer with rental agreement information.
    """

    user = UserMinimalSerializer(read_only=True)
    user_id = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(), source="user", write_only=True
    )

    # Computed fields
    active_agreement_count = serializers.SerializerMethodField()
    total_agreements = serializers.SerializerMethodField()
    current_property = serializers.SerializerMethodField()
    reputation_score = serializers.SerializerMethodField()
    phone = serializers.CharField(source="user.profile.phone_number", read_only=True)

    class Meta:
        model = Tenant
        fields = [
            "id",
            "pkid",
            "user",
            "user_id",
            "id_number",
            "id_document",
            "id_document_front",
            "id_document_back",
            "emergency_contact_name",
            "emergency_contact_phone",
            "emergency_contact_relation",
            "employer",
            "job_title",
            "monthly_income",
            "guarantor_name",
            "guarantor_phone",
            "phone",
            "guarantor_email",
            "guarantor_id_document",
            "notes",
            "language",
            "emergency_contact_name_fr",
            "employer_fr",
            "job_title_fr",
            "notes_fr",
            "guarantor_name_fr",
            "is_discoverable",
            "is_verified",
            "active_agreement_count",
            "total_agreements",
            "current_property",
            "reputation_score",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["created_at", "updated_at"]

    # ============================================================
    # LAZY SERIALIZATION METHODS (using RentalAgreement)
    # ============================================================

    def get_active_agreement_count(self, obj):
        """Get count of active rental agreements."""
        from apps.payments.models import RentalAgreement

        return RentalAgreement.objects.filter(tenant=obj, is_active=True).count()

    def get_total_agreements(self, obj):
        """Get total rental agreement count."""
        from apps.payments.models import RentalAgreement

        return RentalAgreement.objects.filter(tenant=obj).count()

    def get_current_property(self, obj):
        """Get current property info from active rental agreement."""
        from apps.payments.models import RentalAgreement

        agreement = (
            RentalAgreement.objects.filter(tenant=obj, is_active=True)
            .select_related("unit__property")
            .first()
        )

        if agreement and agreement.unit and agreement.unit.property:
            return {
                "id": str(agreement.unit.property.id),
                "name": agreement.unit.property.name,
                "unit_number": agreement.unit.unit_number,
            }
        return None

    def get_reputation_score(self, obj):
        """Calculate reputation score from payment history."""
        from apps.payments.models import Payment

        total_payments = Payment.objects.filter(agreement__tenant=obj).count()
        completed_payments = Payment.objects.filter(
            agreement__tenant=obj, status="completed"
        ).count()

        if total_payments == 0:
            return 50

        return int((completed_payments / total_payments) * 100)

    def validate_id_number(self, value):
        """Validate ID number uniqueness."""
        normalized_value = value.strip().upper()
        queryset = Tenant.objects.filter(id_number=normalized_value)
        if self.instance:
            queryset = queryset.exclude(pk=self.instance.pk)

        if queryset.exists():
            raise serializers.ValidationError(
                _(
                    "This ID number (CNI/Passport) is already registered. "
                    "Each tenant can only have one account in the system."
                )
            )

        return normalized_value

    def create(self, validated_data):
        """Create tenant with normalized ID."""
        if "id_number" in validated_data:
            validated_data["id_number"] = validated_data["id_number"].strip().upper()
        return super().create(validated_data)

    def update(self, instance, validated_data):
        """Update tenant with normalized ID if changed."""
        if "id_number" in validated_data:
            validated_data["id_number"] = validated_data["id_number"].strip().upper()
        return super().update(instance, validated_data)


# ============================================================
# ✅ SEARCH RESULT SERIALIZER
# ============================================================
class TenantSearchResultSerializer(serializers.Serializer):
    """
    Serializer for tenant search results.
    Excludes sensitive data (guarantors, full ID, documents).
    """

    id = serializers.UUIDField()
    pkid = serializers.CharField()
    full_name = serializers.CharField()
    email = serializers.EmailField()
    phone = serializers.CharField(allow_null=True)
    id_number_masked = serializers.CharField()
    current_status = serializers.CharField()
    is_discoverable = serializers.BooleanField()
    is_verified = serializers.BooleanField()
    reputation = serializers.DictField()


# ============================================================
# ✅ TENANT DETAIL SERIALIZER (with nested data)
# ============================================================
class TenantDetailSerializer(serializers.Serializer):
    """
    Detailed tenant info with rental agreement and payment history.
    """

    tenant = serializers.SerializerMethodField()
    active_agreement = serializers.SerializerMethodField()
    agreement_history = serializers.SerializerMethodField()
    payment_history = serializers.SerializerMethodField()
    maintenance_requests = serializers.SerializerMethodField()

    def get_tenant(self, obj):
        return TenantSerializer(obj.get("tenant")).data

    def get_active_agreement(self, obj):
        from apps.payments.serializers import RentalAgreementSerializer

        agreement = obj.get("active_agreement")
        if not agreement:
            return None
        return RentalAgreementSerializer(agreement).data

    def get_agreement_history(self, obj):
        from apps.payments.serializers import RentalAgreementSerializer

        agreements = obj.get("agreement_history", [])
        return RentalAgreementSerializer(agreements, many=True).data

    def get_payment_history(self, obj):
        from apps.payments.serializers import PaymentSerializer

        payments = obj.get("payment_history", [])
        return PaymentSerializer(payments, many=True).data

    def get_maintenance_requests(self, obj):
        from apps.rentals.serializers import MaintenanceRequestSerializer

        requests = obj.get("maintenance_requests", [])
        return MaintenanceRequestSerializer(requests, many=True).data


# ============================================================
# ✅ ADMIN/DISCOVERY SERIALIZERS
# ============================================================
class TenantDiscoveryToggleSerializer(serializers.Serializer):
    """Serializer for tenant discovery toggle request."""

    is_discoverable = serializers.BooleanField(required=True)


class AdminTenantControlSerializer(serializers.Serializer):
    """Serializer for admin tenant control request."""

    is_discoverable = serializers.BooleanField(required=False, allow_null=True)
    is_verified = serializers.BooleanField(required=False, allow_null=True)

    def validate(self, data):
        if data.get("is_discoverable") is None and data.get("is_verified") is None:
            raise serializers.ValidationError(
                "At least one field (is_discoverable or is_verified) is required"
            )
        return data
