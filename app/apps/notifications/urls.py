from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    NotificationTemplateViewSet,
    BroadcastViewSet,
    NotificationViewSet,
    UserNotificationSettingViewSet,
    EmailConfigurationViewSet,
)

app_name = "notifications"

router = DefaultRouter()
router.register(
    r"notifications/templates", NotificationTemplateViewSet, basename="template"
)
router.register(
    r"notifications/settings", UserNotificationSettingViewSet, basename="settings"
)
router.register(r"notifications/broadcasts", BroadcastViewSet, basename="broadcast")
router.register(
    r"notifications/notifications", NotificationViewSet, basename="notification"
)

router.register(
    r"notifications/email-configs", EmailConfigurationViewSet, basename="emailconfig"
)

urlpatterns = [
    path("", include(router.urls)),
]
