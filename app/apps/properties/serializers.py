from rest_framework import serializers
from django.shortcuts import render
from .models import (
    Property,
    Owner,
    PropertyImage,
    UnitImage,
    PropertyOwnership,
    Manager,
    Unit,
)
from apps.users.api.serializers import UserMinimalSerializer
from apps.users.models import User
from .utils import calculatate_occupancy_rate
from apps.payments.models import PaymentPlan


class PropertyImageSerializer(serializers.ModelSerializer):
    image_url = serializers.SerializerMethodField()

    class Meta:
        model = PropertyImage
        fields = ["id", "image", "image_url", "property", "alt_text", "is_primary"]
        read_only_fields = ["id", "property"]

    def get_image_url(self, obj):
        return obj.get_property_image_url()


class UnitImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = UnitImage
        fields = ["id", "image", "unit", "alt_text", "is_primary"]
        read_only_fields = ["id", "unit"]


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


# ----------------------------------------------------------------------
# Unit serializers
# ----------------------------------------------------------------------


class UnitSerializer(serializers.ModelSerializer):
    property_detail = serializers.SerializerMethodField()
    property_id = serializers.PrimaryKeyRelatedField(
        queryset=Property.objects.all(), source="property", write_only=True
    )
    default_payment_plan = serializers.PrimaryKeyRelatedField(
        queryset=PaymentPlan.objects.all(),
        required=False,
        allow_null=True,
        help_text="Payment plan for this unit",
    )
    unit_images = UnitImageSerializer(many=True, read_only=True)
    images = serializers.ListField(
        child=serializers.ImageField(),
        write_only=True,
        required=False,
        help_text="List of images to upload with the unit",
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
            "default_payment_plan",  # add this line
            "default_security_deposit",
            "status",
            "amenities",
            "amenities_fr",
            "unit_images",
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
    units = UnitSerializer(many=True, read_only=True)

    occupancy_rate = serializers.SerializerMethodField()
    lower_bound = serializers.SerializerMethodField(read_only=True)
    upper_bound = serializers.SerializerMethodField()
    property_images = PropertyImageSerializer(many=True, read_only=True)
    images = serializers.ListField(
        child=serializers.ImageField(),
        write_only=True,
        required=False,
        help_text="List of images to upload with the property",
    )

    primary_image = serializers.SerializerMethodField(read_only=True)

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
            "property_images",
            "postal_code",
            "has_generator",
            "has_water_tank",
            "primary_image",
            "images",
            "owners",
            "managers",
            "manager_ids",
            "units",
            "status",
            "starting_amount",
            "top_amount",
            "occupancy_rate",
            "lower_bound",
            "upper_bound",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["created_at", "updated_at"]

    def get_occupancy_rate(self, obj):
        # return calculatate_occupancy_rate(obj.id)
        return 70

    def get_lower_bound(self, obj):
        # convert figure to represent 1k fo 1000
        price = obj.starting_amount / 1000
        return f"{int(price)}k"

    def get_upper_bound(self, obj):
        price = obj.top_amount / 1000
        # remove the .00 from the price
        return f"{int(price)}k"

    def get_primary_image(self, obj):
        return obj.get_primary_image()

    def get_units(self, obj):
        return obj.units


class PropertyManagerAssignmentSerializer(serializers.Serializer):
    """
    Serializer for adding/removing managers to a property.
    """

    manager_ids = serializers.ListField(
        child=serializers.IntegerField(),
        write_only=True,
        required=True,
        help_text="List of manager UUIDs to assign",
    )

    def validate_manager_ids(self, value):
        """Validate that all manager IDs exist."""
        existing_managers = Manager.objects.filter(pkid__in=value)
        if len(existing_managers) != len(value):
            missing = set(value) - set(existing_managers.values_list("pkid", flat=True))
            raise serializers.ValidationError(
                f"Manager(s) with IDs {missing} not found"
            )
        return value


class PropertyManagerListSerializer(serializers.ModelSerializer):
    """
    Serializer for listing managers assigned to a property.
    """

    user = UserMinimalSerializer(read_only=True)
    commission_rate = serializers.DecimalField(max_digits=5, decimal_places=2)

    class Meta:
        model = Manager
        fields = [
            "id",
            "pkid",
            "user",
            "commission_rate",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["created_at", "updated_at"]


class PropertyManagerAddSerializer(serializers.Serializer):
    """
    Serializer for adding a single manager to a property.
    """

    manager_id = serializers.IntegerField(required=True, help_text="PKID Field")

    def validate_manager_id(self, value):
        """Validate that the manager exists."""
        try:
            manager = Manager.objects.get(pkid=value)
            return manager
        except Manager.DoesNotExist:
            raise serializers.ValidationError(f"Manager with ID {value} not found")


class PropertyManagerRemoveSerializer(serializers.Serializer):
    """
    Serializer for removing a single manager from a property.
    """

    manager_id = serializers.UUIDField(
        required=True, help_text="UUID of the manager to remove"
    )
