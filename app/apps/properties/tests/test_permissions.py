"""
Tests for Properties app permissions.
Verifies authorization logic for different user roles.
"""

import pytest
from rest_framework.test import APIRequestFactory
from apps.properties.permissions import (
    IsOwnerOrManagerOrSuperAdmin,
    IsTenantOrReadOnly,
    CanManageProperty,
)
from apps.properties.tests.factories import (
    PropertyFactory,
    OwnerFactory,
    ManagerFactory,
    UnitFactory,
)
from apps.users.tests.factories import UserFactory, AdminUserFactory
from apps.tenants.tests.factories import TenantFactory


@pytest.mark.django_db
@pytest.mark.unit
class TestIsOwnerOrManagerOrSuperAdmin:
    """Test suite for IsOwnerOrManagerOrSuperAdmin permission"""

    @pytest.fixture
    def permission(self):
        return IsOwnerOrManagerOrSuperAdmin()

    @pytest.fixture
    def factory(self):
        return APIRequestFactory()

    def test_superuser_has_permission(self, permission, factory):
        """Test superuser always has access"""
        admin = AdminUserFactory.create()
        request = factory.get("/fake-url")
        request.user = admin

        assert permission.has_permission(request, None) is True

    def test_owner_has_object_permission(self, permission, factory):
        """Test owner can access their property"""
        owner = OwnerFactory.create()
        property = PropertyFactory.create(owners=[owner])
        request = factory.get("/fake-url")
        request.user = owner.user

        assert permission.has_object_permission(request, None, property) is True

    def test_manager_has_object_permission(self, permission, factory):
        """Test manager can access managed property"""
        manager = ManagerFactory.create()
        property = PropertyFactory.create()
        property.managers.add(manager)
        request = factory.get("/fake-url")
        request.user = manager.user

        assert permission.has_object_permission(request, None, property) is True

    def test_non_owner_no_object_permission(self, permission, factory):
        """Test non-owner cannot access property"""
        regular_user = UserFactory.create()
        other_owner = OwnerFactory.create()
        property = PropertyFactory.create(owners=[other_owner])
        request = factory.get("/fake-url")
        request.user = regular_user

        assert permission.has_object_permission(request, None, property) is False

    def test_tenant_cannot_access_property(self, permission, factory):
        """Test tenant cannot access property"""
        tenant = TenantFactory.create()
        property = PropertyFactory.create()
        request = factory.get("/fake-url")
        request.user = tenant.user

        assert permission.has_object_permission(request, None, property) is False

    def test_unit_inherits_property_permission(self, permission, factory):
        """Test unit permission checks through property"""
        owner = OwnerFactory.create()
        property = PropertyFactory.create(owners=[owner])
        unit = UnitFactory.create(property=property)
        request = factory.get("/fake-url")
        request.user = owner.user

        assert permission.has_object_permission(request, None, unit) is True


@pytest.mark.django_db
@pytest.mark.unit
class TestIsTenantOrReadOnly:
    """Test suite for IsTenantOrReadOnly permission"""

    @pytest.fixture
    def permission(self):
        return IsTenantOrReadOnly()

    @pytest.fixture
    def factory(self):
        return APIRequestFactory()

    @pytest.mark.parametrize("method", ["GET", "HEAD", "OPTIONS"])
    def test_safe_methods_allowed(self, permission, factory, method):
        """Test read-only methods allowed for any user"""
        user = UserFactory.create()
        request = factory.generic(method, "/fake-url")
        request.user = user

        assert permission.has_permission(request, None) is True

    @pytest.mark.parametrize("method", ["POST", "PUT", "PATCH", "DELETE"])
    def test_write_methods_require_tenant(self, permission, factory, method):
        """Test write methods require tenant profile"""
        regular_user = UserFactory.create()
        request = factory.generic(method, "/fake-url")
        request.user = regular_user

        assert permission.has_permission(request, None) is False


@pytest.mark.django_db
@pytest.mark.unit
class TestCanManageProperty:
    """Test suite for CanManageProperty permission"""

    @pytest.fixture
    def permission(self):
        return CanManageProperty()

    @pytest.fixture
    def factory(self):
        return APIRequestFactory()

    def test_superuser_has_permission(self, permission, factory):
        """Test superuser can manage properties"""
        admin = AdminUserFactory.create()
        request = factory.get("/fake-url")
        request.user = admin

        assert permission.has_permission(request, None) is True

    def test_landlord_has_permission(self, permission, factory):
        """Test landlord can manage properties"""
        landlord = UserFactory.create(role="landlord")
        request = factory.get("/fake-url")
        request.user = landlord

        assert permission.has_permission(request, None) is True

    def test_manager_has_permission(self, permission, factory):
        """Test manager can manage properties"""
        manager = UserFactory.create(role="manager")
        request = factory.get("/fake-url")
        request.user = manager

        assert permission.has_permission(request, None) is True

    def test_tenant_no_permission(self, permission, factory):
        """Test tenant cannot manage properties"""
        tenant = UserFactory.create(role="tenant")
        request = factory.get("/fake-url")
        request.user = tenant

        assert permission.has_permission(request, None) is False

    def test_regular_user_no_permission(self, permission, factory):
        """Test regular user cannot manage properties"""
        regular_user = UserFactory.create(role="user")
        request = factory.get("/fake-url")
        request.user = regular_user

        assert permission.has_permission(request, None) is False
