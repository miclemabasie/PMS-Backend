from django.db import models
from django.utils.translation import gettext_lazy as _


class NotificationChannel(models.TextChoices):
    EMAIL = "email", _("Email")
    SMS = "sms", _("SMS")
    # Push, Slack, etc. can be added later


class NotificationStatus(models.TextChoices):
    PENDING = "pending", _("Pending")
    SENT = "sent", _("Sent")
    FAILED = "failed", _("Failed")
    CANCELED = "canceled", _("Canceled")


class BroadcastStatus(models.TextChoices):
    DRAFT = "draft", _("Draft")
    SCHEDULED = "scheduled", _("Scheduled")
    SENDING = "sending", _("Sending")
    SENT = "sent", _("Sent")
    FAILED = "failed", _("Failed")
    CANCELED = "canceled", _("Canceled")


class TemplateType(models.TextChoices):
    EMAIL = "email", _("Email")
    SMS = "sms", _("SMS")
