from django.urls import path
from .views import PropertyListCreateView, PropertyDetailView

app_name = "rentals"

urlpatterns = [
    path("properties/", PropertyListCreateView.as_view(), name="property-list"),
    path("properties/<uuid:pk>/", PropertyDetailView.as_view(), name="property-detail"),
]
