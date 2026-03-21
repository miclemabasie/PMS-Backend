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
    PropertyManagerListView,
    PropertyManagerAddView,
    PropertyManagerRemoveView,
    PropertyManagerReplaceView,
    PropertyManagerAddSingleView,
    PropertyManagerRemoveSingleView,
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
    # Property Manager Assignment
    path(
        "<uuid:pk>/managers/",
        PropertyManagerListView.as_view(),
        name="property-managers-list",
    ),
    path(
        "<uuid:pk>/managers/add/",
        PropertyManagerAddView.as_view(),
        name="property-managers-add",
    ),
    path(
        "<uuid:pk>/managers/remove/",
        PropertyManagerRemoveView.as_view(),
        name="property-managers-remove",
    ),
    path(
        "<uuid:pk>/managers/replace/",
        PropertyManagerReplaceView.as_view(),
        name="property-managers-replace",
    ),
    # Single manager operations (alternative to batch operations)
    path(
        "<uuid:pk>/managers/add-single/",
        PropertyManagerAddSingleView.as_view(),
        name="property-manager-add-single",
    ),
    path(
        "<uuid:pk>/managers/<uuid:manager_pk>/remove-single/",
        PropertyManagerRemoveSingleView.as_view(),
        name="property-manager-remove-single",
    ),
]
