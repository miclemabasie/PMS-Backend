from django.urls import path
from .views import TenantListCreateView, TenantDetailView

app_name = "tenants"

urlpatterns = [
    # Tenants
    path("tenants/", TenantListCreateView.as_view(), name="tenant-list"),
    path("tenants/<uuid:pk>/", TenantDetailView.as_view(), name="tenant-detail"),
]
