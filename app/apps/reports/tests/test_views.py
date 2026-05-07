import pytest
from django.urls import reverse
from rest_framework.test import APIClient
from apps.properties.models import Owner


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
