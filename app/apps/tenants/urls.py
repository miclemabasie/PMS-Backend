from django.urls import path
from .views import TenantListCreateView, TenantDetailView, TenantSearchView

app_name = "tenants"

urlpatterns = [
    # Tenants
    path("", TenantListCreateView.as_view(), name="tenant-list"),
    path("<uuid:pk>/", TenantDetailView.as_view(), name="tenant-detail"),
    path("search/", TenantSearchView.as_view(), name="tenant-search"),
]
