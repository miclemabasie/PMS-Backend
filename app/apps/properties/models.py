from django.db import models
from apps.core.models import TimeStampedUUIDModel, PaymentMethod, PaymentType
from django_countries.fields import CountryField
from django.utils.translation import gettext_lazy as _
from apps.users.models import User
from phonenumber_field.modelfields import PhoneNumberField
from django.core.validators import MinValueValidator, MaxValueValidator
from model_utils import FieldTracker

# from apps.payments.models import PaymentTerm
from django.urls import reverse
from django.conf import settings
from decimal import Decimal, ROUND_HALF_UP
import logging

logger = logging.getLogger(__name__)

# Create your models here.


class PropertyType(models.TextChoices):
    APARTMENT = "apartment_unit", _("Apartment (Single Unit)")
    APARTMENT_BUILDING = "apartment_building", _("Apartment Building")
    VILLA = "villa", _("Villa")
    HOUSE = "house", _("House")
    DUPLEX = "duplex", _("Duplex")
    STUDIO = "studio", _("Studio")
    LAND = "land", _("Land")
    SHOP = "shop", _("Shop / Store")
    OFFICE = "office", _("Office")
    COMMERCIAL = "commercial", _("Commercial Space")
    HOSTEL = "hostel", _("Hostel / Student Housing")
    OTHER = "other", _("Other")


class UnitType(models.TextChoices):
    STUDIO = "studio", _("Studio")
    ONE_BED = "1_bed", _("1 bedroom")
    TWO_BED = "2_bed", _("2 bedrooms")
    THREE_BED = "3_bed", _("3 bedrooms")
    SHOP = "shop", _("Shop")
    OFFICE = "office", _("Office")
    OTHER = "other", _("Other")


class RentDurationType(models.TextChoices):
    MONTHLY = "monthly", _("Monthly")
    YEARLY = "yearly", _("Yearly")


class Owner(TimeStampedUUIDModel):
    """
    Property owner. Linked to a User account.
    """

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="owner_profile",
        verbose_name=_("User"),
    )
    preferred_payout_method = models.CharField(
        _("Preferred payout method"),
        max_length=20,
        choices=PaymentMethod.choices,
        default=PaymentMethod.BANK_TRANSFER,
    )
    mobile_money_number = PhoneNumberField(
        _("Mobile money number"),
        max_length=30,
        blank=True,
        null=True,
        help_text=_("For MoMo/Orange payouts"),
    )
    bank_account_name = models.CharField(
        _("Bank account name"), max_length=255, blank=True
    )
    bank_name = models.CharField(_("Bank name"), max_length=100, blank=True)
    bank_account_number = models.CharField(
        _("Account number"), max_length=50, blank=True
    )
    bank_code = models.CharField(_("Bank code / SWIFT"), max_length=20, blank=True)
    tax_id = models.CharField(
        _("Tax ID (NIU)"),
        max_length=50,
        blank=True,
        help_text=_("Numéro d'Identification Unique"),
    )

    class Meta:
        verbose_name = _("Owner")
        verbose_name_plural = _("Owners")
        indexes = [
            models.Index(fields=["user"]),
        ]

    def __str__(self):
        return f"Owner: {self.user.get_full_name()}"

    def save(self, *args, **kwargs):
        # update the role of the user
        self.user.role = "landlord"
        self.user.save()
        super().save()


class Property(TimeStampedUUIDModel):
    """
    A property (building or land) that contains one or more units.
    """

    name = models.CharField(_("Property name"), max_length=255)
    property_type = models.CharField(
        _("Property type"),
        max_length=20,
        choices=PropertyType.choices,
        default=PropertyType.APARTMENT,
    )

    description = models.TextField(_("Description"), blank=True)
    address_line1 = models.CharField(_("Address line 1"), max_length=255)
    address_line2 = models.CharField(_("Address line 2"), max_length=255, blank=True)

    city = models.CharField(_("City"), max_length=100, db_index=True)
    state = models.CharField(_("State/Region"), max_length=100, blank=True)
    country = CountryField(_("Country"), default="CM")
    images = models.JSONField(_("Image URLs"), default=list, blank=True)
    postal_code = models.CharField(_("Postal code"), max_length=20, blank=True)
    # Cameroon specifics
    has_generator = models.BooleanField(_("Has generator"), default=False)
    has_water_tank = models.BooleanField(_("Has water tank"), default=False)
    amenities = models.JSONField(
        _("Amenities"), default=list, blank=True
    )  # list of strings
    owners = models.ManyToManyField(
        Owner,
        through="PropertyOwnership",
        related_name="properties",
        verbose_name=_("Owners"),
    )
    status = models.CharField(
        _("Status"),
        max_length=20,
        choices=[("MAINTENANCE", "Maintenance"), ("ACTIVE", "Active")],
        default="active",
    )
    starting_amount = models.DecimalField(
        _("Starting amount"), max_digits=10, decimal_places=2, default=0
    )
    top_amount = models.DecimalField(
        _("Top amount"), max_digits=10, decimal_places=2, default=0
    )
    is_active = models.BooleanField(_("Active"), default=True)

    language = models.CharField(
        _("Original language"),
        max_length=2,
        choices=[("en", "English"), ("fr", "French")],
        default="en",
        help_text=_("Language of the main text fields (name, description, amenities)"),
    )
    name_fr = models.CharField(_("Name (French)"), max_length=255, blank=True)
    description_fr = models.TextField(_("Description (French)"), blank=True)
    amenities_fr = models.JSONField(_("Amenities (French)"), default=list, blank=True)

    tracker = FieldTracker(fields=["name", "description", "amenities"])

    class Meta:
        verbose_name = _("Property")
        verbose_name_plural = _("Properties")
        indexes = [
            models.Index(fields=["name"]),
            models.Index(fields=["city"]),
            models.Index(fields=["is_active"]),
        ]

    @property
    def active_payment_config(self):
        return getattr(self, "payment_config", None)

    def __str__(self):
        return self.name

    def get_primary_image(self):
        image = self.property_images.filter(is_primary=True).first()
        if image:
            return f"{settings.DOMAIN}{image.image.url}"
        return None

    def get_payout_owner(self):
        """Return the primary owner (or first owner) for payouts."""
        ownership = self.ownership_records.filter(is_primary=True).first()
        if not ownership:
            ownership = self.ownership_records.first()
        return ownership.owner if ownership else None


class PropertyImage(models.Model):
    property = models.ForeignKey(
        "Property", on_delete=models.CASCADE, related_name="property_images"
    )
    alt_text = models.CharField(_("Alt text"), max_length=255, blank=True)
    is_primary = models.BooleanField(_("Primary image"), default=False)
    image = models.ImageField(upload_to="properties/")

    def get_property_image_url(self):
        if not self.image:
            return None
        return f"{settings.DOMAIN}{self.image.url}"


class PropertyOwnership(TimeStampedUUIDModel):
    """
    Through model for Property ↔ Owner with ownership percentage.
    """

    property = models.ForeignKey(
        Property, on_delete=models.CASCADE, related_name="ownership_records"
    )
    owner = models.ForeignKey(
        Owner, on_delete=models.CASCADE, related_name="ownership_records"
    )
    percentage = models.DecimalField(
        _("Ownership percentage"),
        max_digits=5,
        decimal_places=2,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        default=100.0,
    )
    is_primary = models.BooleanField(_("Primary owner"), default=False)

    class Meta:
        verbose_name = _("Property ownership")
        verbose_name_plural = _("Property ownerships")
        unique_together = [["property", "owner"]]
        indexes = [
            models.Index(fields=["property", "owner"]),
        ]

    def __str__(self):
        return f"{self.owner} owns {self.percentage}% of {self.property}"


class Manager(TimeStampedUUIDModel):
    """
    Property manager. Linked to a User account.
    """

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="manager_profile",
        verbose_name=_("User"),
    )
    commission_rate = models.DecimalField(
        _("Commission rate (%)"),
        max_digits=5,
        decimal_places=2,
        default=0.0,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
    )
    managed_properties = models.ManyToManyField(
        "Property",
        related_name="managers",
        blank=True,
        verbose_name=_("Managed properties"),
    )
    is_active = models.BooleanField(_("Active"), default=True)

    class Meta:
        verbose_name = _("Manager")
        verbose_name_plural = _("Managers")
        indexes = [
            models.Index(fields=["user"]),
        ]

    def __str__(self):
        return f"Manager: {self.user.get_full_name()}"


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
    rent_duration_type = models.CharField(
        _("Rent duration type"),
        max_length=20,
        choices=RentDurationType.choices,
        default=RentDurationType.MONTHLY,
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
    yearly_rent = models.DecimalField(
        _("Year rented"), max_digits=10, decimal_places=0, blank=True, null=True
    )
    monthly_rent = models.DecimalField(
        _("Monthly rent (XAF)"),
        max_digits=10,
        decimal_places=0,
        blank=True,
        null=True,
    )
    default_security_deposit = models.DecimalField(
        _("Default security deposit (XAF)"),
        max_digits=10,
        decimal_places=0,
        blank=True,
        null=True,
    )
    default_payment_plan = models.ForeignKey(
        "payments.PaymentPlan", null=True, blank=True, on_delete=models.SET_NULL
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

    def calculate_default_price_based_on_duration(self) -> Decimal:
        if self.rent_duration_type == RentDurationType.MONTHLY:
            return self.calculate_monthly_rent()
        return self.calculate_yearly_rent()

    def calculate_monthly_rent(self) -> Decimal:
        """Return monthly rent as integer XAF, using yearly rent if available."""
        if self.yearly_rent is not None:
            # Yearly rent / 12, rounded to nearest integer
            return (self.yearly_rent / Decimal("12")).quantize(
                Decimal("1."), rounding=ROUND_HALF_UP
            )
        # Fallback to default monthly amount
        return self.default_rent_amount

    def calculate_yearly_rent(self) -> Decimal:
        """Return yearly rent as integer XAF (monthly * 12)."""
        if self.monthly_rent is not None:
            return self.monthly_rent * Decimal("12")
        # Fallback: default monthly amount * 12
        return self.default_rent_amount * Decimal("12")

    def save(self, *args, **kwargs):
        # Step 1: If both primary and secondary are None, use default_rent_amount as primary
        if self.rent_duration_type == RentDurationType.MONTHLY:
            if self.monthly_rent is None:
                self.monthly_rent = self.default_rent_amount or 0
            # Derive yearly_rent (read-only in API, but stored for performance)
            self.yearly_rent = self.monthly_rent * Decimal("12")
        else:  # yearly
            if self.yearly_rent is None:
                self.yearly_rent = self.default_rent_amount or 0
            # Derive monthly_rent, rounded to nearest integer XAF
            self.monthly_rent = (self.yearly_rent / Decimal("12")).quantize(
                Decimal("1."), rounding=ROUND_HALF_UP
            )

        # Step 2: Ensure consistency (optional – warn if user provided both and they mismatch)
        if self.rent_duration_type == RentDurationType.MONTHLY:
            expected_yearly = self.monthly_rent * Decimal("12")
            if self.yearly_rent != expected_yearly:
                # Log warning but do not override (the yearly field is read-only anyway)
                logger.warning(
                    f"Unit {self.pkid}: yearly_rent {self.yearly_rent} does not match "
                    f"monthly_rent * 12 = {expected_yearly}. Overriding yearly_rent."
                )
                self.yearly_rent = expected_yearly
        else:
            expected_monthly = (self.yearly_rent / Decimal("12")).quantize(
                Decimal("1."), rounding=ROUND_HALF_UP
            )
            if self.monthly_rent != expected_monthly:
                logger.warning(
                    f"Unit {self.pkid}: monthly_rent {self.monthly_rent} does not match "
                    f"yearly_rent / 12 = {expected_monthly}. Overriding monthly_rent."
                )
                self.monthly_rent = expected_monthly

        super().save(*args, **kwargs)


class UnitImage(models.Model):
    unit = models.ForeignKey(
        "Unit", on_delete=models.CASCADE, related_name="unit_images"
    )
    alt_text = models.CharField(_("Alt text"), max_length=255, blank=True)
    is_primary = models.BooleanField(_("Primary image"), default=False)
    image = models.ImageField(upload_to="properties/units/")


class PaymentConfiguration(models.Model):
    """
    Defines how fees are applied for a property.
    One configuration per property (auto-created on property save).
    """

    FEES_PAYER_CHOICES = [
        ("tenant", "Tenant pays"),
        ("landlord", "Landlord pays"),
        ("split", "Shared (50/50)"),
    ]
    PRICING_MODEL_CHOICES = [
        ("per_transaction", "Per‑transaction fees"),
        ("subscription", "Monthly subscription (no per‑transaction fees)"),
    ]

    property = models.OneToOneField(
        "Property", on_delete=models.CASCADE, related_name="payment_config"
    )
    pricing_model = models.CharField(
        max_length=20, choices=PRICING_MODEL_CHOICES, default="per_transaction"
    )

    # For subscription model
    monthly_subscription_fee = models.DecimalField(
        max_digits=10,
        decimal_places=0,
        default=0,
        help_text="XAF per month, charged to landlord",
    )

    # For per‑transaction model
    platform_fee_cap = models.PositiveIntegerField(
        default=1000, help_text="Maximum platform fee (XAF)"
    )
    platform_fee_percent = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=1.0,
        help_text="% of rent (capped by platform_fee_cap)",
    )
    gateway_fee_percent = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=2.0,
        help_text="% on the amount disbursed to landlord",
    )
    # Who pays which fee?
    platform_fee_payer = models.CharField(
        max_length=10, choices=FEES_PAYER_CHOICES, default="tenant"
    )
    gateway_fee_payer = models.CharField(
        max_length=10, choices=FEES_PAYER_CHOICES, default="tenant"
    )

    # Optional fixed extra fee (e.g., 100 XAF) – always paid by tenant
    fixed_extra_fee = models.DecimalField(
        max_digits=10,
        decimal_places=0,
        default=0,
        help_text="Fixed fee added to tenant total",
    )

    # Payment methods that incur gateway fee (list of strings)
    gateway_methods = models.JSONField(
        default=list,
        blank=True,
        help_text="e.g., ['mtn_momo', 'orange_money'] – leave empty to never charge gateway fee",
    )

    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Payment Configuration"
        verbose_name_plural = "Payment Configurations"

    def __str__(self):
        return f"Payment config for {self.property.name} ({self.pricing_model})"
