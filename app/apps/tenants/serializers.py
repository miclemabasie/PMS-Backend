from rest_framework import serializers
from django.utils.translation import gettext_lazy as _
from .models import (
    Tenant,
)
from apps.users.models import User  # adjust import as needed
from django.contrib.contenttypes.models import ContentType
from apps.users.api.serializers import UserMinimalSerializer


from rest_framework import serializers
from django.utils.translation import gettext_lazy as _
from .models import Tenant
from apps.users.models import User
from apps.users.api.serializers import UserMinimalSerializer


class TenantSerializer(serializers.ModelSerializer):
    """
    Serializer for Tenant model.

    Includes validation to provide user-friendly error messages
    when duplicate ID numbers are detected.
    """

    user = UserMinimalSerializer(read_only=True)
    user_id = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(), source="user", write_only=True
    )

    class Meta:
        model = Tenant
        fields = [
            "id",
            "pkid",
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
            "language",
            "emergency_contact_name_fr",
            "employer_fr",
            "job_title_fr",
            "notes_fr",
            "guarantor_name_fr",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["created_at", "updated_at"]

    def validate_id_number(self, value):
        """
        Validate that the ID number is not already in use.

        This provides a user-friendly error message before hitting
        the database constraint.
        """
        # Normalize the ID number (remove spaces, uppercase)
        normalized_value = value.strip().upper()

        # Check if this ID number already exists
        # Exclude current instance if updating
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
        """
        Create a new tenant with normalized ID number.
        """
        # Ensure ID number is normalized before saving
        if "id_number" in validated_data:
            validated_data["id_number"] = validated_data["id_number"].strip().upper()

        return super().create(validated_data)

    def update(self, instance, validated_data):
        """
        Update tenant with normalized ID number if changed.
        """
        if "id_number" in validated_data:
            validated_data["id_number"] = validated_data["id_number"].strip().upper()

        return super().update(instance, validated_data)


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
    reputation = serializers.DictField()
