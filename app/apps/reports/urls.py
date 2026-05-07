from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    TemplateConfigViewSet,
    PropertyFinancialSummaryView,
    OwnerOverviewView,
    ReceiptDataView,
    MaintenanceSummaryView,
    ExpenseViewSet,
    MaintenanceAnalyticsView,
)

app_name = "reports"

router = DefaultRouter()
router.register(r"templates", TemplateConfigViewSet, basename="template-config")
router.register(r"expenses", ExpenseViewSet, basename="expense")

urlpatterns = [
    path("", include(router.urls)),
    path(
        "property/<uuid:property_id>/summary/",
        PropertyFinancialSummaryView.as_view(),
        name="property-summary",
    ),
    path("owner/overview/", OwnerOverviewView.as_view(), name="owner-overview"),
    path("receipt/<uuid:payment_id>/", ReceiptDataView.as_view(), name="receipt-data"),
    path(
        "maintenance/property/<uuid:property_id>/",
        MaintenanceSummaryView.as_view(),
        name="maintenance-summary",
    ),
    path(
        "maintenance/analytics/<uuid:property_id>/",
        MaintenanceAnalyticsView.as_view(),
        name="maintenance-analytics",
    ),
]
