from rest_framework import serializers
from django.utils.translation import gettext_lazy as _
from .models import (
    Tenant,
)
from apps.users.models import User  # adjust import as needed
from django.contrib.contenttypes.models import ContentType
from apps.users.api.serializers import UserMinimalSerializer


class TenantSerializer(serializers.ModelSerializer):
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
