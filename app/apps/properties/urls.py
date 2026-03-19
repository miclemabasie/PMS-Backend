from django.urls import path
from .views import (
    OwnerListCreateView,
    OwnerDetailView,
    PropertyListCreateView,
    PropertyDetailView,
    UnitListCreateView,
    UnitDetailView,
    ManagerListCreateView,
    ManagerDetailView,
)

app_name = "properties"

urlpatterns = [
    # Owners
    path("owners/", OwnerListCreateView.as_view(), name="owner-list"),
    path("owners/<uuid:pk>/", OwnerDetailView.as_view(), name="owner-detail"),
    # Properties
    path("", PropertyListCreateView.as_view(), name="property-list"),
    path("<uuid:pk>/", PropertyDetailView.as_view(), name="property-detail"),
    # Units
    path("units/", UnitListCreateView.as_view(), name="unit-list"),
    path("units/<uuid:pk>/", UnitDetailView.as_view(), name="unit-detail"),
    path("managers/", ManagerListCreateView.as_view(), name="manager-list"),
    path("managers/<uuid:pk>/", ManagerDetailView.as_view(), name="manager-detail"),
]
