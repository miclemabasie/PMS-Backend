import uuid
from django.conf import settings
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.core.validators import validate_email
from django.core.exceptions import ValidationError

from .choices import (
    NotificationChannel,
    NotificationStatus,
    BroadcastStatus,
    TemplateType,
)


class NotificationTemplate(models.Model):
    """
    Reusable email/SMS template.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(_("Name"), max_length=255, unique=True)
    description = models.TextField(_("Description"), blank=True)
    type = models.CharField(
        _("Type"),
        max_length=10,
        choices=TemplateType.choices,
        default=TemplateType.EMAIL,
    )
    subject = models.CharField(
        _("Subject"), max_length=255, blank=True
    )  # used for email
    template = models.TextField(_("Template"))
    html_template = models.TextField(
        _("HTML Template"), blank=True
    )  # optional for email
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_templates",
    )
    is_active = models.BooleanField(_("Active"), default=True)

    class Meta:
        verbose_name = _("Notification Template")
        verbose_name_plural = _("Notification Templates")
        ordering = ["-created_at"]

    def __str__(self):
        return self.name


class Broadcast(models.Model):
    """
    A broadcast sends a template to a list of recipients.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(_("Broadcast name"), max_length=255)
    template = models.ForeignKey(
        NotificationTemplate,
        on_delete=models.PROTECT,
        related_name="broadcasts",
    )
    channel = models.CharField(
        _("Channel"),
        max_length=10,
        choices=NotificationChannel.choices,
        default=NotificationChannel.EMAIL,
    )
    recipient_filter = models.JSONField(
        _("Recipient filter"),
        default=dict,
        help_text=_("Query filters to select users (e.g., {'is_active': True})"),
    )
    scheduled_at = models.DateTimeField(_("Scheduled at"), null=True, blank=True)
    status = models.CharField(
        _("Status"),
        max_length=20,
        choices=BroadcastStatus.choices,
        default=BroadcastStatus.DRAFT,
    )
    total_recipients = models.PositiveIntegerField(default=0)
    sent_count = models.PositiveIntegerField(default=0)
    failed_count = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="broadcasts_created",
    )
    completed_at = models.DateTimeField(null=True, blank=True)
    error_log = models.TextField(blank=True)

    class Meta:
        verbose_name = _("Broadcast")
        verbose_name_plural = _("Broadcasts")
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.name} ({self.get_status_display()})"


class Notification(models.Model):
    """
    Log of a single notification sent to a user.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="notifications",
    )
    recipient = models.EmailField(_("Recipient email"), blank=True)
    phone_number = models.CharField(_("Phone number"), max_length=30, blank=True)
    channel = models.CharField(
        _("Channel"),
        max_length=10,
        choices=NotificationChannel.choices,
    )
    subject = models.CharField(_("Subject"), max_length=255, blank=True)
    body = models.TextField(_("Body"))
    status = models.CharField(
        _("Status"),
        max_length=20,
        choices=NotificationStatus.choices,
        default=NotificationStatus.PENDING,
    )
    broadcast = models.ForeignKey(
        Broadcast,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="notifications",
    )
    template = models.ForeignKey(
        NotificationTemplate,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="sent_notifications",
    )
    context = models.JSONField(_("Context"), default=dict, blank=True)
    error_message = models.TextField(_("Error message"), blank=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _("Notification")
        verbose_name_plural = _("Notifications")
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status"]),
            models.Index(fields=["user", "-created_at"]),
        ]

    def __str__(self):
        return f"{self.channel} to {self.recipient or self.user} - {self.status}"


class UserNotificationSetting(models.Model):
    """
    Per‑user preferences for each notification channel/type.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notification_settings",
    )
    email_enabled = models.BooleanField(_("Email notifications"), default=True)
    sms_enabled = models.BooleanField(_("SMS notifications"), default=False)
    # You can extend with specific types (e.g., marketing, security)
    receive_marketing_emails = models.BooleanField(_("Marketing emails"), default=False)
    receive_security_emails = models.BooleanField(_("Security emails"), default=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("User Notification Setting")
        verbose_name_plural = _("User Notification Settings")

    def __str__(self):
        return f"Settings for {self.user.email}"


class EmailConfiguration(models.Model):
    """
    Stores SMTP settings for sending emails.
    Only one configuration can be active at a time.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255, help_text="e.g., SendGrid, Gmail, etc.")
    host = models.CharField(max_length=255)
    port = models.PositiveIntegerField(default=587)
    username = models.CharField(max_length=255, blank=True)
    password = models.CharField(max_length=255, blank=True)
    use_tls = models.BooleanField(default=True)
    use_ssl = models.BooleanField(default=False)
    from_email = models.EmailField(help_text="Default from email address")
    reply_to = models.EmailField(blank=True, null=True)
    timeout = models.PositiveIntegerField(default=30)
    is_active = models.BooleanField(
        default=False, help_text="Only one config can be active at a time"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Email Configuration"
        verbose_name_plural = "Email Configurations"
        ordering = ["-is_active", "-created_at"]

    def save(self, *args, **kwargs):
        # Ensure only one active config
        if self.is_active:
            EmailConfiguration.objects.filter(is_active=True).exclude(
                pk=self.pk
            ).update(is_active=False)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name} ({'active' if self.is_active else 'inactive'})"

    @classmethod
    def get_active(cls):
        return cls.objects.filter(is_active=True).first()
