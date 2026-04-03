import pytest
from rest_framework.test import APIRequestFactory
from apps.users.api.permissions import IsOwnerOrAdmin, IsAdminOrReadOnly
from apps.users.models import User


@pytest.mark.django_db
class TestIsOwnerOrAdmin:
    def setup_method(self):
        self.factory = APIRequestFactory()

    def test_owner_can_access_own_object(self, user):
        request = self.factory.get("/")
        request.user = user  # manually attach user
        permission = IsOwnerOrAdmin()
        assert permission.has_object_permission(request, None, user)

    def test_user_cannot_access_other_user(self, user, admin_user):
        request = self.factory.get("/")
        request.user = user
        permission = IsOwnerOrAdmin()
        assert not permission.has_object_permission(request, None, admin_user)

    def test_admin_can_access_any_user(self, admin_user, user):
        request = self.factory.get("/")
        request.user = admin_user
        permission = IsOwnerOrAdmin()
        assert permission.has_object_permission(request, None, user)


@pytest.mark.django_db
class TestIsAdminOrReadOnly:
    def setup_method(self):
        self.factory = APIRequestFactory()

    def test_readonly_allowed_for_any_user(self, user):
        request = self.factory.get("/")
        request.user = user
        permission = IsAdminOrReadOnly()
        assert permission.has_permission(request, None) is True

    def test_write_forbidden_for_non_admin(self, user):
        request = self.factory.post("/")
        request.user = user
        permission = IsAdminOrReadOnly()
        assert permission.has_permission(request, None) is False

    def test_write_allowed_for_admin(self, admin_user):
        request = self.factory.post("/")
        request.user = admin_user
        permission = IsAdminOrReadOnly()
        assert permission.has_permission(request, None) is True
