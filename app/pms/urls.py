from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/v1/auth/", include("djoser.urls")),
    path("api/v1/auth/", include("djoser.urls.jwt")),
    # APIs
    path("api/v1/", include("apps.users.api.urls", namespace="users_api")),
    path("api/v1/tenants/", include("apps.tenants.urls", namespace="tenants")),
    path("api/v1/properties/", include("apps.properties.urls", namespace="properties")),
    path("api/v1/payments/", include("apps.payments.urls", namespace="payments")),
    # path("api/v1/", include("apps.notifications.urls", namespace="notifications")),
    # app/pms/urls.py - add line under other includes
    path("api/v1/reports/", include("apps.reports.urls", namespace="reports")),
    path("api/v1/dashboard/", include("apps.dashboard.urls", namespace="dashboard")),
    path(
        "api/v1/maintenance/", include("apps.maintenance.urls", namespace="maintenance")
    ),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
