import uuid

from django.db import models
from django.utils.translation import gettext_lazy as _


class TimeStampedUUIDModel(models.Model):
    """
    Abstract base model providing:
    - Internal numeric primary key (performance-friendly)
    - Public UUID identifier (safe for APIs)
    - Creation & update timestamps
    """

    pkid = models.BigAutoField(
        primary_key=True,
        editable=False,
    )

    id = models.UUIDField(
        default=uuid.uuid4,
        editable=False,
        unique=True,
        db_index=True,  # Fast lookups for API usage
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        db_index=True,  # Useful for sorting & filtering
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        abstract = True
        ordering = ("-created_at",)  # Sensible default for most models

    def __str__(self):
        return str(self.id)


class Gender(models.TextChoices):
    """
    Enumerated gender choices.
    Stored values are stable and API-friendly.
    """

    MALE = "male", _("Male")
    FEMALE = "female", _("Female")
    OTHER = "other", _("Other")


class PaymentMethod(models.TextChoices):
    MTN_MOMO = "mtn_momo", _("MTN MoMo")
    ORANGE_MONEY = "orange_money", _("Orange Money")
    BANK_TRANSFER = "bank_transfer", _("Bank transfer")
    CASH = "cash", _("Cash")
    OTHER = "other", _("Other")


class PaymentType(models.TextChoices):
    RENT = "rent", _("Rent")
    DEPOSIT = "deposit", _("Security deposit")
    FEE = "fee", _("Fee / penalty")
    UTILITY = "utility", _("Utility bill")
    OTHER = "other", _("Other")


class PlatformSettings(models.Model):
    """Singleton model for global fee configuration."""

    platform_fee_percent = models.DecimalField(
        max_digits=5, decimal_places=2, default=1.0
    )
    platform_fee_cap = models.PositiveIntegerField(default=1000)
    gateway_fee_percent = models.DecimalField(
        max_digits=5, decimal_places=2, default=2.0
    )
    fixed_extra_fee = models.DecimalField(max_digits=10, decimal_places=0, default=0)

    # Which payment methods incur gateway fee? (global default)
    gateway_methods = models.JSONField(default=list, blank=True)

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Platform Settings"
        verbose_name_plural = "Platform Settings"

    def save(self, *args, **kwargs):
        # Ensure only one row
        if not self.pk and PlatformSettings.objects.exists():
            raise Exception("Only one PlatformSettings instance allowed")
        super().save(*args, **kwargs)

    @classmethod
    def get_settings(cls):
        obj, _ = cls.objects.get_or_create(
            defaults={
                "platform_fee_percent": 1.0,
                "platform_fee_cap": 1000,
                "gateway_fee_percent": 2.0,
                "fixed_extra_fee": 0,
                "gateway_methods": ["mtn_momo", "orange_money"],
            }
        )
        return obj
