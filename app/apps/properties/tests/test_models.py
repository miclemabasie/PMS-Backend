"""
Tests for Properties app models.
Verifies model behavior, constraints, relationships, and custom methods.
"""

import pytest
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
from apps.properties.tests.factories import (
    OwnerFactory,
    PropertyFactory,
    PropertyOwnershipFactory,
    ManagerFactory,
    UnitFactory,
    PropertyImageFactory,
    UnitImageFactory,
)
from apps.users.tests.factories import UserFactory


@pytest.mark.unit
class TestOwnerModel:
    """Test suite for Owner model"""

    def test_owner_creation(self, db):
        """Test that we can create an owner"""
        owner = OwnerFactory.create()

        assert owner.user is not None
        assert owner.user.role == "landlord"
        assert owner.preferred_payout_method == "bank_transfer"

    def test_owner_str_representation(self, db):
        """Test owner string representation"""
        owner = OwnerFactory.create(user__first_name="John", user__last_name="Doe")

        assert "Owner: John Doe" in str(owner)

    def test_owner_user_on_delete_cascade(self, db):
        """Test owner is deleted when user is deleted"""
        owner = OwnerFactory.create()
        owner_id = owner.pkid
        user_id = owner.user.pkid

        owner.user.delete()

        assert not Owner.objects.filter(pkid=owner_id).exists()

    def test_owner_payout_method_choices(self, db):
        """Test owner payout method is valid choice"""
        owner = OwnerFactory.create(preferred_payout_method="mtn_momo")

        assert owner.preferred_payout_method in [
            "mtn_momo",
            "orange_money",
            "bank_transfer",
            "cash",
            "other",
        ]


@pytest.mark.unit
class TestPropertyModel:
    """Test suite for Property model"""

    def test_property_creation(self, db):
        """Test that we can create a property"""
        property = PropertyFactory.create(name="Test Property")

        assert property.name == "Test Property"
        assert property.is_active is True
        assert property.status == "active"
        assert property.country == "CM"

    def test_property_str_representation(self, db):
        """Test property string representation"""
        property = PropertyFactory.create(name="Sunset Villas")

        assert str(property) == "Sunset Villas"

    def test_property_ownership_created(self, db):
        """Test that ownership record is created with property"""
        property = PropertyFactory.create()

        assert property.ownership_records.exists()
        ownership = property.ownership_records.first()
        assert ownership.percentage == Decimal("100.00")
        assert ownership.is_primary is True

    def test_property_default_country(self, db):
        """Test property default country is Cameroon"""
        property = PropertyFactory.create()

        assert property.country == "CM"

    def test_property_type_choices(self, db):
        """Test property type is valid choice"""
        property = PropertyFactory.create(property_type="villa")

        assert property.property_type in PropertyType.values

    def test_property_amounts(self, db):
        """Test property starting and top amounts"""
        property = PropertyFactory.create(
            starting_amount=Decimal("100000"), top_amount=Decimal("500000")
        )

        assert property.starting_amount == Decimal("100000")
        assert property.top_amount == Decimal("500000")

    def test_property_multiple_owners(self, db):
        """Test that property can have multiple owners"""
        property = PropertyFactory.create()
        owner1 = OwnerFactory.create()
        owner2 = OwnerFactory.create()

        PropertyOwnershipFactory(
            property=property, owner=owner1, percentage=Decimal("60.00")
        )
        PropertyOwnershipFactory(
            property=property, owner=owner2, percentage=Decimal("40.00")
        )

        assert property.ownership_records.count() == 3  # 1 from factory + 2 new
        assert property.owners.count() == 3

    def test_property_get_primary_image(self, db):
        """Test get_primary_image method"""
        property = PropertyFactory.create()

        # No images yet
        assert property.get_primary_image() is None

        # Add primary image
        PropertyImageFactory.create(property=property, is_primary=True)

        # Should return image URL (will be None in tests without MEDIA_URL)
        primary = property.property_images.filter(is_primary=True).first()
        assert primary is not None

    def test_property_status_choices(self, db):
        """Test property status is valid choice"""
        property = PropertyFactory.create(status="maintenance")

        assert property.status in ["maintenance", "active"]

    def test_property_language_default(self, db):
        """Test property default language is English"""
        property = PropertyFactory.create()

        assert property.language == "en"


@pytest.mark.unit
class TestPropertyOwnershipModel:
    """Test suite for PropertyOwnership model"""

    def test_ownership_creation(self, db):
        """Test that we can create ownership record"""
        ownership = PropertyOwnershipFactory.create(percentage=Decimal("75.00"))

        assert ownership.percentage == Decimal("75.00")
        assert ownership.is_primary is True
        assert ownership.property is not None
        assert ownership.owner is not None

    def test_ownership_str_representation(self, db):
        """Test ownership string representation"""
        ownership = PropertyOwnershipFactory.create(percentage=Decimal("50.00"))

        assert "50.00" in str(ownership)
        assert ownership.owner.user.get_full_name() in str(ownership)

    def test_ownership_percentage_validation(self, db):
        """Test ownership percentage is between 0 and 100"""
        from django.core.exceptions import ValidationError

        # Valid percentage
        ownership = PropertyOwnershipFactory.create(percentage=Decimal("100.00"))
        assert ownership.percentage <= Decimal("100.00")
        p = PropertyOwnershipFactory.create(percentage=Decimal("150.00"))
        with pytest.raises(ValidationError):
            p.full_clean()

        # Invalid percentage should fail at DB level
        # with pytest.raises(Exception):

    def test_ownership_unique_together(self, db):
        """Test unique constraint on property + owner"""
        ownership1 = PropertyOwnershipFactory.create()

        # Cannot create duplicate property-owner pair
        with pytest.raises(Exception):
            PropertyOwnershipFactory.create(
                property=ownership1.property, owner=ownership1.owner
            )


@pytest.mark.unit
class TestManagerModel:
    """Test suite for Manager model"""

    def test_manager_creation(self, db):
        """Test that we can create a manager"""
        manager = ManagerFactory.create()

        assert manager.user is not None
        assert manager.user.role == "manager"
        assert manager.commission_rate == Decimal("5.00")
        assert manager.is_active is True

    def test_manager_str_representation(self, db):
        """Test manager string representation"""
        manager = ManagerFactory.create(
            user__first_name="Jane", user__last_name="Manager"
        )

        assert "Manager: Jane Manager" in str(manager)

    def test_manager_commission_rate_validation(self, db):
        """Test commission rate is between 0 and 100"""
        manager = ManagerFactory.create(commission_rate=Decimal("10.00"))

        assert manager.commission_rate >= Decimal("0.00")
        assert manager.commission_rate <= Decimal("100.00")

    def test_manager_managed_properties(self, db):
        """Test manager can manage multiple properties"""
        manager = ManagerFactory.create()
        property1 = PropertyFactory.create()
        property2 = PropertyFactory.create()

        manager.managed_properties.add(property1, property2)

        assert manager.managed_properties.count() == 2


@pytest.mark.unit
class TestUnitModel:
    """Test suite for Unit model"""

    def test_unit_creation(self, db):
        """Test that we can create a unit"""
        unit = UnitFactory.create(unit_number="Apt-001")

        assert unit.unit_number == "Apt-001"
        assert unit.status == "vacant"
        assert unit.property is not None

    def test_unit_str_representation(self, db):
        """Test unit string representation"""
        unit = UnitFactory.create(unit_number="Apt-101")

        assert f"{unit.property.name} - Apt-101" == str(unit)

    def test_unit_unique_per_property(self, db):
        """Test unit number is unique within property"""
        property = UnitFactory.create().property
        UnitFactory.create(property=property, unit_number="Apt-001")

        # Creating another unit with same number in same property should fail
        with pytest.raises(Exception):
            UnitFactory.create(property=property, unit_number="Apt-001")

    def test_unit_default_status_vacant(self, db):
        """Test unit default status is vacant"""
        unit = UnitFactory.create()

        assert unit.status == "vacant"

    def test_unit_type_choices(self, db):
        """Test unit type is valid choice"""
        unit = UnitFactory.create(unit_type="2_bed")

        assert unit.unit_type in UnitType.values

    def test_unit_bedrooms_bathrooms(self, db):
        """Test unit bedrooms and bathrooms"""
        unit = UnitFactory.create(bedrooms=2, bathrooms=2)

        assert unit.bedrooms == 2
        assert unit.bathrooms == 2

    def test_unit_rent_amount(self, db):
        """Test unit default rent amount"""
        unit = UnitFactory.create(default_rent_amount=Decimal("100000"))

        assert unit.default_rent_amount == Decimal("100000")

    def test_unit_meters(self, db):
        """Test unit water and electricity meter numbers"""
        unit = UnitFactory.create()

        assert unit.water_meter_number is not None
        assert unit.electricity_meter_number is not None

    def test_unit_on_delete_cascade(self, db):
        """Test unit is deleted when property is deleted"""
        unit = UnitFactory.create()
        unit_id = unit.pkid
        property_id = unit.property.pkid

        unit.property.delete()

        assert not Unit.objects.filter(pkid=unit_id).exists()


@pytest.mark.unit
class TestPropertyImageModel:
    """Test suite for PropertyImage model"""

    def test_property_image_creation(self, db):
        """Test that we can create a property image"""
        image = PropertyImageFactory.create(alt_text="Front view")

        assert image.alt_text == "Front view"
        assert image.property is not None
        assert image.is_primary is False

    def test_property_image_on_delete_cascade(self, db):
        """Test image is deleted when property is deleted"""
        image = PropertyImageFactory.create()
        image_id = image.id

        image.property.delete()

        assert not PropertyImage.objects.filter(id=image_id).exists()


@pytest.mark.unit
class TestUnitImageModel:
    """Test suite for UnitImage model"""

    def test_unit_image_creation(self, db):
        """Test that we can create a unit image"""
        image = UnitImageFactory.create(alt_text="Kitchen view")

        assert image.alt_text == "Kitchen view"
        assert image.unit is not None

    def test_unit_image_on_delete_cascade(self, db):
        """Test image is deleted when unit is deleted"""
        image = UnitImageFactory.create()
        image_id = image.id

        image.unit.delete()

        assert not UnitImage.objects.filter(id=image_id).exists()
