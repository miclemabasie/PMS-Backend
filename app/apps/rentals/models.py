import uuid
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.core.validators import MinValueValidator, MaxValueValidator
from phonenumber_field.modelfields import PhoneNumberField
from model_utils import FieldTracker

from apps.core.models import TimeStampedUUIDModel
from apps.users.models import User
from apps.tenants.models import Tenant
from apps.properties.models import Property, Owner, Manager

# ----------------------------------------------------------------------
# Choices (Cameroon‑aware)
# ----------------------------------------------------------------------


class UnitType(models.TextChoices):
    STUDIO = "studio", _("Studio")
    ONE_BED = "1_bed", _("1 bedroom")
    TWO_BED = "2_bed", _("2 bedrooms")
    THREE_BED = "3_bed", _("3 bedrooms")
    SHOP = "shop", _("Shop")
    OFFICE = "office", _("Office")
    OTHER = "other", _("Other")


class LeaseStatus(models.TextChoices):
    ACTIVE = "active", _("Active")
    EXPIRED = "expired", _("Expired")
    TERMINATED = "terminated", _("Terminated")
    RENEWED = "renewed", _("Renewed")


class PaymentMethod(models.TextChoices):
    MTN_MOMO = "mtn_momo", _("MTN MoMo")
    ORANGE_MONEY = "orange_money", _("Orange Money")
    BANK_TRANSFER = "bank_transfer", _("Bank transfer")
    CASH = "cash", _("Cash")
    OTHER = "other", _("Other")


class PaymentStatus(models.TextChoices):
    PENDING = "pending", _("Pending")
    COMPLETED = "completed", _("Completed")
    FAILED = "failed", _("Failed")
    REFUNDED = "refunded", _("Refunded")


class PaymentType(models.TextChoices):
    RENT = "rent", _("Rent")
    DEPOSIT = "deposit", _("Security deposit")
    FEE = "fee", _("Fee / penalty")
    UTILITY = "utility", _("Utility bill")
    OTHER = "other", _("Other")


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


class ExpenseCategory(models.TextChoices):
    MAINTENANCE = "maintenance", _("Maintenance / repairs")
    UTILITY = "utility", _("Utility (water/electricity)")
    TAX = "tax", _("Property tax")
    INSURANCE = "insurance", _("Insurance")
    MANAGEMENT_FEE = "management_fee", _("Management fee")
    OTHER = "other", _("Other")


class LateFeeType(models.TextChoices):
    FIXED = "fixed", _("Fixed amount (XAF)")
    PERCENTAGE = "percentage", _("Percentage of rent")


# ----------------------------------------------------------------------
# Payment Term Model (NEW)
# ----------------------------------------------------------------------


class PaymentTerm(TimeStampedUUIDModel):
    """
    Defines a payment schedule interval.
    Examples: Monthly (1 month), Quarterly (3 months), Yearly (12 months).
    """

    name = models.CharField(_("Name"), max_length=50, unique=True)
    interval_months = models.PositiveSmallIntegerField(
        _("Interval (months)"),
        validators=[MinValueValidator(1)],
        help_text=_(
            "Number of months between payments (1 = monthly, 3 = quarterly, etc.)"
        ),
    )
    description = models.TextField(_("Description"), blank=True)

    class Meta:
        verbose_name = _("Payment term")
        verbose_name_plural = _("Payment terms")
        ordering = ["interval_months"]

    def __str__(self):
        return self.name


# ----------------------------------------------------------------------
# Role‑specific profiles (linked to User)
# ----------------------------------------------------------------------


# ----------------------------------------------------------------------
# Core property models
# ----------------------------------------------------------------------


class Unit(TimeStampedUUIDModel):
    """
    A rentable unit within a property.
    """

    property = models.ForeignKey(
        Property,
        on_delete=models.CASCADE,
        related_name="units",
        verbose_name=_("Property"),
    )
    unit_number = models.CharField(_("Unit number / name"), max_length=50)
    unit_type = models.CharField(
        _("Unit type"),
        max_length=20,
        choices=UnitType.choices,
        default=UnitType.ONE_BED,
    )
    floor = models.PositiveSmallIntegerField(_("Floor"), blank=True, null=True)
    size_m2 = models.PositiveIntegerField(_("Size (m²)"), blank=True, null=True)
    bedrooms = models.PositiveSmallIntegerField(_("Bedrooms"), default=1)
    bathrooms = models.PositiveSmallIntegerField(_("Bathrooms"), default=1)
    default_rent_amount = models.DecimalField(
        _("Default rent amount (XAF)"),
        max_digits=10,
        decimal_places=0,
        help_text=_("Default amount per payment interval (if no lease override)"),
    )
    default_payment_term = models.ForeignKey(
        PaymentTerm,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="units",
        verbose_name=_("Default payment term"),
        help_text=_("Default interval for this unit (e.g., monthly, yearly)"),
    )
    default_security_deposit = models.DecimalField(
        _("Default security deposit (XAF)"),
        max_digits=10,
        decimal_places=0,
        blank=True,
        null=True,
    )
    status = models.CharField(
        _("Status"),
        max_length=20,
        choices=[
            ("vacant", _("Vacant")),
            ("occupied", _("Occupied")),
            ("maintenance", _("Maintenance")),
        ],
        default="vacant",
        db_index=True,
    )
    amenities = models.JSONField(_("Amenities"), default=list, blank=True)
    images = models.JSONField(_("Image URLs"), default=list, blank=True)
    # Cameroon specifics
    water_meter_number = models.CharField(
        _("Water meter number"), max_length=50, blank=True
    )
    electricity_meter_number = models.CharField(
        _("Electricity meter number"), max_length=50, blank=True
    )
    has_prepaid_meter = models.BooleanField(_("Prepaid meter"), default=False)
    # Flexible custom fields
    custom_fields = models.JSONField(_("Custom fields"), default=dict, blank=True)

    language = models.CharField(
        max_length=2, choices=[("en", "English"), ("fr", "French")], default="en"
    )
    amenities_fr = models.JSONField(_("Amenities (French)"), default=list, blank=True)

    tracker = FieldTracker(fields=["amenities"])

    class Meta:
        verbose_name = _("Unit")
        verbose_name_plural = _("Units")
        unique_together = [["property", "unit_number"]]
        indexes = [
            models.Index(fields=["property", "status"]),
            models.Index(fields=["unit_number"]),
        ]

    def __str__(self):
        return f"{self.property.name} - {self.unit_number}"


# ----------------------------------------------------------------------
# Lease and payment models (with dynamic payment plans)
# ----------------------------------------------------------------------


class Lease(TimeStampedUUIDModel):
    """
    Rental agreement linking a unit to one or more tenants.
    Includes payment term and amount per interval.
    """

    unit = models.ForeignKey(
        Unit, on_delete=models.CASCADE, related_name="leases", verbose_name=_("Unit")
    )
    tenants = models.ManyToManyField(
        Tenant, through="LeaseTenant", related_name="leases", verbose_name=_("Tenants")
    )
    start_date = models.DateField(_("Start date"), db_index=True)
    end_date = models.DateField(_("End date"), db_index=True)

    # Payment plan fields (NEW)
    payment_term = models.ForeignKey(
        PaymentTerm,
        on_delete=models.PROTECT,
        related_name="leases",
        verbose_name=_("Payment term"),
        help_text=_("How often rent is due (monthly, quarterly, yearly, etc.)"),
    )
    rent_amount = models.DecimalField(
        _("Rent amount per interval (XAF)"),
        max_digits=10,
        decimal_places=0,
        help_text=_("Amount due each payment period (e.g., 600,000 XAF for 12 months)"),
    )
    due_day = models.PositiveSmallIntegerField(
        _("Due day of month"),
        default=1,
        validators=[MinValueValidator(1), MaxValueValidator(31)],
        help_text=_("Day of the month when payment is due (e.g., 1st, 5th)"),
    )
    # End new fields

    security_deposit = models.DecimalField(
        _("Security deposit (XAF)"), max_digits=10, decimal_places=0
    )
    deposit_paid = models.BooleanField(_("Deposit paid"), default=False)
    late_fee_type = models.CharField(
        _("Late fee type"),
        max_length=20,
        choices=LateFeeType.choices,
        default=LateFeeType.FIXED,
    )
    late_fee_value = models.DecimalField(
        _("Late fee value"),
        max_digits=10,
        decimal_places=0,
        default=0,
        help_text=_("Amount in XAF or percentage points"),
    )
    utilities_included = models.JSONField(
        _("Utilities included"), default=list, blank=True
    )
    documents = models.JSONField(
        _("Document URLs"), default=list, blank=True
    )  # or use Document model
    status = models.CharField(
        _("Status"),
        max_length=20,
        choices=LeaseStatus.choices,
        default=LeaseStatus.ACTIVE,
        db_index=True,
    )
    termination_reason = models.TextField(_("Termination reason"), blank=True)
    renewed_from = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="renewed_to",
        verbose_name=_("Renewed from"),
    )

    class Meta:
        verbose_name = _("Lease")
        verbose_name_plural = _("Leases")
        indexes = [
            models.Index(fields=["unit", "start_date", "end_date"]),
            models.Index(fields=["status"]),
            models.Index(fields=["payment_term"]),  # new
        ]

    def __str__(self):
        term_name = self.payment_term.name if self.payment_term else "?"
        return f"Lease {self.id} - {self.unit} ({self.start_date} to {self.end_date}) - {term_name}"


class LeaseTenant(TimeStampedUUIDModel):
    """
    Through model for Lease ↔ Tenant (allows storing additional info per tenant in a lease).
    """

    lease = models.ForeignKey(
        Lease, on_delete=models.CASCADE, related_name="lease_tenants"
    )
    tenant = models.ForeignKey(
        Tenant, on_delete=models.CASCADE, related_name="lease_tenants"
    )
    is_primary = models.BooleanField(_("Primary tenant"), default=False)
    signed_at = models.DateTimeField(_("Signed at"), blank=True, null=True)

    class Meta:
        verbose_name = _("Lease tenant")
        verbose_name_plural = _("Lease tenants")
        unique_together = [["lease", "tenant"]]
        indexes = [
            models.Index(fields=["lease", "tenant"]),
        ]

    def __str__(self):
        return f"{self.tenant} in {self.lease}"


class Payment(TimeStampedUUIDModel):
    """
    Record of a payment (rent, deposit, fee, etc.)
    Now includes period covered by the payment.
    """

    lease = models.ForeignKey(
        Lease,
        on_delete=models.CASCADE,
        related_name="payments",
        verbose_name=_("Lease"),
    )
    tenant = models.ForeignKey(
        Tenant,
        on_delete=models.CASCADE,
        related_name="payments",
        null=True,
        blank=True,
        verbose_name=_("Paying tenant"),
    )
    amount = models.DecimalField(_("Amount (XAF)"), max_digits=10, decimal_places=0)
    payment_date = models.DateField(_("Payment date"), db_index=True)
    payment_method = models.CharField(
        _("Payment method"),
        max_length=20,
        choices=PaymentMethod.choices,
        default=PaymentMethod.CASH,
    )
    payment_type = models.CharField(
        _("Payment type"),
        max_length=20,
        choices=PaymentType.choices,
        default=PaymentType.RENT,
    )
    status = models.CharField(
        _("Status"),
        max_length=20,
        choices=PaymentStatus.choices,
        default=PaymentStatus.PENDING,
        db_index=True,
    )
    # New fields to track the rental period covered
    period_start = models.DateField(
        _("Period start"),
        help_text=_("Start date of the rental period this payment covers"),
    )
    period_end = models.DateField(
        _("Period end"),
        help_text=_("End date of the rental period this payment covers"),
    )
    # End new fields

    transaction_id = models.CharField(_("Transaction ID"), max_length=255, blank=True)
    # For mobile money
    mobile_provider = models.CharField(
        _("Mobile provider"), max_length=50, blank=True
    )  # e.g., "MTN"
    mobile_phone = PhoneNumberField(_("Payer phone number"), blank=True)
    mobile_reference = models.CharField(
        _("Mobile money reference"), max_length=255, blank=True
    )
    # For bank/cash
    bank_name = models.CharField(_("Bank name"), max_length=100, blank=True)
    check_number = models.CharField(_("Check number"), max_length=50, blank=True)
    notes = models.TextField(_("Notes"), blank=True)
    # For reconciliation with payment gateway webhooks
    gateway_response = models.JSONField(_("Gateway response"), default=dict, blank=True)

    class Meta:
        verbose_name = _("Payment")
        verbose_name_plural = _("Payments")
        indexes = [
            models.Index(fields=["lease", "payment_date"]),
            models.Index(fields=["transaction_id"]),
            models.Index(fields=["status"]),
            models.Index(fields=["period_start", "period_end"]),  # new
        ]

    def __str__(self):
        return f"Payment {self.amount} XAF - {self.payment_type} on {self.payment_date} (covers {self.period_start} to {self.period_end})"


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
    photos = models.JSONField(_("Photo URLs"), default=list, blank=True)
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


# ----------------------------------------------------------------------
# Documents and communication (unchanged)
# ----------------------------------------------------------------------


class Document(TimeStampedUUIDModel):
    """
    Generic document attached to any model (Property, Unit, Lease, Tenant, etc.)
    Uses Django's ContentTypes framework for flexibility.
    """

    from django.contrib.contenttypes.fields import GenericForeignKey
    from django.contrib.contenttypes.models import ContentType

    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = (
        models.UUIDField()
    )  # because our models use UUID as primary key (id field)
    content_object = GenericForeignKey("content_type", "object_id")

    name = models.CharField(_("Document name"), max_length=255)
    file = models.FileField(_("File"), upload_to="documents/%Y/%m/")
    description = models.TextField(_("Description"), blank=True)
    uploaded_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="uploaded_documents",
        verbose_name=_("Uploaded by"),
    )

    class Meta:
        verbose_name = _("Document")
        verbose_name_plural = _("Documents")
        indexes = [
            models.Index(fields=["content_type", "object_id"]),
        ]

    def __str__(self):
        return self.name
