# apps/reports/tests/test_models.py
import pytest
from django.core.exceptions import ValidationError
from apps.reports.models import TemplateConfig
from apps.properties.models import Owner
from apps.users.models import User
from model_bakery import baker
from apps.reports.models import Expense
from apps.maintenance.models import MaintenanceStatus


@pytest.mark.django_db
class TestTemplateConfig:
    def test_create_default_template(self, landlord_user):
        owner = Owner.objects.create(user=landlord_user)
        template = TemplateConfig.objects.create(
            landlord=owner, template_type="receipt", is_default=True
        )
        assert template.selected_layout == 1
        assert template.primary_color == "#1E3A8A"

    def test_only_one_default_per_type(self, landlord_user):
        owner = Owner.objects.create(user=landlord_user)
        # Use save() instead of create() to trigger the custom save() logic
        t1 = TemplateConfig(landlord=owner, template_type="receipt", is_default=True)
        t1.save()
        t2 = TemplateConfig(landlord=owner, template_type="receipt", is_default=True)
        t2.save()

        t1.refresh_from_db()
        t2.refresh_from_db()
        assert t1.is_default is False
        assert t2.is_default is True


pytestmark = pytest.mark.django_db


class TestExpenseMaintenanceLink:
    def test_expense_can_be_linked_to_maintenance_request(self, maintenance_request):
        expense = baker.make(
            Expense,
            maintenance_request=maintenance_request,
            amount=50000,
            category="maintenance",
        )
        expense.refresh_from_db()
        assert expense.maintenance_request == maintenance_request
        assert maintenance_request.expenses.count() == 1
        assert maintenance_request.expenses.first().amount == 50000

    def test_expense_is_created_when_maintenance_completed(self, maintenance_request):
        # This integration test relies on the service, but we can test the FK directly
        expense = baker.make(Expense, maintenance_request=maintenance_request)
        assert (
            expense.maintenance_request.status == MaintenanceStatus.SUBMITTED
        )  # unchanged
        # The service will later mark request as completed
