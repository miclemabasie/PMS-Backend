from rest_framework import serializers
from django.shortcuts import render
from .models import Property, Owner, PropertyOwnership, Manager, Unit
from apps.users.api.serializers import UserMinimalSerializer
from apps.users.models import User
from apps.rentals.serializers import PaymentSerializer, PaymentTermSerializer
from apps.rentals.models import PaymentTerm


class OwnerSerializer(serializers.ModelSerializer):
    user = UserMinimalSerializer(read_only=True)
    user_id = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(), source="user", write_only=True
    )

    class Meta:
        model = Owner
        fields = [
            "id",
            "pkid",
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
            "pkid",
            "user",
            "user_id",
            "commission_rate",
            "managed_properties",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["created_at", "updated_at"]


# Create your views here.
class PropertyOwnershipSerializer(serializers.ModelSerializer):
    owner = OwnerSerializer(read_only=True)
    owner_id = serializers.PrimaryKeyRelatedField(
        queryset=Owner.objects.all(), source="owner", write_only=True
    )

    class Meta:
        model = PropertyOwnership
        fields = ["id", "pkid", "owner", "owner_id", "percentage", "is_primary"]


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
            "pkid",
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
            "pkid",
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
