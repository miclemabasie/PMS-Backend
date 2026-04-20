"""
Factory Boy factories for Tenants app models.
Minimal version to support properties tests.
"""

import factory
from apps.tenants.models import Tenant
from apps.users.tests.factories import UserFactory
from factory.django import DjangoModelFactory


class TenantFactory(DjangoModelFactory):
    """Creates Tenant profile linked to User with tenant role."""

    class Meta:
        model = Tenant

    user = factory.SubFactory(UserFactory, role="tenant")
    id_number = factory.Sequence(lambda n: f"CNI{n:010d}")
    is_discoverable = True
    is_verified = False
