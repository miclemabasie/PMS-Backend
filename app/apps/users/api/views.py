import logging

from django.shortcuts import get_object_or_404
from rest_framework import viewsets, permissions, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet
from rest_framework.mixins import (
    RetrieveModelMixin,
    UpdateModelMixin,
    DestroyModelMixin,
    ListModelMixin,
)

from apps.users.models import User, Profile, Role
from apps.users.api.serializers import (
    UserSerializer,
    ProfileSerializer,
    UpdateProfileSerializer,
)
from apps.users.api.permissions import IsOwnerOrAdmin, IsAdminOrReadOnly
from apps.users.api.renderers import ProfileJSONRenderer

logger = logging.getLogger(__name__)


class UserViewSet(viewsets.ModelViewSet):
    """
    ViewSet for User model.
    Admin users can list and manage all users; regular users can only retrieve/update their own.
    """

    queryset = User.objects.all().select_related("profile")
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["username", "email", "first_name", "last_name"]
    ordering_fields = ["date_joined", "last_login", "username"]
    ordering = ["-date_joined"]

    def get_permissions(self):
        if self.action in ["list", "destroy"]:
            self.permission_classes = [permissions.IsAdminUser]
        elif self.action in ["retrieve", "update", "partial_update"]:
            self.permission_classes = [permissions.IsAuthenticated, IsOwnerOrAdmin]
        else:
            self.permission_classes = [permissions.IsAuthenticated]
        return super().get_permissions()

    def get_serializer_class(self):
        if self.action == "partial_update":
            return UpdateProfileSerializer  # for profile updates
        return super().get_serializer_class()

    @action(
        detail=False, methods=["get"], permission_classes=[permissions.IsAuthenticated]
    )
    def me(self, request):
        """Retrieve the currently authenticated user."""
        serializer = self.get_serializer(request.user)
        return Response(serializer.data)

    @action(
        detail=False,
        methods=["patch"],
        permission_classes=[permissions.IsAuthenticated],
    )
    def update_me(self, request):
        """Update the currently authenticated user's profile."""
        instance = request.user.profile
        serializer = UpdateProfileSerializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        # Return full user data after update
        user_serializer = UserSerializer(request.user)
        return Response(user_serializer.data)

    @action(
        detail=False,
        methods=["delete"],
        permission_classes=[permissions.IsAuthenticated],
    )
    def delete_me(self, request):
        """Soft‑delete the current user (or mark as inactive)."""
        user = request.user
        user.is_active = False
        user.save()
        logger.info(f"User {user.email} deactivated their account.")
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(
        detail=False, methods=["post"], permission_classes=[permissions.IsAdminUser]
    )
    def assign_role(self, request):
        """Admin endpoint to change a user's role."""
        user_id = request.data.get("user_id")
        new_role = request.data.get("role")
        if not user_id or not new_role:
            return Response(
                {"error": "user_id and role are required."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if new_role not in Role.values:
            return Response(
                {"error": f"Role must be one of {Role.values}."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        user = get_object_or_404(User, pkid=user_id)
        user.role = new_role
        user.save()
        logger.info(
            f"Admin {request.user.email} changed role of {user.email} to {new_role}."
        )
        return Response({"detail": f"Role updated to {new_role}."})
