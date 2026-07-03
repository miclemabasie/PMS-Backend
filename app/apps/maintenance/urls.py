from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ApproveMaintenanceView, CompleteMaintenanceView, MaintenanceRequestViewSet

app_name = "maintenance"


router = DefaultRouter()
router.register(r'requests', MaintenanceRequestViewSet, basename='maintenance-request')

urlpatterns = [
    path('', include(router.urls)),
    path(
        "<uuid:pk>/approve/",
        ApproveMaintenanceView.as_view(),
        name="approve-maintenance",
    ),
    path(
        "<uuid:pk>/complete/",
        CompleteMaintenanceView.as_view(),
        name="complete-maintenance",
    ),
]

