from rest_framework import serializers
from django.contrib.auth import get_user_model

from .models import (
    NotificationTemplate,
    Broadcast,
    Notification,
    UserNotificationSetting,
    EmailConfiguration,
)

User = get_user_model()


class NotificationTemplateSerializer(serializers.ModelSerializer):
    class Meta:
        model = NotificationTemplate
        fields = [
            "id",
            "name",
            "description",
            "type",
            "subject",
            "template",
            "html_template",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class BroadcastSerializer(serializers.ModelSerializer):
    template_name = serializers.CharField(source="template.name", read_only=True)

    class Meta:
        model = Broadcast
        fields = [
            "id",
            "name",
            "template",
            "template_name",
            "channel",
            "recipient_filter",
            "scheduled_at",
            "status",
            "total_recipients",
            "sent_count",
            "failed_count",
            "created_at",
            "completed_at",
            "error_log",
        ]
        read_only_fields = [
            "id",
            "status",
            "total_recipients",
            "sent_count",
            "failed_count",
            "created_at",
            "completed_at",
            "error_log",
        ]

    def validate_recipient_filter(self, value):
        """Ensure the filter is a valid Django ORM filter dict."""
        if not isinstance(value, dict):
            raise serializers.ValidationError("Must be a JSON object.")
        # Optionally, test the filter against User model
        try:
            User.objects.filter(**value)[:1]
        except Exception as e:
            raise serializers.ValidationError(f"Invalid filter: {e}")
        return value


class NotificationSerializer(serializers.ModelSerializer):
    user_email = serializers.EmailField(source="user.email", read_only=True)

    class Meta:
        model = Notification
        fields = [
            "id",
            "user",
            "user_email",
            "recipient",
            "phone_number",
            "channel",
            "subject",
            "body",
            "status",
            "broadcast",
            "template",
            "error_message",
            "sent_at",
            "created_at",
        ]
        read_only_fields = [
            "id",
            "status",
            "error_message",
            "sent_at",
            "created_at",
        ]


class UserNotificationSettingSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserNotificationSetting
        fields = [
            "id",
            "email_enabled",
            "sms_enabled",
            "receive_marketing_emails",
            "receive_security_emails",
            "updated_at",
        ]
        read_only_fields = ["id", "updated_at"]


class EmailConfigurationSerializer(serializers.ModelSerializer):
    class Meta:
        model = EmailConfiguration
        fields = [
            "id",
            "name",
            "host",
            "port",
            "username",
            "password",
            "use_tls",
            "use_ssl",
            "from_email",
            "reply_to",
            "timeout",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]
        extra_kwargs = {"password": {"write_only": True}}
