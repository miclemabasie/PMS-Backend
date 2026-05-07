"""
Global pytest fixtures for the entire PMS project.
This file is automatically discovered by pytest - do NOT import it manually.

Fixtures provide reusable test data and setup code.
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


# ========== ADDITIONAL FIXTURES FOR REPORTS TESTS ==========
# ========== ADDITIONAL FIXTURES FOR REPORTS TESTS ==========
from apps.properties.models import Property, Owner, Unit
from apps.payments.models import Payment, RentalAgreement, PaymentPlan
from apps.tenants.models import Tenant
from django.utils import timezone


@pytest.fixture
def owner(landlord_user):
    return baker.make(Owner, user=landlord_user)


@pytest.fixture
def property(owner):
    # Use `baker.make` with m2m assignment
    prop = baker.make(Property, owners=[])
    prop.owners.add(owner)
    return prop


@pytest.fixture
def unit(property):
    return baker.make(
        Unit,
        property=property,
        unit_number="A101",
        default_rent_amount=100000,
        monthly_rent=100000,
        yearly_rent=1200000,
        default_security_deposit=50000,
        bedrooms=2,
        bathrooms=1,
        size_m2=75,
    )


@pytest.fixture
def tenant(tenant_user):
    return baker.make(Tenant, user=tenant_user)


@pytest.fixture
def payment_plan():
    return baker.make(PaymentPlan, mode="monthly", is_active=True)


@pytest.fixture
def rental_agreement(unit, tenant, payment_plan):
    return baker.make(
        RentalAgreement,
        unit=unit,
        tenant=tenant,
        payment_plan=payment_plan,
        is_active=True,
    )


@pytest.fixture
def payment(rental_agreement):
    return baker.make(
        Payment,
        agreement=rental_agreement,
        amount=100000,
        status="completed",
        payment_date=timezone.now().date(),
        period_start=timezone.now().date(),
        period_end=timezone.now().date(),
        fee_breakdown={
            "platform_fee": 1000,
            "gateway_fee": 2000,
            "landlord_net": 97000,
        },
        net_landlord_amount=97000,
        transaction_id="TXN123",
    )
