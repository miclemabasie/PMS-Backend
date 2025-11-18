from django.urls import path, include
from rest_framework.routers import DefaultRouter

from apps.users.api.views import UserViewSet

app_name = "users_api"

router = DefaultRouter()
router.register(r"users", UserViewSet, basename="user")

urlpatterns = [
    path("", include(router.urls)),
]
