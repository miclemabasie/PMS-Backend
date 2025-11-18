from django.contrib import admin
from .models import (
    NotificationTemplate,
    Broadcast,
    Notification,
    UserNotificationSetting,
)


@admin.register(NotificationTemplate)
class NotificationTemplateAdmin(admin.ModelAdmin):
    list_display = ["name", "type", "is_active", "created_at"]
    list_filter = ["type", "is_active"]
    search_fields = ["name", "subject"]


@admin.register(Broadcast)
class BroadcastAdmin(admin.ModelAdmin):
    list_display = [
        "name",
        "template",
        "channel",
        "status",
        "total_recipients",
        "scheduled_at",
    ]
    list_filter = ["status", "channel", "created_at"]
    search_fields = ["name"]
    readonly_fields = [
        "total_recipients",
        "sent_count",
        "failed_count",
        "completed_at",
        "error_log",
    ]


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ["id", "user", "recipient", "channel", "status", "created_at"]
    list_filter = ["channel", "status", "created_at"]
    search_fields = ["user__email", "recipient"]
    readonly_fields = ["context", "error_message"]


@admin.register(UserNotificationSetting)
class UserNotificationSettingAdmin(admin.ModelAdmin):
    list_display = ["user", "email_enabled", "sms_enabled", "updated_at"]
    search_fields = ["user__email"]
