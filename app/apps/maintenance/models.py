import uuid
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.core.validators import MinValueValidator, MaxValueValidator
from phonenumber_field.modelfields import PhoneNumberField
from model_utils import FieldTracker

from apps.core.models import TimeStampedUUIDModel
from apps.users.models import User
from apps.tenants.models import Tenant
from apps.properties.models import Property, Manager, Unit

# ----------------------------------------------------------------------
# Choices (Cameroon‑aware)
# ----------------------------------------------------------------------


class MaintenancePriority(models.TextChoices):
    LOW = "low", _("Low")
    MEDIUM = "medium", _("Medium")
    HIGH = "high", _("High")
    EMERGENCY = "emergency", _("Emergency")


class MaintenanceStatus(models.TextChoices):
    SUBMITTED = "submitted", _("Submitted")
    ASSIGNED = "assigned", _("Assigned to vendor")
    IN_PROGRESS = "in_progress", _("In progress")
    COMPLETED = "completed", _("Completed")
    CANCELLED = "cancelled", _("Cancelled")


# ----------------------------------------------------------------------
# Maintenance, vendors, and expenses (unchanged)
# ----------------------------------------------------------------------


class Vendor(TimeStampedUUIDModel):
    """
    Service provider (plumber, electrician, etc.)
    """

    company_name = models.CharField(_("Company name"), max_length=255, blank=True)
    contact_name = models.CharField(_("Contact person"), max_length=255)
    phone = PhoneNumberField(_("Phone number"))
    email = models.EmailField(_("Email"), blank=True)
    address = models.CharField(_("Address"), max_length=255, blank=True)
    specialties = models.JSONField(
        _("Specialties"), default=list, blank=True
    )  # e.g., ["plumbing", "electrical"]
    notes = models.TextField(_("Notes"), blank=True)
    is_active = models.BooleanField(_("Active"), default=True)

    language = models.CharField(
        max_length=2, choices=[("en", "English"), ("fr", "French")], default="en"
    )
    company_name_fr = models.CharField(
        _("Company name (French)"), max_length=255, blank=True
    )
    contact_name_fr = models.CharField(
        _("Contact person (French)"), max_length=255, blank=True
    )
    address_fr = models.CharField(_("Address (French)"), max_length=255, blank=True)
    specialties_fr = models.JSONField(
        _("Specialties (French)"), default=list, blank=True
    )
    notes_fr = models.TextField(_("Notes (French)"), blank=True)

    tracker = FieldTracker(
        fields=["company_name", "contact_name", "address", "specialties", "notes"]
    )

    class Meta:
        verbose_name = _("Vendor")
        verbose_name_plural = _("Vendors")
        indexes = [
            models.Index(fields=["phone"]),
        ]

    def __str__(self):
        return self.company_name or self.contact_name


class MaintenanceRequest(TimeStampedUUIDModel):
    """
    Maintenance request submitted by tenant or manager.
    """

    unit = models.ForeignKey(
        Unit,
        on_delete=models.CASCADE,
        related_name="maintenance_requests",
        verbose_name=_("Unit"),
    )
    tenant = models.ForeignKey(
        Tenant,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="maintenance_requests",
        verbose_name=_("Requested by (tenant)"),
    )
    requested_by_manager = models.ForeignKey(
        Manager,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="maintenance_requests",
        verbose_name=_("Requested by (manager)"),
    )
    title = models.CharField(_("Title"), max_length=255)
    description = models.TextField(_("Description"))
    priority = models.CharField(
        _("Priority"),
        max_length=20,
        choices=MaintenancePriority.choices,
        default=MaintenancePriority.MEDIUM,
    )
    status = models.CharField(
        _("Status"),
        max_length=20,
        choices=MaintenanceStatus.choices,
        default=MaintenanceStatus.SUBMITTED,
        db_index=True,
    )
    assigned_vendor = models.ForeignKey(
        Vendor,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="maintenance_requests",
        verbose_name=_("Assigned vendor"),
    )
    estimated_cost = models.DecimalField(
        _("Estimated cost (XAF)"),
        max_digits=10,
        decimal_places=0,
        blank=True,
        null=True,
    )
    actual_cost = models.DecimalField(
        _("Actual cost (XAF)"), max_digits=10, decimal_places=0, blank=True, null=True
    )
    approved_by = models.ForeignKey(
        Manager,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="approved_maintenance",
        verbose_name=_("Approved by"),
    )
    approved_at = models.DateTimeField(_("Approved at"), blank=True, null=True)
    completed_at = models.DateTimeField(_("Completed at"), blank=True, null=True)
    notes = models.TextField(_("Notes"), blank=True)

    language = models.CharField(
        max_length=2, choices=[("en", "English"), ("fr", "French")], default="en"
    )
    title_fr = models.CharField(_("Title (French)"), max_length=255, blank=True)
    description_fr = models.TextField(_("Description (French)"), blank=True)

    tracker = FieldTracker(fields=["title", "description"])

    class Meta:
        verbose_name = _("Maintenance request")
        verbose_name_plural = _("Maintenance requests")
        indexes = [
            models.Index(fields=["unit", "status"]),
            models.Index(fields=["priority"]),
        ]

    def __str__(self):
        return f"{self.title} - {self.unit}"


class MaintenanceRequestImage(TimeStampedUUIDModel):
    maintenance_request = models.ForeignKey(
        MaintenanceRequest,
        on_delete=models.CASCADE,
        related_name="images",
        verbose_name=_("Maintenance request"),
    )
    image = models.ImageField(_("Image"), upload_to="maintenance_requests")

    class Meta:
        verbose_name = _("Maintenance request image")
        verbose_name_plural = _("Maintenance request images")
