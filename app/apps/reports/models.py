import uuid
from django.db import models
from django.utils.translation import gettext_lazy as _
from model_utils import FieldTracker
from apps.core.models import TimeStampedUUIDModel
from apps.properties.models import Property, Unit
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
