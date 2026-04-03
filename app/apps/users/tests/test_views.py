"""
Tests for User API views.
Tests verify endpoints work correctly with proper permissions.

Run: make test-users
"""

import pytest
from django.urls import reverse
from rest_framework import status
from apps.users.models import Role
from apps.users.tests.factories import (
    UserFactory,
    AdminUserFactory,
    LandlordUserFactory,
    TenantUserFactory,
)


@pytest.mark.integration
class TestUserAPIViews:
    """Test suite for User API endpoints"""

    def test_authenticated_user_can_get_own_profile(self, authenticated_client, user):
        """Test that authenticated user can retrieve their profile"""
        url = reverse("users_api:user-me")
        response = authenticated_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data["email"] == user.email
        assert response.data["username"] == user.username

    def test_unauthenticated_user_cannot_access_profile(self, api_client):
        """Test that unauthenticated user cannot access profile"""
        url = reverse("users_api:user-me")
        response = api_client.get(url)

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_admin_can_assign_user_role(
        self, authenticated_admin_client, admin_user, user
    ):
        """Test that admin can assign user role"""
        url = reverse("users_api:user-assign-role")
        data = {"user_id": str(user.pkid), "role": "landlord"}

        response = authenticated_admin_client.post(url, data)

        assert response.status_code == status.HTTP_200_OK
        user.refresh_from_db()
        assert user.role == "landlord"

    def test_regular_user_cannot_assign_role(self, authenticated_client, user):
        """Test that regular user cannot assign roles"""
        url = reverse("users_api:user-assign-role")
        data = {"user_id": str(user.pkid), "role": "landlord"}

        response = authenticated_client.post(url, data)

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_user_can_update_own_profile(self, authenticated_client, user):
        """Test that user can update their own profile"""
        url = reverse("users_api:user-update-me")
        data = {"first_name": "Updated", "last_name": "Name"}

        response = authenticated_client.patch(url, data)

        assert response.status_code == status.HTTP_200_OK
        user.refresh_from_db()
        assert user.first_name == "Updated"
        assert user.last_name == "Name"

    def test_user_can_deactivate_own_account(self, authenticated_client, user):
        """Test that user can deactivate their account"""
        url = reverse("users_api:user-delete-me")
        response = authenticated_client.delete(url)

        assert response.status_code == status.HTTP_204_NO_CONTENT
        user.refresh_from_db()
        assert user.is_active is False

    def test_admin_can_list_all_users(self, authenticated_admin_client, db):
        """Test that admin can list all users"""
        UserFactory.create_batch(5)
        url = reverse("users_api:user-list")

        response = authenticated_admin_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) >= 5

    def test_regular_user_cannot_list_all_users(self, authenticated_client, db):
        """Test that regular user cannot list all users"""
        UserFactory.create_batch(5)
        url = reverse("users_api:user-list")

        response = authenticated_client.get(url)

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_admin_invalid_role_assignment(self, authenticated_admin_client, user):
        """Test admin cannot assign invalid role"""
        url = reverse("users_api:user-assign-role")
        data = {"user_id": str(user.pkid), "role": "invalid_role"}

        response = authenticated_admin_client.post(url, data)

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "Role must be one of" in str(response.data)

    def test_admin_assign_role_missing_user_id(self, authenticated_admin_client):
        """Test admin role assignment requires user_id"""
        url = reverse("users_api:user-assign-role")
        data = {"role": "landlord"}

        response = authenticated_admin_client.post(url, data)

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "user_id and role are required" in str(response.data)


@pytest.mark.integration
class TestUserPermissions:
    """Test suite for User permissions"""

    def test_landlord_cannot_access_admin_endpoints(
        self, authenticated_landlord_client
    ):
        """Test landlord cannot access admin-only endpoints"""
        url = reverse("users_api:user-list")
        response = authenticated_landlord_client.get(url)

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_tenant_cannot_access_admin_endpoints(self, authenticated_tenant_client):
        """Test tenant cannot access admin-only endpoints"""
        url = reverse("users_api:user-list")
        response = authenticated_tenant_client.get(url)

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_admin_can_access_all_endpoints(self, authenticated_admin_client):
        """Test admin can access all user endpoints"""
        urls = [
            reverse("users_api:user-list"),
            reverse("users_api:user-me"),
        ]

        for url in urls:
            response = authenticated_admin_client.get(url)
            assert response.status_code in [
                status.HTTP_200_OK,
                status.HTTP_201_CREATED,
            ]
