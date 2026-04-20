# app/apps/users/repositories.py

from apps.core.base_repository import DjangoRepository
from apps.users.models import User


class UserRepository(DjangoRepository[User]):
    """Repository for User model with pkid-based lookups."""

    def __init__(self):
        super().__init__(User)

    def get(self, pkid: int) -> User | None:
        """Get user by pkid (internal numeric ID)."""
        try:
            return self.model_class.objects.get(pkid=pkid)
        except self.model_class.DoesNotExist:
            return None

    def filter(self, **filters) -> list[User]:
        """Filter users - returns list for consistency."""
        return list(self.model_class.objects.filter(**filters))

    def get_queryset(self, **filters):
        """Return QuerySet for chaining (e.g., .order_by())."""
        return self.model_class.objects.filter(**filters)

    def create(self, **data) -> User:
        """Create user - handles password hashing."""
        if "password" in data and data["password"]:
            user = self.model_class(
                **{k: v for k, v in data.items() if k != "password"}
            )
            user.set_password(data["password"])
            user.save()
            return user
        return self.model_class.objects.create(**data)

    def update(self, instance: User, **data) -> User:
        """Update user fields."""
        for key, value in data.items():
            if key != "updated_at":  # auto_now field
                setattr(instance, key, value)
        instance.save()
        return instance

    def delete(self, instance: User) -> None:
        """Delete user."""
        instance.delete()

    # Custom queries
    def find_by_email(self, email: str) -> User | None:
        """Find user by email."""
        return self.model_class.objects.filter(email=email).first()

    def find_active_by_role(self, role: str) -> list[User]:
        """Find active users with specific role."""
        return list(
            self.model_class.objects.filter(role=role, is_active=True).select_related(
                "profile"
            )
        )

    def get_queryset_for_user(self, user: User):
        """
        Return queryset scoped to what the given user can see.

        Rules:
        - Superuser: all users
        - Regular user: only themselves
        """
        qs = self.model_class.objects.all().select_related("profile")

        if user.is_superuser:
            return qs

        # Regular users only see themselves
        return qs.filter(pkid=user.pkid)
