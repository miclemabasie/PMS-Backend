from django.urls import path
from .views import ApproveMaintenanceView, CompleteMaintenanceView

app_name = "maintenance"

urlpatterns = [
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
