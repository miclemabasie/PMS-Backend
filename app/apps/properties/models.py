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
    subscription_plan = models.ForeignKey(
        "subscriptions.SubscriptionPlan",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    subscription_status = models.CharField(
        max_length=20,
        choices=[
            ("active", "Active"),
            ("trial", "Trial"),
            ("past_due", "Past Due"),
            ("cancelled", "Cancelled"),
            ("expired", "Expired"),
        ],
        default="trial",
    )
    subscription_start_date = models.DateField(null=True, blank=True)
    subscription_end_date = models.DateField(null=True, blank=True)
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

    payment_pin = models.CharField(
        _("Payment Pin"),
        max_length=128,
        blank=True,
        null=True,
        help_text=_("Hashed PIN for manual payment authorization.")
    )

    def set_payment_pin(self, raw_pin: str) -> None:
        from django.contrib.auth.hashers import make_password
        self.payment_pin = make_password(raw_pin)
        self.save(update_fields=["payment_pin"])


    def check_payment_pin(self, raw_pin: str) -> bool:
        from django.contrib.auth.hashers import check_password
        if not self.payment_pin:
            return False
        return check_password(raw_pin, self.payment_pin)

    
    def has_active_subscription(self) -> bool:
        """Check if the owner has an active subscription."""
        return self.subscription_status in ("active", "trial")

        

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


class PaymentOwnerSplit(models.Model):
    payment = models.ForeignKey(
        "payments.Payment", on_delete=models.CASCADE, related_name="owner_splits"
    )
    owner = models.ForeignKey("properties.Owner", on_delete=models.PROTECT)
    amount = models.DecimalField(max_digits=10, decimal_places=0)
    percentage = models.DecimalField(max_digits=5, decimal_places=2)


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


class OwnerPaymentConfig(TimeStampedUUIDModel):
    """
    Landlord‑global default fee rates and distribution rules.
    Used when a property does not override them.
    """

    owner = models.OneToOneField(
        "properties.Owner",
        on_delete=models.CASCADE,
        related_name="payment_config",
        verbose_name=_("Owner"),
    )

    platform_fee_percent = models.DecimalField(
        _("Platform Fee (%)"),
        max_digits=5,
        decimal_places=2,
        default=1.0,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
    )
    platform_fee_cap = models.PositiveIntegerField(
        _("Platform Fee Cap (XAF)"), default=1000
    )
    gateway_fee_percent = models.DecimalField(
        _("Gateway Fee (%)"),
        max_digits=5,
        decimal_places=2,
        default=2.0,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
    )
    fixed_extra_fee = models.DecimalField(
        _("Fixed Extra Fee (XAF)"), max_digits=10, decimal_places=0, default=0
    )

    # Payer choices
    PAYER_CHOICES = [
        ("tenant", "Tenant"),
        ("landlord", "Landlord"),
        ("split", "Split 50/50"),
    ]

    platform_fee_payer = models.CharField(
        _("Platform Fee Payer"), max_length=10, choices=PAYER_CHOICES, default="tenant"
    )
    gateway_fee_payer = models.CharField(
        _("Gateway Fee Payer"), max_length=10, choices=PAYER_CHOICES, default="tenant"
    )
    wallet_fee_payer = models.CharField(
        _("Wallet Fee Payer"), max_length=10, choices=PAYER_CHOICES, default="tenant"
    )

    gateway_methods = models.JSONField(
        _("Gateway Methods"),
        default=list,
        blank=True,
        help_text=_("e.g., ['mtn_momo', 'orange_money']"),
    )

    pricing_model = models.CharField(
        _("Pricing Model"),
        max_length=20,
        choices=[
            ("per_transaction", "Per‑transaction"),
            ("subscription", "Subscription"),
        ],
        default="per_transaction",
    )

    is_active = models.BooleanField(_("Active"), default=True)

    class Meta:
        verbose_name = _("Owner Payment Config")
        verbose_name_plural = _("Owner Payment Configs")

    def __str__(self):
        return f"Payment Config for {self.owner.user.email}"


class PropertyPaymentConfig(TimeStampedUUIDModel):
    """
    Per‑property override of fee rules and default payment plan template.
    Highest priority (after fee_overrides JSON) in the fee resolution chain.
    """

    property = models.OneToOneField(
        Property,
        on_delete=models.CASCADE,
        related_name="property_payment_config",
        verbose_name=_("Property"),
    )

    pricing_model = models.CharField(
        _("Pricing Model"),
        max_length=20,
        choices=[
            ("per_transaction", "Per‑transaction"),
            ("subscription", "Subscription"),
        ],
        default="per_transaction",
    )

    PAYER_CHOICES = [
        ("tenant", "Tenant"),
        ("landlord", "Landlord"),
        ("split", "Split 50/50"),
    ]

    platform_fee_payer = models.CharField(
        _("Platform Fee Payer"), max_length=10, choices=PAYER_CHOICES, default="tenant"
    )
    gateway_fee_payer = models.CharField(
        _("Gateway Fee Payer"), max_length=10, choices=PAYER_CHOICES, default="tenant"
    )
    wallet_fee_payer = models.CharField(
        _("Wallet Fee Payer"), max_length=10, choices=PAYER_CHOICES, default="tenant"
    )

    gateway_methods = models.JSONField(_("Gateway Methods"), default=list, blank=True)

    # Highest priority override – bypasses all other rates
    fee_overrides = models.JSONField(
        _("Fee Overrides"),
        default=dict,
        blank=True,
        help_text=_(
            "Override rates, caps, fixed fees for this property. "
            "Example: {'platform_fee_percent': 0.5, 'platform_fee_cap': 500}"
        ),
    )

    # Default payment plan template used when creating a new agreement on this property
    default_payment_plan = models.ForeignKey(
        "payments.PaymentPlan",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="default_for_properties",
        verbose_name=_("Default Payment Plan"),
        help_text=_("Template copied when a new rental agreement is created."),
    )

    # Wallet and manual payment features
    enable_wallet_payments = models.BooleanField(
        _("Enable Wallet Payments"), default=True
    )
    allow_manual_payments = models.BooleanField(
        _("Allow Manual Payments"), default=False
    )
    manual_payment_requires_verification = models.BooleanField(
        _("Manual Payment Requires Tenant Verification"), default=True
    )

    currency = models.CharField(
        _("Currency"),
        max_length=3,
        choices=[("XAF", "XAF"), ("USD", "USD"), ("EUR", "EUR")],
        default="XAF",
    )

    is_active = models.BooleanField(_("Active"), default=True)

    class Meta:
        verbose_name = _("Property Payment Config")
        verbose_name_plural = _("Property Payment Configs")

    def __str__(self):
        return f"Payment Config for {self.property.name}"

    def get_effective_config(self, owner):
        from apps.core.models import PlatformSettings

        config = PlatformSettings.get_settings()

        # 1. Owner-level overrides
        if hasattr(owner, "payment_config"):  # OwnerPaymentConfig
            oc = owner.payment_config
            for field in [
                "platform_fee_percent",
                "platform_fee_cap",
                "gateway_fee_percent",
                "fixed_extra_fee",
            ]:
                if getattr(oc, field, None) is not None:
                    config[field] = getattr(oc, field)

        # 2. Property fields
        config["pricing_model"] = self.pricing_model
        config["platform_fee_payer"] = self.platform_fee_payer
        config["gateway_fee_payer"] = self.gateway_fee_payer
        config["wallet_fee_payer"] = self.wallet_fee_payer
        config["gateway_methods"] = self.gateway_methods

        # 3. Property fee_overrides (highest priority)
        for k, v in self.fee_overrides.items():
            config[k] = v

        # 4. Apply subscription status (critical!)
        if owner.subscription_status in ["active", "trial"]:
            # If pricing_model == 'subscription', waive fees entirely
            if config.get("pricing_model") == "subscription":
                config["platform_fee_percent"] = 0
                config["gateway_fee_percent"] = 0
                config["fixed_extra_fee"] = 0
            # Else apply discounts from subscription plan
            elif owner.subscription_plan:
                plan = owner.subscription_plan
                if plan.transaction_fee_discount_percent:
                    config["platform_fee_percent"] = max(
                        0,
                        config.get("platform_fee_percent")
                        - plan.transaction_fee_discount_percent,
                    )
                if plan.platform_fee_cap_override is not None:
                    config["platform_fee_cap"] = plan.platform_fee_cap_override
        # If subscription is inactive, always use per‑transaction pricing_model (no fee waiver)
        else:
            config["pricing_model"] = "per_transaction"

        return config


class TermTemplate(TimeStampedUUIDModel):
    """
    Landlord-defined terms template for a property.
    Can be reused across multiple agreements.
    """

    property = models.ForeignKey(
        Property,
        on_delete=models.CASCADE,
        related_name="term_templates",
        verbose_name=_("Property"),
    )
    name = models.CharField(_("Template name"), max_length=255)
    content = models.TextField(_("Terms and conditions content"))
    is_active = models.BooleanField(_("Active"), default=True)

    class Meta:
        verbose_name = _("Term Template")
        verbose_name_plural = _("Term Templates")
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} ({self.property.name})"
