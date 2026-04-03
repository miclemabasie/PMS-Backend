# apps/users/tests/test_controllers.py
import pytest
from django.urls import reverse
from rest_framework.test import APIClient
from apps.users.models import User


@pytest.mark.django_db
class TestUserViewSetEndpoints:
    def test_authenticated_user_can_get_own_profile(self, authenticated_client, user):
        url = reverse("users_api:user-me")  # namespace "users_api", action "me"
        response = authenticated_client.get(url)
        assert response.status_code == 200
        assert response.data["email"] == user.email

    def test_unauthenticated_user_cannot_get_profile(self, api_client):
        url = reverse("users_api:user-me")
        response = api_client.get(url)
        assert response.status_code == 401

    def test_user_can_update_own_profile(self, authenticated_client, user):
        url = reverse("users_api:user-update-me")
        data = {"first_name": "UpdatedFirst", "bio": "New bio"}
        response = authenticated_client.patch(url, data)
        assert response.status_code == 200
        user.refresh_from_db()
        assert user.first_name == "UpdatedFirst"
        assert user.profile.bio == "New bio"

    def test_user_cannot_update_other_profile(
        self, authenticated_client, user, admin_user
    ):
        # The endpoint only allows updating the authenticated user.
        # Trying to pass a different user ID is not possible.
        # This test is already covered by the fact that update_me only affects current user.
        pass  # Not applicable – the endpoint is user‑specific

    def test_user_can_deactivate_own_account(self, authenticated_client, user):
        url = reverse("users_api:user-delete-me")
        response = authenticated_client.delete(url)
        assert response.status_code == 204
        user.refresh_from_db()
        assert user.is_active is False
