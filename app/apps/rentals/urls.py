from django.urls import path
from .views import (
    PaymentTermListCreateView,
    PaymentTermDetailView,
    OwnerListCreateView,
    OwnerDetailView,
    # ManagerListCreateView, ManagerDetailView,
    TenantListCreateView,
    TenantDetailView,
    PropertyListCreateView,
    PropertyDetailView,
    UnitListCreateView,
    UnitDetailView,
    LeaseListCreateView,
    LeaseDetailView,
    LeaseTerminateView,
    LeaseRenewView,
    PaymentListCreateView,
    PaymentDetailView,
    MaintenanceRequestListCreateView,
    MaintenanceRequestDetailView,
    MaintenanceRequestAssignView,
    MaintenanceRequestCompleteView,
    VendorListCreateView,
    VendorDetailView,
    ExpenseListCreateView,
    ExpenseDetailView,
    DocumentListCreateView,
    DocumentDetailView,
)

app_name = "rentals"

urlpatterns = [
    # Payment Terms
    path(
        "payment-terms/", PaymentTermListCreateView.as_view(), name="payment-term-list"
    ),
    path(
        "payment-terms/<uuid:pk>/",
        PaymentTermDetailView.as_view(),
        name="payment-term-detail",
    ),
    # Owners
    path("owners/", OwnerListCreateView.as_view(), name="owner-list"),
    path("owners/<uuid:pk>/", OwnerDetailView.as_view(), name="owner-detail"),
    # Tenants
    path("tenants/", TenantListCreateView.as_view(), name="tenant-list"),
    path("tenants/<uuid:pk>/", TenantDetailView.as_view(), name="tenant-detail"),
    # Properties
    path("properties/", PropertyListCreateView.as_view(), name="property-list"),
    path("properties/<uuid:pk>/", PropertyDetailView.as_view(), name="property-detail"),
    # Units
    path("units/", UnitListCreateView.as_view(), name="unit-list"),
    path("units/<uuid:pk>/", UnitDetailView.as_view(), name="unit-detail"),
    # Leases
    path("leases/", LeaseListCreateView.as_view(), name="lease-list"),
    path("leases/<uuid:pk>/", LeaseDetailView.as_view(), name="lease-detail"),
    path(
        "leases/<uuid:pk>/terminate/",
        LeaseTerminateView.as_view(),
        name="lease-terminate",
    ),
    path("leases/<uuid:pk>/renew/", LeaseRenewView.as_view(), name="lease-renew"),
    # Payments
    path("payments/", PaymentListCreateView.as_view(), name="payment-list"),
    path("payments/<uuid:pk>/", PaymentDetailView.as_view(), name="payment-detail"),
    # Maintenance Requests
    path(
        "maintenance-requests/",
        MaintenanceRequestListCreateView.as_view(),
        name="maintenance-list",
    ),
    path(
        "maintenance-requests/<uuid:pk>/",
        MaintenanceRequestDetailView.as_view(),
        name="maintenance-detail",
    ),
    path(
        "maintenance-requests/<uuid:pk>/assign/",
        MaintenanceRequestAssignView.as_view(),
        name="maintenance-assign",
    ),
    path(
        "maintenance-requests/<uuid:pk>/complete/",
        MaintenanceRequestCompleteView.as_view(),
        name="maintenance-complete",
    ),
    # Vendors
    path("vendors/", VendorListCreateView.as_view(), name="vendor-list"),
    path("vendors/<uuid:pk>/", VendorDetailView.as_view(), name="vendor-detail"),
    # Expenses
    path("expenses/", ExpenseListCreateView.as_view(), name="expense-list"),
    path("expenses/<uuid:pk>/", ExpenseDetailView.as_view(), name="expense-detail"),
    # Documents
    path("documents/", DocumentListCreateView.as_view(), name="document-list"),
    path("documents/<uuid:pk>/", DocumentDetailView.as_view(), name="document-detail"),
]
