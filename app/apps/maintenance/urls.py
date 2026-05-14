from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import MaintenanceRequestViewSet, VendorViewSet

app_name = "maintenance"


router = DefaultRouter()
router.register(r"requests", MaintenanceRequestViewSet, basename="maintenance-request")
router.register(r"vendors", VendorViewSet, basename="vendor")

urlpatterns = [
    path("", include(router.urls)),
]
