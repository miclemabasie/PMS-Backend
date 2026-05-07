# apps/reports/tests/test_services.py
import pytest
from datetime import datetime, timedelta
from django.utils import timezone
from model_bakery import baker
from apps.reports.services.financial_service import FinancialReportService
from apps.payments.models import Payment, RentalAgreement


@pytest.mark.django_db
class TestFinancialReportService:
    def test_property_summary_no_data(self, property):
        service = FinancialReportService()
        result = service.get_property_summary(str(property.id))
        assert result["property_id"] == str(property.id)
        assert len(result["income"]) > 0  # there will be at least one month of zeros

    def test_receipt_data(self, payment):
        service = FinancialReportService()
        data = service.get_receipt_data(str(payment.id))
        assert "payment" in data
        assert "tenant" in data
        assert "property" in data
