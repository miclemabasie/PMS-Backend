"""
Factory Boy factories for Properties app models.
Generates realistic test data for Owner, Property, Unit, Manager, etc.
"""

import factory
from decimal import Decimal
from apps.properties.models import (
    Owner,
    Property,
    PropertyImage,
    PropertyOwnership,
    Manager,
    Unit,
    UnitImage,
    PropertyType,
    UnitType,
)
from apps.users.tests.factories import UserFactory
from factory.django import DjangoModelFactory
from factory.faker import Faker
from apps.users.models import Role

# ============================================================
# Owner Factories
# ============================================================


class OwnerFactory(DjangoModelFactory):
    """Creates Owner profile linked to User with landlord role."""

    class Meta:
        model = Owner

    user = factory.SubFactory(UserFactory, role=Role.Owner)
    preferred_payout_method = "bank_transfer"
    mobile_money_number = "+237600000000"
    bank_account_name = Faker("name")
    bank_name = Faker("company")
    bank_account_number = factory.Sequence(lambda n: f"ACC{n:010d}")
    tax_id = factory.Sequence(lambda n: f"NIU{n:015d}")


# ============================================================
# Property Factories
# ============================================================


class PropertyFactory(DjangoModelFactory):
    """
    Creates Property with ownership records.
    Automatically creates primary owner via post_generation hook.
    """

    class Meta:
        model = Property

    name = Faker("company")
    property_type = PropertyType.APARTMENT_BUILDING
    description = Faker("text", max_nb_chars=200)
    address_line1 = Faker("address")
    address_line2 = ""
    city = Faker("city")
    state = ""
    country = "CM"
    postal_code = ""
    has_generator = False
    has_water_tank = True
    amenities = ["parking", "security", "water"]
    status = "active"
    starting_amount = Decimal("50000")
    top_amount = Decimal("500000")
    is_active = True
    language = "en"

    # Create ownership record after property is created
    @factory.post_generation
    def owners(self, create, extracted, **kwargs):
        if not create:
            return
        if extracted:
            for owner in extracted:
                PropertyOwnershipFactory(
                    property=self,
                    owner=owner,
                    percentage=Decimal("100.00"),
                    is_primary=True,
                )
        else:
            # Default: create one primary owner
            owner = OwnerFactory.create()
            PropertyOwnershipFactory(
                property=self,
                owner=owner,
                percentage=Decimal("100.00"),
                is_primary=True,
            )


class PropertyOwnershipFactory(DjangoModelFactory):
    """Creates PropertyOwnership (through model for Property ↔ Owner)."""

    class Meta:
        model = PropertyOwnership

    property = factory.SubFactory(PropertyFactory)
    owner = factory.SubFactory(OwnerFactory)
    percentage = Decimal("100.00")
    is_primary = True


class PropertyImageFactory(DjangoModelFactory):
    """Creates PropertyImage."""

    class Meta:
        model = PropertyImage

    property = factory.SubFactory(PropertyFactory)
    alt_text = Faker("sentence")
    is_primary = False
    # image = factory.django.ImageField()  # Uncomment if testing file uploads


# ============================================================
# Manager Factories
# ============================================================


class ManagerFactory(DjangoModelFactory):
    """Creates Manager profile linked to User."""

    class Meta:
        model = Manager

    user = factory.SubFactory(UserFactory, role="manager")
    commission_rate = Decimal("5.00")
    is_active = True

    @factory.post_generation
    def managed_properties(self, create, extracted, **kwargs):
        if not create:
            return
        if extracted:
            self.managed_properties.set(extracted)


# ============================================================
# Unit Factories
# ============================================================


class UnitFactory(DjangoModelFactory):
    """Creates Unit within a Property."""

    class Meta:
        model = Unit

    property = factory.SubFactory(PropertyFactory)
    unit_number = factory.Sequence(lambda n: f"Apt-{n:03d}")
    unit_type = UnitType.ONE_BED
    floor = 1
    size_m2 = 50
    bedrooms = 1
    bathrooms = 1
    default_rent_amount = Decimal("75000")
    default_security_deposit = Decimal("150000")
    status = "vacant"
    amenities = ["ac", "balcony"]
    water_meter_number = factory.Sequence(lambda n: f"WTR{n:010d}")
    electricity_meter_number = factory.Sequence(lambda n: f"ELEC{n:010d}")
    has_prepaid_meter = False
    language = "en"


class UnitImageFactory(DjangoModelFactory):
    """Creates UnitImage."""

    class Meta:
        model = UnitImage

    unit = factory.SubFactory(UnitFactory)
    alt_text = Faker("sentence")
    is_primary = False
    # image = factory.django.ImageField()  # Uncomment if testing file uploads
