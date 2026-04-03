"""
Factories for User app models.
Factory Boy creates test data programmatically without hardcoding values.

Usage:
    user = UserFactory.create()
    admin = AdminUserFactory.create()
    profile = ProfileFactory.create()
"""

import factory
from django.contrib.auth import get_user_model
from apps.users.models import Profile, Role
from factory.django import DjangoModelFactory
from factory.faker import Faker

User = get_user_model()


class UserFactory(DjangoModelFactory):
    """
    Creates User instances with realistic fake data.
    Automatically creates Profile via post_save signal.
    """

    class Meta:
        model = User
        django_get_or_create = ("email",)  # Prevent duplicates during tests

    username = Faker("user_name")
    email = Faker("email")
    first_name = Faker("first_name")
    last_name = Faker("last_name")
    password = factory.PostGenerationMethodCall("set_password", "SecurePass123!")
    is_active = True
    role = Role.USER

    # After creating User, Profile is auto-created via signal
    # No need for explicit profile creation


class ProfileFactory(DjangoModelFactory):
    """
    Creates Profile instances linked to User.
    Use when you need to override profile-specific fields.
    """

    class Meta:
        model = Profile

    user = factory.SubFactory(UserFactory)
    bio = Faker("text", max_nb_chars=100)
    country = "CMR"
    city = Faker("city")
    phone_number = "+237600000000"
    gender = "other"


class AdminUserFactory(UserFactory):
    """
    Creates admin/superuser instances.
    """

    is_staff = True
    is_superuser = True
    role = Role.ADMIN
    email = factory.Sequence(lambda n: f"admin{n}@example.com")


class LandlordUserFactory(UserFactory):
    """
    Creates landlord/owner user instances.
    """

    role = Role.Owner
    email = factory.Sequence(lambda n: f"landlord{n}@example.com")


class TenantUserFactory(UserFactory):
    """
    Creates tenant user instances.
    """

    role = Role.Tenant
    email = factory.Sequence(lambda n: f"tenant{n}@example.com")


class ManagerUserFactory(UserFactory):
    """
    Creates property manager user instances.
    """

    role = Role.Manager
    email = factory.Sequence(lambda n: f"manager{n}@example.com")
