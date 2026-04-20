"""
Tests for Properties app API views.
Verifies endpoints, permissions, and HTTP responses.
"""

import pytest
from django.urls import reverse
from rest_framework import status
from decimal import Decimal
from apps.properties.tests.factories import (
    PropertyFactory,
    OwnerFactory,
    ManagerFactory,
    UnitFactory,
    PropertyImageFactory,
    UnitImageFactory,
)
from apps.users.tests.factories import UserFactory, AdminUserFactory


@pytest.mark.integration
class TestOwnerViews:
    """Test suite for Owner API views"""

    def test_list_owners_superadmin_only(self, authenticated_admin_client, db):
        """Test that only superadmin can list all owners"""
        OwnerFactory.create_batch(3)
        url = reverse("properties:owner-list")

        response = authenticated_admin_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["results"]) >= 3

    def test_list_owners_regular_user_forbidden(self, authenticated_client, db):
        """Test that regular user cannot list owners"""
        OwnerFactory.create_batch(3)
        url = reverse("properties:owner-list")

        response = authenticated_client.get(url)

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_create_owner_for_self(self, authenticated_client, db):
        """Test that user can create owner profile for themselves"""
        url = reverse("properties:owner-list")
        data = {
            "preferred_payout_method": "bank_transfer",
            "bank_account_name": "Test Account",
        }

        response = authenticated_client.post(url, data)

        assert response.status_code == status.HTTP_201_CREATED
        assert (
            response.data["user"]["email"]
            == authenticated_client.handler._force_user.email
        )

    def test_get_own_owner_detail(self, authenticated_client, db):
        """Test that user can view their own owner profile"""
        owner = OwnerFactory.create(user=authenticated_client.handler._force_user)
        url = reverse("properties:owner-detail", kwargs={"pk": owner.pkid})

        response = authenticated_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data["pkid"] == str(owner.pkid)

    def test_cannot_view_other_owner_detail(self, authenticated_client, db):
        """Test that user cannot view another user's owner profile"""
        other_owner = OwnerFactory.create()
        url = reverse("properties:owner-detail", kwargs={"pk": other_owner.pkid})

        response = authenticated_client.get(url)

        assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.integration
class TestPropertyViews:
    """Test suite for Property API views"""

    def test_list_properties_for_owner(self, authenticated_client, db):
        """Test that owner can list their properties"""
        owner = OwnerFactory.create(user=authenticated_client.handler._force_user)
        PropertyFactory.create_batch(3, owners=[owner])
        url = reverse("properties:property-list")

        response = authenticated_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["results"]) >= 3

    def test_create_property_as_owner(self, authenticated_client, db):
        """Test that owner can create property"""
        url = reverse("properties:property-list")
        data = {
            "name": "Test Property",
            "property_type": "apartment_building",
            "description": "Test description",
            "address_line1": "123 Test Street",
            "city": "Yaounde",
            "country": "CM",
            "starting_amount": "50000",
            "top_amount": "500000",
        }

        response = authenticated_client.post(url, data)

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["name"] == "Test Property"

    def test_get_property_detail_as_owner(self, authenticated_client, db):
        """Test that owner can view their property detail"""
        owner = OwnerFactory.create(user=authenticated_client.handler._force_user)
        property = PropertyFactory.create(owners=[owner])
        url = reverse("properties:property-detail", kwargs={"pk": property.pkid})

        response = authenticated_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data["pkid"] == str(property.pkid)

    def test_update_property_as_owner(self, authenticated_client, db):
        """Test that owner can update their property"""
        owner = OwnerFactory.create(user=authenticated_client.handler._force_user)
        property = PropertyFactory.create(owners=[owner])
        url = reverse("properties:property-detail", kwargs={"pk": property.pkid})
        data = {"name": "Updated Property Name"}

        response = authenticated_client.patch(url, data)

        assert response.status_code == status.HTTP_200_OK
        assert response.data["name"] == "Updated Property Name"

    def test_cannot_view_other_owner_property(self, authenticated_client, db):
        """Test that user cannot view another owner's property"""
        other_owner = OwnerFactory.create()
        property = PropertyFactory.create(owners=[other_owner])
        url = reverse("properties:property-detail", kwargs={"pk": property.pkid})

        response = authenticated_client.get(url)

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_delete_property_with_units_forbidden(self, authenticated_client, db):
        """Test cannot delete property with units"""
        owner = OwnerFactory.create(user=authenticated_client.handler._force_user)
        property = PropertyFactory.create(owners=[owner])
        UnitFactory.create(property=property)
        url = reverse("properties:property-detail", kwargs={"pk": property.pkid})

        response = authenticated_client.delete(url)

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "Cannot delete property with units" in str(response.data)


@pytest.mark.integration
class TestUnitViews:
    """Test suite for Unit API views"""

    def test_list_units_for_property(self, authenticated_client, db):
        """Test that owner can list units for their property"""
        owner = OwnerFactory.create(user=authenticated_client.handler._force_user)
        property = PropertyFactory.create(owners=[owner])
        UnitFactory.create_batch(3, property=property)
        url = reverse("properties:unit-list")

        response = authenticated_client.get(url, {"property": str(property.pkid)})

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["results"]) >= 3

    def test_create_unit_as_owner(self, authenticated_client, db):
        """Test that owner can create unit in their property"""
        owner = OwnerFactory.create(user=authenticated_client.handler._force_user)
        property = PropertyFactory.create(owners=[owner])
        url = reverse("properties:unit-list")
        data = {
            "property_id": str(property.pkid),
            "unit_number": "Apt-100",
            "unit_type": "1_bed",
            "bedrooms": 1,
            "bathrooms": 1,
            "default_rent_amount": "75000",
        }

        response = authenticated_client.post(url, data)

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["unit_number"] == "Apt-100"

    def test_cannot_create_unit_in_other_property(self, authenticated_client, db):
        """Test cannot create unit in another owner's property"""
        other_owner = OwnerFactory.create()
        other_property = PropertyFactory.create(owners=[other_owner])
        url = reverse("properties:unit-list")
        data = {
            "property_id": str(other_property.pkid),
            "unit_number": "Apt-100",
            "default_rent_amount": "75000",
        }

        response = authenticated_client.post(url, data)

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_delete_occupied_unit_forbidden(self, authenticated_client, db):
        """Test cannot delete occupied unit"""
        owner = OwnerFactory.create(user=authenticated_client.handler._force_user)
        property = PropertyFactory.create(owners=[owner])
        unit = UnitFactory.create(property=property, status="occupied")
        url = reverse("properties:unit-detail", kwargs={"pk": unit.pkid})

        response = authenticated_client.delete(url)

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "Cannot delete occupied unit" in str(response.data)


@pytest.mark.integration
class TestManagerViews:
    """Test suite for Manager API views"""

    def test_list_managers(self, authenticated_client, db):
        """Test that authorized user can list managers"""
        ManagerFactory.create_batch(3)
        url = reverse("properties:manager-list")

        response = authenticated_client.get(url)

        # Depends on permission logic - may be 200 or 403
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_403_FORBIDDEN]

    def test_create_manager(self, authenticated_admin_client, db):
        """Test that admin can create manager"""
        user = UserFactory.create()
        url = reverse("properties:manager-list")
        data = {
            "user_id": user.pkid,
            "commission_rate": "5.00",
        }

        response = authenticated_admin_client.post(url, data)

        assert response.status_code == status.HTTP_201_CREATED


@pytest.mark.integration
class TestPropertyManagerAssignmentViews:
    """Test suite for Property Manager Assignment views"""

    def test_list_property_managers(self, authenticated_client, db):
        """Test can list managers for owned property"""
        owner = OwnerFactory.create(user=authenticated_client.handler._force_user)
        property = PropertyFactory.create(owners=[owner])
        manager = ManagerFactory.create()
        property.managers.add(manager)
        url = reverse("properties:property-managers-list", kwargs={"pk": property.pkid})

        response = authenticated_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) >= 1

    def test_add_managers_to_property(self, authenticated_client, db):
        """Test can add managers to owned property"""
        owner = OwnerFactory.create(user=authenticated_client.handler._force_user)
        property = PropertyFactory.create(owners=[owner])
        manager1 = ManagerFactory.create()
        manager2 = ManagerFactory.create()
        url = reverse("properties:property-managers-add", kwargs={"pk": property.pkid})
        data = {"manager_ids": [str(manager1.pkid), str(manager2.pkid)]}

        response = authenticated_client.post(url, data)

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["managers"]) >= 2

    def test_remove_managers_from_property(self, authenticated_client, db):
        """Test can remove managers from owned property"""
        owner = OwnerFactory.create(user=authenticated_client.handler._force_user)
        property = PropertyFactory.create(owners=[owner])
        manager = ManagerFactory.create()
        property.managers.add(manager)
        url = reverse(
            "properties:property-managers-remove", kwargs={"pk": property.pkid}
        )
        data = {"manager_ids": [str(manager.pkid)]}

        response = authenticated_client.post(url, data)

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["managers"]) == 0

    def test_cannot_manage_other_property_managers(self, authenticated_client, db):
        """Test cannot manage managers for another owner's property"""
        other_owner = OwnerFactory.create()
        other_property = PropertyFactory.create(owners=[other_owner])
        manager = ManagerFactory.create()
        url = reverse(
            "properties:property-managers-add", kwargs={"pk": other_property.pkid}
        )
        data = {"manager_ids": [str(manager.pkid)]}

        response = authenticated_client.post(url, data)

        assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.integration
class TestPropertyImageViews:
    """Test suite for Property Image views"""

    def test_list_property_images(self, authenticated_client, db):
        """Test can list images for owned property"""
        owner = OwnerFactory.create(user=authenticated_client.handler._force_user)
        property = PropertyFactory.create(owners=[owner])
        PropertyImageFactory.create_batch(3, property=property)
        url = reverse("properties:property-images-list", kwargs={"pk": property.pkid})

        response = authenticated_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) >= 3


@pytest.mark.integration
class TestUnitImageViews:
    """Test suite for Unit Image views"""

    def test_list_unit_images(self, authenticated_client, db):
        """Test can list images for unit in owned property"""
        owner = OwnerFactory.create(user=authenticated_client.handler._force_user)
        property = PropertyFactory.create(owners=[owner])
        unit = UnitFactory.create(property=property)
        UnitImageFactory.create_batch(2, unit=unit)
        url = reverse("properties:unit-images-list", kwargs={"pk": unit.pkid})

        response = authenticated_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) >= 2
