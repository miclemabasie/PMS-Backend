"""
Global pytest fixtures for the entire PMS project.
This file is automatically discovered by pytest - do NOT import it manually.
"""

import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from model_bakery import baker

User = get_user_model()


@pytest.fixture
def api_client():
    """
    Returns an unauthenticated API client.
    Use for testing public endpoints or authentication flows.
    """
    return APIClient()


@pytest.fixture
def user(db):
    """
    Creates a standard test user with profile.
    The 'db' fixture tells pytest this test needs database access.
    """
    return baker.make(
        User,
        email="test@example.com",
        username="testuser",
        first_name="Test",
        last_name="User",
        is_active=True,
        role="user",
    )


@pytest.fixture
def authenticated_client(api_client, user):
    """
    Returns an authenticated API client for a standard user.
    """
    api_client.force_authenticate(user=user)
    return api_client


@pytest.fixture
def admin_user(db):
    """
    Creates a superuser for admin-level tests.
    """
    return baker.make(
        User,
        email="admin@example.com",
        username="admin",
        first_name="Admin",
        last_name="User",
        is_active=True,
        is_staff=True,
        is_superuser=True,
        role="admin",
    )


@pytest.fixture
def authenticated_admin_client(api_client, admin_user):
    """
    Returns an authenticated API client for admin user.
    """
    api_client.force_authenticate(user=admin_user)
    return api_client


@pytest.fixture
def landlord_user(db):
    """
    Creates a user with landlord role.
    """
    return baker.make(
        User,
        email="landlord@example.com",
        username="landlord",
        first_name="Land",
        last_name="Lord",
        is_active=True,
        role="landlord",
    )


@pytest.fixture
def authenticated_landlord_client(api_client, landlord_user):
    """
    Returns an authenticated API client for landlord user.
    """
    api_client.force_authenticate(user=landlord_user)
    return api_client


@pytest.fixture
def tenant_user(db):
    """
    Creates a user with tenant role.
    """
    return baker.make(
        User,
        email="tenant@example.com",
        username="tenant",
        first_name="Ten",
        last_name="Ant",
        is_active=True,
        role="tenant",
    )


@pytest.fixture
def authenticated_tenant_client(api_client, tenant_user):
    """
    Returns an authenticated API client for tenant user.
    """
    api_client.force_authenticate(user=tenant_user)
    return api_client
