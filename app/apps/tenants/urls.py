from django.urls import path
from .views import (
    TenantListCreateView,
    TenantDetailView,
    TenantSearchView,
    TenantDiscoveryToggleView,
    AdminTenantControlView,
)

app_name = "tenants"

urlpatterns = [
    # Tenants
    path("", TenantListCreateView.as_view(), name="tenant-list"),
    path("<uuid:pk>/", TenantDetailView.as_view(), name="tenant-detail"),
    path("search/", TenantSearchView.as_view(), name="tenant-search"),
    path(
        "discovery-toggle/",
        TenantDiscoveryToggleView.as_view(),
        name="tenant-discovery-toggle",
    ),
    path(
        "<uuid:pk>/admin-control/",
        AdminTenantControlView.as_view(),
        name="admin-tenant-control",
    ),
]
