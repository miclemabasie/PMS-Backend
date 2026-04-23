"""
Tests for Properties app services.
Verifies business logic, transactions, and cross-repository operations.
"""

import pytest
from decimal import Decimal
from apps.properties.services import (
    OwnerService,
    ManagerService,
    PropertyService,
    UnitService,
    PropertyOwnershipService,
)
from apps.properties.tests.factories import (
    OwnerFactory,
    ManagerFactory,
    PropertyFactory,
    UnitFactory,
    PropertyOwnershipFactory,
)
from apps.users.tests.factories import UserFactory, AdminUserFactory


@pytest.mark.integration
class TestOwnerService:
    """Test suite for OwnerService"""

    @pytest.fixture
    def service(self):
        return OwnerService()

    def test_create_owner_sets_user_role(self, db, service):
        """Test creating owner sets user role to landlord"""
        user = UserFactory.create(role="user")

        owner = service.create(user=user)

        user.refresh_from_db()
        assert user.role == "landlord"

    def test_get_or_create_for_user_exists(self, db, service):
        """Test get_or_create returns existing owner"""
        owner = OwnerFactory.create()

        result = service.get_or_create_for_user(owner.user)

        assert result.pkid == owner.pkid

    def test_get_or_create_for_user_creates(self, db, service):
        """Test get_or_create creates new owner if not exists"""
        user = UserFactory.create(role="user")

        result = service.get_or_create_for_user(user)

        assert result is not None
        assert result.user == user
        user.refresh_from_db()
        assert user.role == "landlord"


@pytest.mark.integration
class TestManagerService:
    """Test suite for ManagerService"""

    @pytest.fixture
    def service(self):
        return ManagerService()

    def test_get_or_create_for_user(self, db, service):
        """Test get_or_create for manager"""
        user = UserFactory.create(role="user")

        result = service.get_or_create_for_user(user)

        assert result is not None
        assert result.user == user

    def test_get_all_for_user_superuser(self, db, service):
        """Test superuser can get all managers"""
        admin = AdminUserFactory.create()
        ManagerFactory.create_batch(3)

        results = service.get_all_for_user(admin)

        assert results.count() >= 3

    def test_get_all_for_user_owner(self, db, service):
        """Test owner can get managers of their properties"""
        owner = OwnerFactory.create()
        property = PropertyFactory.create(owners=[owner])
        manager = ManagerFactory.create()
        property.managers.add(manager)

        results = service.get_all_for_user(owner.user)

        assert results.count() >= 1


@pytest.mark.integration
class TestPropertyService:
    """Test suite for PropertyService"""

    @pytest.fixture
    def service(self):
        return PropertyService()

    def test_create_property_creates_ownership(self, db, service):
        """Test creating property creates ownership record"""
        owner = OwnerFactory.create()
        data = {
            "name": "Test Property",
            "city": "Yaounde",
            "property_type": "villa",
            "description": "Test",
            "address_line1": "Street 1",
            "country": "CM",
            "starting_amount": Decimal("100000"),
            "top_amount": Decimal("500000"),
        }

        property = service.create_property(data=data, owner=owner)

        assert property.name == "Test Property"
        assert property.ownership_records.filter(owner=owner).exists()
        assert property.ownership_records.get(owner=owner).percentage == Decimal(
            "100.00"
        )

    def test_get_properties_for_user_superuser(self, db, service):
        """Test superuser can get all properties"""
        admin = AdminUserFactory.create()
        PropertyFactory.create_batch(5)

        results = service.get_properties_for_user(admin)

        assert len(results) >= 5

    def test_get_properties_for_user_owner(self, db, service):
        """Test owner can get their properties"""
        owner = OwnerFactory.create()
        PropertyFactory.create_batch(3, owners=[owner])
        PropertyFactory.create()  # Different owner

        results = service.get_properties_for_user(owner.user)

        assert len(results) == 3

    def test_add_managers_to_property(self, db, service):
        """Test adding managers to property"""
        property = PropertyFactory.create()
        manager1 = ManagerFactory.create()
        manager2 = ManagerFactory.create()

        updated = service.add_managers(
            str(property.id), [str(manager1.pkid), str(manager2.pkid)]
        )

        assert updated.managers.count() == 2

    def test_remove_managers_from_property(self, db, service):
        """Test removing managers from property"""
        property = PropertyFactory.create()
        manager = ManagerFactory.create()
        property.managers.add(manager)

        updated = service.remove_managers(str(property.id), [str(manager.pkid)])

        assert updated.managers.count() == 0

    def test_replace_managers(self, db, service):
        """Test replacing all managers"""
        property = PropertyFactory.create()
        manager1 = ManagerFactory.create()
        manager2 = ManagerFactory.create()
        property.managers.add(manager1)

        updated = service.replace_managers(str(property.id), [str(manager2.pkid)])

        assert updated.managers.count() == 1
        assert updated.managers.first() == manager2

    def test_update_property(self, db, service):
        """Test updating property"""
        property = PropertyFactory.create(name="Original")

        updated = service.update_property(str(property.id), {"name": "Updated"})

        assert updated.name == "Updated"


@pytest.mark.integration
class TestUnitService:
    """Test suite for UnitService"""

    @pytest.fixture
    def service(self):
        return UnitService()

    def test_create_unit(self, db, service):
        """Test creating unit"""
        property = PropertyFactory.create()
        data = {
            "property": property,
            "unit_number": "Apt-100",
            "default_rent_amount": Decimal("75000"),
        }

        unit = service.repository.create(**data)

        assert unit.unit_number == "Apt-100"
        assert unit.property == property

    def test_get_units_for_property(self, db, service):
        """Test getting units for property"""
        property = PropertyFactory.create()
        UnitFactory.create_batch(4, property=property)

        results = service.get_units_for_property(property.pkid)

        assert len(results) == 4

    def test_get_available_units(self, db, service):
        """Test getting available (vacant) units"""
        property = PropertyFactory.create()
        UnitFactory.create(property=property, status="vacant")
        UnitFactory.create(property=property, status="occupied")
        UnitFactory.create(property=property, status="vacant")

        results = service.get_available_units()

        assert len(results) == 2

    def test_update_unit_status(self, db, service):
        """Test updating unit status"""
        unit = UnitFactory.create(status="vacant")

        updated = service.update_unit_status(unit.id, "occupied")

        assert updated.status == "occupied"

    def test_get_units_for_user_owner(self, db, service):
        """Test getting units for owner"""
        owner = OwnerFactory.create()
        property = PropertyFactory.create(owners=[owner])
        UnitFactory.create_batch(3, property=property)

        results = service.get_units_for_user(owner.user)

        assert results.count() == 3
