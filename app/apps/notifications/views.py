from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.contrib.auth import get_user_model
from django.utils import timezone

from .models import (
    NotificationTemplate,
    Broadcast,
    Notification,
    UserNotificationSetting,
    BroadcastStatus,
)
from .serializers import (
    NotificationTemplateSerializer,
    BroadcastSerializer,
    NotificationSerializer,
    UserNotificationSettingSerializer,
)
from .tasks import process_broadcast
from .utils import send_notification
from .choices import NotificationChannel

User = get_user_model()


class NotificationTemplateViewSet(viewsets.ModelViewSet):
    queryset = NotificationTemplate.objects.all()
    serializer_class = NotificationTemplateSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)


class BroadcastViewSet(viewsets.ModelViewSet):
    queryset = Broadcast.objects.all()
    serializer_class = BroadcastSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    @action(detail=True, methods=["post"])
    def send(self, request, pk=None):
        broadcast = self.get_object()
        if broadcast.status != BroadcastStatus.DRAFT:
            return Response(
                {"error": "Broadcast is not in draft state."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if broadcast.scheduled_at:
            broadcast.status = BroadcastStatus.SCHEDULED
            broadcast.save()
            # Schedule Celery task (use apply_async with eta)
            process_broadcast.apply_async(
                args=[str(broadcast.id)], eta=broadcast.scheduled_at
            )
        else:
            broadcast.status = BroadcastStatus.SCHEDULED
            broadcast.save()
            # Send immediately
            process_broadcast.delay(str(broadcast.id))
        return Response({"status": "scheduled"})


class NotificationViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Read‑only list/retrieve of sent notifications.
    Users can only see their own notifications.
    """

    serializer_class = NotificationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.is_staff:
            return Notification.objects.all()
        return Notification.objects.filter(user=user)


class UserNotificationSettingViewSet(
    viewsets.GenericViewSet,
    viewsets.mixins.RetrieveModelMixin,
    viewsets.mixins.UpdateModelMixin,
):
    """
    Retrieve and update the current user's notification settings.
    """

    serializer_class = UserNotificationSettingSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        obj, _ = UserNotificationSetting.objects.get_or_create(user=self.request.user)
        return obj

    def get_queryset(self):
        user = self.request.user
        if user.is_staff:
            return UserNotificationSetting.objects.all()
        return UserNotificationSetting.objects.filter(user=user)


from .models import EmailConfiguration
from .serializers import EmailConfigurationSerializer


class EmailConfigurationViewSet(viewsets.ModelViewSet):
    queryset = EmailConfiguration.objects.all()
    serializer_class = EmailConfigurationSerializer
    permission_classes = [permissions.IsAdminUser]  # only admins can manage
