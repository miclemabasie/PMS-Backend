# app/apps/payments/tests/factories.py
"""
Factory Boy factories for Payments app models.
"""
import factory
from apps.payments.models import PaymentTerm
from factory.django import DjangoModelFactory
from factory.faker import Faker


class PaymentTermFactory(DjangoModelFactory):
    """Creates PaymentTerm instances."""

    class Meta:
        model = PaymentTerm
        django_get_or_create = ("name",)  # Prevent duplicates

    name = factory.Sequence(lambda n: f"PaymentTerm-{n}")
    interval_months = 1
    description = Faker("sentence")
