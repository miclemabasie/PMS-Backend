from django.db import models
from apps.core.models import TimeStampedUUIDModel
from django_countries.fields import CountryField
from django.utils.translation import gettext_lazy as _
from apps.users.models import User
from phonenumber_field.modelfields import PhoneNumberField
from model_utils import FieldTracker


# Create your models here.


class PropertyType(models.TextChoices):
    APARTMENT = "apartment", _("Apartment building")
    HOUSE = "house", _("Single family house")
    COMMERCIAL = "commercial", _("Commercial (shop/office)")
    LAND = "land", _("Land")
    HOSTEL = "hostel", _("Hostel")
    OTHER = "other", _("Other")


class PaymentMethod(models.TextChoices):
    MTN_MOMO = "mtn_momo", _("MTN MoMo")
    ORANGE_MONEY = "orange_money", _("Orange Money")
    BANK_TRANSFER = "bank_transfer", _("Bank transfer")
    CASH = "cash", _("Cash")
    OTHER = "other", _("Other")


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
    postal_code = models.CharField(_("Postal code"), max_length=20, blank=True)
    # Cameroon specifics
    has_generator = models.BooleanField(_("Has generator"), default=False)
    has_water_tank = models.BooleanField(_("Has water tank"), default=False)
    amenities = models.JSONField(
        _("Amenities"), default=list, blank=True
    )  # list of strings
    images = models.JSONField(_("Image URLs"), default=list, blank=True)
    owners = models.ManyToManyField(
        Owner,
        through="PropertyOwnership",
        related_name="properties",
        verbose_name=_("Owners"),
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

    def __str__(self):
        return self.name
