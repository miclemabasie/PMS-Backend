# app/apps/users/services.py

from typing import List, Optional, Dict, Any
from django.db import transaction
from django.db.models import Count, Q
from django.utils import timezone
from apps.users.models import User, Profile, Role
from apps.users.repositories import UserRepository
from apps.core.base_service import BaseService


class UserService(BaseService[User]):
    """Service for User model."""

    def __init__(self):
        super().__init__(UserRepository())

    def create(self, **data) -> User:
        """Create user with profile (profile created via signal)."""
        # Force role to USER for registration
        if "role" not in data or data["role"] not in Role.values:
            data["role"] = Role.USER
        return self.repository.create(**data)

    def get_by_id(self, pkid: int) -> Optional[User]:
        """Get user by pkid."""
        return self.repository.get(pkid)

    def update_user_role(self, pkid: int, new_role: str, updated_by: User) -> User:
        """Update user role (admin-only operation)."""
        if not updated_by.is_superuser:
            raise PermissionError("Only admins can change user roles")

        if new_role not in Role.values:
            raise ValueError(f"Invalid role: {new_role}")

        user = self.get_by_id(pkid)
        if not user:
            raise ValueError(f"User with pkid {pkid} not found")

        user.role = new_role
        user.save(update_fields=["role"])
        return user

    def deactivate_user(self, pkid: int) -> Optional[User]:
        """Soft-deactivate a user."""
        user = self.get_by_id(pkid)
        if user:
            user.is_active = False
            user.save(update_fields=["is_active"])
        return user

    def search_users(self, **filters) -> List[User]:
        """Search users with flexible filters."""
        return self.repository.filter(**filters)

    def get_user_statistics(self) -> Dict[str, Any]:
        """Get aggregate user statistics."""
        from django.db.models import Count

        # ✅ CORRECT: Use Count() objects, not dict
        stats = User.objects.aggregate(
            total=Count("pkid"),
            active=Count("pkid", filter=Q(is_active=True)),
        )

        by_role = User.objects.values("role").annotate(count=Count("pkid"))

        return {
            "total_users": stats["total"] or 0,
            "active_count": stats["active"] or 0,
            "by_role": {item["role"]: item["count"] for item in by_role},
        }

    @transaction.atomic
    def bulk_deactivate(self, pkids: List[int]) -> int:
        """Bulk deactivate users - transactional."""
        count, _ = User.objects.filter(pkid__in=pkids).update(is_active=False)
        return count


class ProfileService:
    """Business logic for Profile operations."""

    def get_profile_for_user(self, pkid: int) -> Optional[Profile]:
        """Get profile for a user."""
        try:
            return Profile.objects.select_related("user").get(user_id=pkid)
        except Profile.DoesNotExist:
            return None

    def update_profile(self, pkid: int, **data) -> Profile:
        """Update profile and nested user fields."""
        from apps.users.models import User

        user = User.objects.select_related("profile").get(pkid=pkid)
        profile = user.profile

        # Separate user fields from profile fields
        user_fields = {}
        profile_fields = {}

        for key, value in data.items():
            if hasattr(User, key) and key not in ["profile", "pkid", "id"]:
                user_fields[key] = value
            elif hasattr(Profile, key):
                profile_fields[key] = value

        # Update user fields (exclude auto-managed fields)
        for key, value in user_fields.items():
            if key not in ["updated_at", "created_at", "last_login"]:
                setattr(user, key, value)
        if user_fields:
            # ✅ CORRECT: Only save fields that exist on User model
            user.save(
                update_fields=[k for k in user_fields.keys() if k not in ["updated_at"]]
            )

        # Update profile fields
        for key, value in profile_fields.items():
            setattr(profile, key, value)
        if profile_fields:
            profile.save(update_fields=list(profile_fields.keys()))

        return profile

    def update_profile_photo(self, pkid: int, photo_file) -> Profile:
        """Update profile photo with validation."""
        profile = self.get_profile_for_user(pkid)
        if not profile:
            raise ValueError(f"Profile for user {pkid} not found")

        # Validate file type (basic check)
        if photo_file and not photo_file.content_type.startswith("image/"):
            raise ValueError("Only image files are allowed")

        if photo_file:
            profile.profile_photo = photo_file
            profile.save(update_fields=["profile_photo"])
        return profile
