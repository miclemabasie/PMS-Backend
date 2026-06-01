from django.urls import path
from apps.dashboard.views import LandlordDashboardStatsView

app_name = "dashboard"

urlpatterns = [
    path(
        "landlord/stats/",
        LandlordDashboardStatsView.as_view(),
        name="landlord-stats",
    ),
]
