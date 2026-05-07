from rest_framework import serializers
from django.utils.translation import gettext_lazy as _
from .models import Document
from apps.users.models import User  # adjust import as needed
from django.contrib.contenttypes.models import ContentType
from apps.users.api.serializers import UserMinimalSerializer

# ----------------------------------------------------------------------
# Document serializers
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
            "pkid",
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
