# apps/subscriptions/models.py

from django.db import models
from django.utils.translation import gettext_lazy as _
from apps.core.models import TimeStampedUUIDModel


class BaseSubscriptionFeatureGroup(TimeStampedUUIDModel):
    """
    A reusable set of permissions and quotas that defines what a landlord
    can do. When this group is updated, all SubscriptionPlans that reference it
    automatically inherit the new capabilities.
    """

    name = models.CharField(_("Group Name"), max_length=100, unique=True)
    description = models.TextField(_("Description"), blank=True)

    # Permissions & quotas as a JSON object.
    # Example:
    # {
    #   "can_create_properties": true,
    #   "max_properties": 5,
    #   "can_create_units": true,
    #   "max_units_total": 20,
    #   "max_units_per_property": 10,
    #   "can_use_advanced_reports": false,
    #   "can_use_bulk_sms": false,
    #   "can_use_manual_payments": false,
    #   "can_use_api_access": false,
    #   "can_use_priority_support": false,
    #   "can_use_wallet": true,
    #   ...  # extend as needed
    # }
    permissions = models.JSONField(
        _("Permissions & Quotas"),
        default=dict,
        blank=True,
        help_text=_(
            "All capabilities for this feature group. "
            "Use boolean flags for features, integers for quotas."
        ),
    )

    is_active = models.BooleanField(_("Active"), default=True)

    class Meta:
        verbose_name = _("Base Subscription Feature Group")
        verbose_name_plural = _("Base Subscription Feature Groups")
        ordering = ["name"]

    def __str__(self):
        return self.name

    def has_permission(self, key: str, default=False) -> bool:
        """Check if a permission is enabled."""
        return self.permissions.get(key, default)

    def get_quota(self, key: str, default=None):
        """Get a quota value (e.g., max_properties)."""
        return self.permissions.get(key, default)


class SubscriptionPlan(TimeStampedUUIDModel):
    """
    A subscription tier. All capabilities are inherited from the referenced
    BaseSubscriptionFeatureGroup. The plan only adds price and name/description.
    """

    name = models.CharField(_("Plan Name"), max_length=100)
    description = models.TextField(_("Description"), blank=True)
    monthly_price = models.DecimalField(
        _("Monthly Price (XAF)"), max_digits=10, decimal_places=0, default=0
    )

    # The feature group that defines what this plan includes.
    feature_group = models.ForeignKey(
        BaseSubscriptionFeatureGroup,
        on_delete=models.PROTECT,
        related_name="plans",
        verbose_name=_("Feature Group"),
    )

    is_active = models.BooleanField(_("Active"), default=True)

    class Meta:
        verbose_name = _("Subscription Plan")
        verbose_name_plural = _("Subscription Plans")
        ordering = ["monthly_price"]

    def __str__(self):
        return f"{self.name} – {self.monthly_price} XAF/mo"

    def has_feature(self, key: str) -> bool:
        """Delegate permission check to the feature group."""
        return self.feature_group.has_permission(key)

    def get_quota(self, key: str, default=None):
        """Delegate quota check to the feature group."""
        return self.feature_group.get_quota(key, default)


class SubscriptionInvoice(TimeStampedUUIDModel):
    STATUS_CHOICES = (
        ("pending", "Pending"),
        ("paid", "Paid"),
        ("failed", "Failed"),
        ("refunded", "Refunded"),
        ("cancelled", "Cancelled"),
    )

    owner = models.ForeignKey(
        "properties.Owner",
        on_delete=models.PROTECT,
        related_name="invoices",
        verbose_name=_("Owner"),
    )
    plan = models.ForeignKey(
        SubscriptionPlan, on_delete=models.PROTECT, verbose_name=_("Plan")
    )
    amount = models.DecimalField(_("Amount (XAF)"), max_digits=10, decimal_places=0)
    due_date = models.DateField(_("Due Date"))
    status = models.CharField(
        _("Status"), max_length=20, choices=STATUS_CHOICES, default="pending"
    )
    payment = models.OneToOneField(
        "payments.Payment",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="subscription_invoice",
        verbose_name=_("Payment"),
    )
    retry_count = models.PositiveSmallIntegerField(_("Retry Count"), default=0)
    error_message = models.TextField(_("Error Message"), blank=True)
    paid_at = models.DateTimeField(_("Paid At"), null=True, blank=True)

    class Meta:
        verbose_name = _("Subscription Invoice")
        verbose_name_plural = _("Subscription Invoices")
        ordering = ["-due_date"]
        indexes = [
            models.Index(fields=["owner", "status"]),
            models.Index(fields=["due_date"]),
        ]

    def __str__(self):
        return f"Invoice #{self.id[:8]} – {self.owner.user.email} – {self.amount} XAF"
