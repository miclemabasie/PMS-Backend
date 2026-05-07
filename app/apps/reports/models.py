import uuid
from django.db import models
from django.utils.translation import gettext_lazy as _
from model_utils import FieldTracker
from apps.core.models import TimeStampedUUIDModel
from apps.properties.models import Property, Unit, Owner
from apps.maintenance.models import Vendor

# ----------------------------------------------------------------------
# Choices (Cameroon‑aware)
# ----------------------------------------------------------------------


class ExpenseCategory(models.TextChoices):
    MAINTENANCE = "maintenance", _("Maintenance / repairs")
    UTILITY = "utility", _("Utility (water/electricity)")
    TAX = "tax", _("Property tax")
    INSURANCE = "insurance", _("Insurance")
    MANAGEMENT_FEE = "management_fee", _("Management fee")
    OTHER = "other", _("Other")


class Expense(TimeStampedUUIDModel):
    """
    Expense incurred for a property or unit.
    """

    property = models.ForeignKey(
        Property,
        on_delete=models.CASCADE,
        related_name="expenses",
        verbose_name=_("Property"),
    )
    unit = models.ForeignKey(
        Unit,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="expenses",
        verbose_name=_("Unit (optional)"),
    )
    category = models.CharField(
        _("Category"),
        max_length=30,
        choices=ExpenseCategory.choices,
        default=ExpenseCategory.MAINTENANCE,
    )
    amount = models.DecimalField(_("Amount (XAF)"), max_digits=10, decimal_places=0)
    expense_date = models.DateField(_("Expense date"), db_index=True)
    description = models.TextField(_("Description"), blank=True)
    vendor = models.ForeignKey(
        Vendor,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="expenses",
        verbose_name=_("Vendor"),
    )
    receipt = models.FileField(
        _("Receipt"), upload_to="expenses/receipts/", blank=True, null=True
    )
    is_reimbursable = models.BooleanField(_("Reimbursable by tenant"), default=False)
    reimbursed = models.BooleanField(_("Reimbursed"), default=False)

    language = models.CharField(
        max_length=2, choices=[("en", "English"), ("fr", "French")], default="en"
    )
    description_fr = models.TextField(_("Description (French)"), blank=True)

    tracker = FieldTracker(fields=["description"])

    class Meta:
        verbose_name = _("Expense")
        verbose_name_plural = _("Expenses")
        indexes = [
            models.Index(fields=["property", "expense_date"]),
            models.Index(fields=["category"]),
        ]

    def __str__(self):
        return f"{self.category} - {self.amount} XAF on {self.expense_date}"


class TemplateConfig(TimeStampedUUIDModel):
    """Stores landlord's chosen layout and branding for receipts/agreements/reports."""

    class TemplateType(models.TextChoices):
        RECEIPT = "receipt", _("Payment Receipt")
        AGREEMENT = "agreement", _("Rental Agreement")
        REPORT = "report", _("Financial Report")

    LAYOUT_CHOICES = [(i, f"Layout {i}") for i in range(1, 6)]

    landlord = models.ForeignKey(
        Owner, on_delete=models.CASCADE, related_name="templates"
    )
    template_type = models.CharField(max_length=10, choices=TemplateType.choices)
    selected_layout = models.IntegerField(choices=LAYOUT_CHOICES, default=1)
    is_default = models.BooleanField(
        default=False,
        help_text="Only one template per type per landlord can be default.",
    )

    # Branding fields
    logo = models.ImageField(upload_to="templates/logos/", blank=True, null=True)
    primary_color = models.CharField(max_length=7, default="#1E3A8A")
    secondary_color = models.CharField(max_length=7, default="#F59E0B")
    agency_name = models.CharField(max_length=255, blank=True)
    agency_address = models.TextField(blank=True)
    agency_phone = models.CharField(max_length=30, blank=True)
    agency_email = models.EmailField(blank=True)
    footer_text = models.TextField(blank=True)

    # Property name inclusion
    show_property_name = models.BooleanField(default=True)

    class Meta:
        verbose_name = _("Template Configuration")
        verbose_name_plural = _("Template Configurations")
        indexes = [
            models.Index(fields=["landlord", "template_type"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["landlord", "template_type"],
                condition=models.Q(is_default=True),
                name="unique_default_template_per_landlord_type",
            )
        ]

    def __str__(self):
        return f"{self.landlord.user.get_full_name()} - {self.get_template_type_display()} (Layout {self.selected_layout})"

    def save(self, *args, **kwargs):
        if self.is_default:
            qs = TemplateConfig.objects.filter(
                landlord=self.landlord,
                template_type=self.template_type,
                is_default=True,
            )
            if self.pk:
                qs = qs.exclude(pk=self.pk)
            qs.update(is_default=False)
        super().save(*args, **kwargs)
