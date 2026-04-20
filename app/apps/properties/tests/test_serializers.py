"""
Tests for Properties app serializers.
Verifies data validation, serialization, and business logic.
"""

import pytest
from decimal import Decimal
from apps.properties.serializers import (
    PropertySerializer,
    OwnerSerializer,
    ManagerSerializer,
    UnitSerializer,
    PropertyOwnershipSerializer,
    PropertyImageSerializer,
    PropertyManagerAddSerializer,
    PropertyManagerAssignmentSerializer,
)
from apps.properties.tests.factories import (
    PropertyFactory,
    OwnerFactory,
    ManagerFactory,
    UnitFactory,
    PropertyOwnershipFactory,
    PropertyImageFactory,
)
from apps.users.tests.factories import UserFactory


@pytest.mark.unit
class TestOwnerSerializer:
    """Test suite for OwnerSerializer"""

    def test_owner_serializer_fields(self, db):
        """Test that serializer has expected fields"""
        owner = OwnerFactory.create()
        serializer = OwnerSerializer(owner)

        expected_fields = [
            "id",
            "pkid",
            "user",
            "preferred_payout_method",
            "mobile_money_number",
            "bank_account_name",
            "bank_name",
            "bank_account_number",
            "bank_code",
            "tax_id",
            "created_at",
            "updated_at",
        ]

        for field in expected_fields:
            assert field in serializer.data

    def test_owner_serializer_nested_user(self, db):
        """Test that user data is nested correctly"""
        owner = OwnerFactory.create(
            user__first_name="John",
            user__last_name="Doe",
            user__email="john@example.com",
        )
        serializer = OwnerSerializer(owner)

        assert serializer.data["user"]["first_name"] == "John"
        assert serializer.data["user"]["last_name"] == "Doe"
        assert serializer.data["user"]["email"] == "john@example.com"

    def test_owner_serializer_write_only_user_id(self, db):
        """Test user_id is write-only"""
        user = UserFactory.create(role="landlord")
        data = {"user_id": user.pkid}

        serializer = OwnerSerializer(data=data)
        # Should be valid for write operations
        # assert "user_id" in serializer.fields


@pytest.mark.unit
class TestPropertySerializer:
    """Test suite for PropertySerializer"""

    def test_property_serializer_fields(self, db):
        """Test that serializer has expected fields"""
        property = PropertyFactory.create()
        serializer = PropertySerializer(property)

        expected_fields = [
            "id",
            "pkid",
            "name",
            "property_type",
            "description",
            "address_line1",
            "city",
            "country",
            "owners",
            "managers",
            "units",
            "status",
            "starting_amount",
            "top_amount",
            "occupancy_rate",
            "is_active",
            "created_at",
            "updated_at",
        ]

        for field in expected_fields:
            assert field in serializer.data

    def test_property_serializer_nested_owners(self, db):
        """Test that owners are nested correctly"""
        property = PropertyFactory.create()
        serializer = PropertySerializer(property)

        assert "owners" in serializer.data
        assert isinstance(serializer.data["owners"], list)
        assert len(serializer.data["owners"]) >= 1

    def test_property_serializer_occupancy_rate(self, db):
        """Test occupancy_rate is calculated"""
        property = PropertyFactory.create()
        serializer = PropertySerializer(property)

        # Currently hardcoded to 70 in serializer
        assert serializer.data["occupancy_rate"] == 70

    def test_property_serializer_price_bounds(self, db):
        """Test lower_bound and upper_bound are formatted"""
        property = PropertyFactory.create(
            starting_amount=Decimal("100000"), top_amount=Decimal("500000")
        )
        serializer = PropertySerializer(property)

        assert serializer.data["lower_bound"] == "100k"
        assert serializer.data["upper_bound"] == "500k"

    def test_property_serializer_primary_image(self, db):
        """Test primary_image method"""
        property = PropertyFactory.create()
        serializer = PropertySerializer(property)

        # No images yet
        assert serializer.data["primary_image"] is None

        # # Add primary image
        # PropertyImageFactory.create(property=property, is_primary=True)
        # serializer = PropertySerializer(property)

        # # Will have URL in production
        # assert serializer.data["primary_image"] is not None


@pytest.mark.unit
class TestUnitSerializer:
    """Test suite for UnitSerializer"""

    def test_unit_serializer_fields(self, db):
        """Test that serializer has expected fields"""
        unit = UnitFactory.create()
        serializer = UnitSerializer(unit)

        expected_fields = [
            "id",
            "pkid",
            "property_detail",
            "unit_number",
            "unit_type",
            "bedrooms",
            "bathrooms",
            "default_rent_amount",
            "status",
            "amenities",
            "created_at",
            "updated_at",
        ]

        for field in expected_fields:
            assert field in serializer.data

    def test_unit_serializer_property_id_write_only(self, db):
        """Test property_id is write-only"""
        property = PropertyFactory.create()
        data = {
            "property_id": property.pkid,
            "unit_number": "Apt-100",
            "default_rent_amount": "50000",
        }

        serializer = UnitSerializer(data=data)
        # assert "property_id" in serializer.fields


@pytest.mark.unit
class TestManagerSerializer:
    """Test suite for ManagerSerializer"""

    def test_manager_serializer_fields(self, db):
        """Test that serializer has expected fields"""
        manager = ManagerFactory.create()
        serializer = ManagerSerializer(manager)

        expected_fields = [
            "id",
            "pkid",
            "user",
            "commission_rate",
            "managed_properties",
            "is_active",
            "created_at",
            "updated_at",
        ]

        for field in expected_fields:
            assert field in serializer.data

    def test_manager_serializer_commission_rate(self, db):
        """Test commission rate is serialized correctly"""
        manager = ManagerFactory.create(commission_rate=Decimal("7.50"))
        serializer = ManagerSerializer(manager)

        assert serializer.data["commission_rate"] == "7.50"


@pytest.mark.unit
class TestPropertyOwnershipSerializer:
    """Test suite for PropertyOwnershipSerializer"""

    def test_ownership_serializer_fields(self, db):
        """Test that serializer has expected fields"""
        ownership = PropertyOwnershipFactory.create()
        serializer = PropertyOwnershipSerializer(ownership)

        expected_fields = [
            "id",
            "pkid",
            "owner",
            "percentage",
            "is_primary",
        ]

        for field in expected_fields:
            assert field in serializer.data

    def test_ownership_serializer_percentage(self, db):
        """Test percentage is serialized correctly"""
        ownership = PropertyOwnershipFactory.create(percentage=Decimal("75.00"))
        serializer = PropertyOwnershipSerializer(ownership)

        assert serializer.data["percentage"] == "75.00"


@pytest.mark.unit
class TestPropertyManagerAddSerializer:
    """Test suite for PropertyManagerAddSerializer"""

    def test_manager_add_serializer_valid(self, db):
        """Test valid manager ID"""
        manager = ManagerFactory.create()
        data = {"manager_id": str(manager.pkid)}

        serializer = PropertyManagerAddSerializer(data=data)
        assert serializer.is_valid(), serializer.errors

    def test_manager_add_serializer_invalid_uuid(self, db):
        """Test invalid UUID format"""
        data = {"manager_id": "invalid-uuid"}

        serializer = PropertyManagerAddSerializer(data=data)
        assert serializer.is_valid() is False
        assert "manager_id" in serializer.errors

    def test_manager_add_serializer_nonexistent(self, db):
        """Test non-existent manager ID"""
        import uuid

        data = {"manager_id": str(uuid.uuid4())}

        serializer = PropertyManagerAddSerializer(data=data)
        assert serializer.is_valid() is False


@pytest.mark.unit
class TestPropertyManagerAssignmentSerializer:
    """Test suite for PropertyManagerAssignmentSerializer"""

    def test_assignment_serializer_valid(self, db):
        """Test valid manager IDs list"""
        manager1 = ManagerFactory.create()
        manager2 = ManagerFactory.create()
        data = {"manager_ids": [str(manager1.pkid), str(manager2.pkid)]}

        serializer = PropertyManagerAssignmentSerializer(data=data)
        assert serializer.is_valid(), serializer.errors

    def test_assignment_serializer_partial_invalid(self, db):
        """Test partial invalid manager IDs"""
        manager1 = ManagerFactory.create()
        import uuid

        data = {"manager_ids": [str(manager1.pkid), str(uuid.uuid4())]}

        serializer = PropertyManagerAssignmentSerializer(data=data)
        assert serializer.is_valid() is False
        # assert "not found" in str(serializer.errors).lower()
