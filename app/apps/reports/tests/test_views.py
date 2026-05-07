import pytest
from django.urls import reverse
from rest_framework.test import APIClient
from apps.properties.models import Owner


from rest_framework import status
from model_bakery import baker
from apps.properties.models import Property


@pytest.mark.django_db
class TestTemplateViews:
    def test_list_templates_authenticated(self, authenticated_client, landlord_user):
        owner = Owner.objects.create(user=landlord_user)
        response = authenticated_client.get(reverse("reports:template-config-list"))
        assert response.status_code == 200

    def test_create_template(self, authenticated_client, landlord_user):
        owner = Owner.objects.create(user=landlord_user)
        data = {"template_type": "receipt", "selected_layout": 2, "is_default": True}
        response = authenticated_client.post(
            reverse("reports:template-config-list"), data
        )
        assert response.status_code == 201


pytestmark = pytest.mark.django_db


class TestExpenseViewSet:
    def test_list_expenses_as_landlord(
        self, authenticated_landlord_client, property, expense
    ):
        url = reverse("reports:expense-list")
        response = authenticated_landlord_client.get(url)
        assert response.status_code == 200
        data = response.data
        # If pagination is enabled, data is a dict with 'results'
        if isinstance(data, dict) and "results" in data:
            data = data["results"]
        assert len(data) >= 1

    def test_create_expense_with_receipt(
        self, authenticated_landlord_client, property, unit, vendor
    ):
        url = reverse("reports:expense-list")
        data = {
            "property_id": property.pkid,  # integer
            "unit_id": unit.pkid,  # integer
            "category": "maintenance",
            "amount": 75000,
            "expense_date": "2026-05-07",
            "description": "New AC unit",
            "vendor_id": vendor.pkid,  # integer
            "is_reimbursable": False,
        }
        # Attach receipt as multipart file
        from django.core.files.uploadedfile import SimpleUploadedFile

        receipt = SimpleUploadedFile(
            "ac_receipt.pdf", b"file_content", content_type="application/pdf"
        )
        data["receipt"] = receipt
        response = authenticated_landlord_client.post(url, data, format="multipart")
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["amount"] == "75000"
        assert response.data["receipt"] is not None

    def test_expense_permission_other_landlord_cannot_see(
        self, api_client, landlord_user, property, expense
    ):
        from apps.users.models import User

        other_user = baker.make(
            User,
            email="other@example.com",
            role="landlord",
            first_name="Other",
            last_name="Landlord",
        )
        other_owner = baker.make(Owner, user=other_user)
        other_property = baker.make(Property, owners=[other_owner])
        api_client.force_authenticate(user=other_user)
        url = reverse("reports:expense-list")
        response = api_client.get(url)
        assert response.status_code == 200
        data = response.data
        if isinstance(data, dict) and "results" in data:
            data = data["results"]
        expense_ids = [item["id"] for item in data]
        assert str(expense.id) not in expense_ids
