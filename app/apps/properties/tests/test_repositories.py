"""
Tests for Properties app repositories.
Verifies data access layer, query optimization, and filtering.
"""

import pytest
from apps.properties.repositories import (
    OwnerRepository,
    ManagerRepository,
    PropertyRepository,
    PropertyOwnershipRepository,
    UnitRepository,
)
from apps.properties.tests.factories import (
    OwnerFactory,
    ManagerFactory,
    PropertyFactory,
    PropertyOwnershipFactory,
    UnitFactory,
)
from apps.users.tests.factories import UserFactory, AdminUserFactory


@pytest.mark.unit
class TestOwnerRepository:
    """Test suite for OwnerRepository"""

    @pytest.fixture
    def repository(self):
        return OwnerRepository()

    def test_get_owner_by_id(self, db, repository):
        """Test retrieving owner by ID"""
        owner = OwnerFactory.create()

        result = repository.get(owner.id)

        assert result is not None
        assert result.pkid == owner.pkid

    def test_filter_owners(self, db, repository):
        """Test filtering owners"""
        OwnerFactory.create_batch(3)

        results = repository.filter()

        assert len(results) >= 3


@pytest.mark.unit
class TestPropertyRepository:
    """Test suite for PropertyRepository"""

    @pytest.fixture
    def repository(self):
        return PropertyRepository()

    def test_find_by_owner(self, db, repository):
        """Test finding properties by owner"""
        owner = OwnerFactory.create()
        PropertyFactory.create_batch(3, owners=[owner])
        PropertyFactory.create()  # Different owner

        results = repository.find_by_owner(owner.pkid)

        assert results.count() == 3

    def test_find_by_manager(self, db, repository):
        """Test finding properties by manager"""
        manager = ManagerFactory.create()
        property1 = PropertyFactory.create()
        property2 = PropertyFactory.create()
        property1.managers.add(manager)
        property2.managers.add(manager)
        results = repository.find_by_manager(manager.id)

        assert results.count() == 2

    def test_get_property_by_id(self, db, repository):
        """Test retrieving property by ID"""
        property = PropertyFactory.create()

        result = repository.get(property.id)

        assert result is not None
        assert result.pkid == property.pkid


@pytest.mark.unit
class TestUnitRepository:
    """Test suite for UnitRepository"""

    @pytest.fixture
    def repository(self):
        return UnitRepository()

    def test_find_by_property(self, db, repository):
        """Test finding units by property"""
        property = PropertyFactory.create()
        UnitFactory.create_batch(5, property=property)

        results = repository.find_by_property(property.pkid)

        assert results.count() == 5

    def test_find_by_user_owner(self, db, repository):
        """Test finding units for owner user"""
        owner = OwnerFactory.create()
        property = PropertyFactory.create(owners=[owner])
        UnitFactory.create_batch(3, property=property)

        results = repository.find_by_user(owner.user)

        assert results.count() == 3

    def test_find_by_user_manager(self, db, repository):
        """Test finding units for manager user"""
        manager = ManagerFactory.create()
        property = PropertyFactory.create()
        property.managers.add(manager)
        UnitFactory.create_batch(2, property=property)

        results = repository.find_by_user(manager.user)

        assert results.count() == 2

    def test_find_by_user_no_access(self, db, repository):
        """Test finding units for user with no access"""
        regular_user = UserFactory.create(role="user")
        PropertyFactory.create()

        results = repository.find_by_user(regular_user)

        assert results.count() == 0

    def test_find_by_user_superuser(self, db, repository):
        """Test finding units for superuser"""
        admin = AdminUserFactory.create()
        UnitFactory.create_batch(5)

        results = repository.find_by_user(admin)

        assert results.count() >= 5


@pytest.mark.unit
class TestManagerRepository:
    """Test suite for ManagerRepository"""

    @pytest.fixture
    def repository(self):
        return ManagerRepository()

    def test_get_queryset_for_user_superuser(self, db, repository):
        """Test superuser can see all managers"""
        admin = AdminUserFactory.create()
        ManagerFactory.create_batch(3)

        results = repository.get_queryset_for_user(admin)

        assert results.count() >= 3

    def test_get_queryset_for_user_owner(self, db, repository):
        """Test owner can see managers of their properties"""
        owner = OwnerFactory.create()
        property = PropertyFactory.create(owners=[owner])
        manager = ManagerFactory.create()
        property.managers.add(manager)

        results = repository.get_queryset_for_user(owner.user)

        assert results.count() >= 1

    def test_get_queryset_for_user_manager(self, db, repository):
        """Test manager can see only themselves"""
        manager = ManagerFactory.create()

        results = repository.get_queryset_for_user(manager.user)

        assert results.count() == 1
        assert results.first().pkid == manager.pkid


@pytest.mark.unit
class TestPropertyOwnershipRepository:
    """Test suite for PropertyOwnershipRepository"""

    @pytest.fixture
    def repository(self):
        return PropertyOwnershipRepository()

    def test_create_ownership(self, db, repository):
        """Test creating ownership record"""
        property = PropertyFactory.create()
        owner = OwnerFactory.create()

        ownership = repository.create(property=property, owner=owner, percentage=50.00)

        assert ownership.property == property
        assert ownership.owner == owner
        assert ownership.percentage == 50.00
