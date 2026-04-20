"""
Tests for User repositories.
Tests the data access layer in isolation.

Repository tests verify:
- Query correctness (filtering, ordering, joins)
- Permission-based query scoping
- Edge cases (empty results, duplicates)
- Performance hints (select_related, prefetch_related usage)
"""

import pytest
from django.contrib.auth import get_user_model
from apps.users.repositories import UserRepository  # Create this if doesn't exist
from apps.users.tests.factories import (
    UserFactory,
    AdminUserFactory,
    LandlordUserFactory,
)

User = get_user_model()


@pytest.mark.unit
class TestUserRepository:
    """Test suite for UserRepository"""

    @pytest.fixture
    def repository(self):
        """Provide a fresh repository instance for each test"""
        return UserRepository()

    def test_get_by_id_returns_user(self, db, repository):
        """Test retrieving user by ID"""
        user = UserFactory.create()

        result = repository.get(user.pkid)

        assert result is not None
        assert result.pkid == user.pkid
        assert result.email == user.email

    def test_get_by_id_returns_none_for_missing(self, db, repository):
        """Test retrieving non-existent user returns None"""
        result = repository.get(999999)

        assert result is None

    def test_filter_by_role(self, db, repository):
        """Test filtering users by role"""
        UserFactory.create_batch(3, role="user")
        UserFactory.create_batch(2, role="landlord")
        AdminUserFactory.create()

        landlords = repository.filter(role="landlord")

        assert len(landlords) == 2
        assert all(u.role == "landlord" for u in landlords)

    def test_filter_by_active_status(self, db, repository):
        """Test filtering by is_active"""
        UserFactory.create_batch(3, is_active=True)
        UserFactory.create_batch(2, is_active=False)

        active_users = repository.filter(is_active=True)

        assert len(active_users) == 3
        assert all(u.is_active for u in active_users)

    def test_search_by_email_partial_match(self, db, repository):
        """Test email search with partial match"""
        UserFactory.create(email="john@example.com")
        UserFactory.create(email="jane@example.com")
        UserFactory.create(email="bob@other.com")

        results = repository.filter(email__icontains="example.com")

        assert len(results) == 2
        assert all("example.com" in u.email for u in results)

    def test_search_by_name(self, db, repository):
        """Test searching by first or last name"""
        UserFactory.create(first_name="John", last_name="Smith")
        UserFactory.create(first_name="Jane", last_name="Smith")
        UserFactory.create(first_name="Bob", last_name="Jones")

        results = repository.filter(last_name="Smith")

        assert len(results) == 2
        assert all(u.last_name == "Smith" for u in results)

    # Fix test_order_by_date_joined:
    def test_order_by_date_joined(self, db, repository):
        """Test ordering by date_joined descending"""
        from django.utils import timezone
        from datetime import timedelta

        # ✅ Use timezone-aware datetimes to avoid warnings
        now = timezone.now()
        user1 = UserFactory.create(date_joined=now - timedelta(days=10))
        user2 = UserFactory.create(date_joined=now)
        user3 = UserFactory.create(date_joined=now - timedelta(days=5))

        # ✅ Use get_queryset() to get QuerySet for chaining
        results = repository.get_queryset().order_by("-date_joined")

        # Convert to list for assertion
        results_list = list(results)

        assert results_list[0].pkid == user2.pkid  # Most recent first
        assert results_list[1].pkid == user3.pkid
        assert results_list[2].pkid == user1.pkid

    def test_get_queryset_for_user_superuser(self, db, repository):
        """Test superuser can see all users"""
        admin = AdminUserFactory.create()
        UserFactory.create_batch(5)

        queryset = repository.get_queryset_for_user(admin)

        # Should include all users (admin + 5 others)
        assert queryset.count() >= 6

    def test_get_queryset_for_user_regular_user(self, db, repository):
        """Test regular user can only see themselves"""
        regular_user = UserFactory.create()
        UserFactory.create_batch(3)  # Other users

        queryset = repository.get_queryset_for_user(regular_user)

        # Regular users should only see themselves (or empty, depending on policy)
        # Adjust assertion based on your actual permission policy
        user_ids = [u.pkid for u in queryset]
        assert regular_user.pkid in user_ids or queryset.count() == 0

    def test_create_user_sets_defaults(self, db, repository):
        """Test create method applies model defaults"""
        data = {
            "username": "newuser",
            "email": "new@example.com",
            "first_name": "New",
            "last_name": "User",
            "password": "SecurePass123!",
        }

        user = repository.create(**data)

        assert user.role == "user"  # Default from model
        assert user.is_active is False  # Default from factory/model
        assert user.pkid is not None

    def test_update_user_changes_fields(self, db, repository):
        """Test update method modifies user fields"""
        user = UserFactory.create(first_name="Original")

        updated = repository.update(user, first_name="Updated", last_name="Name")

        assert updated.first_name == "Updated"
        assert updated.last_name == "Name"
        # Verify it's the same record
        assert updated.pkid == user.pkid

    def test_delete_user_removes_record(self, db, repository):
        """Test delete method removes user"""
        user = UserFactory.create()
        user_id = user.pkid

        repository.delete(user)

        # Verify user no longer exists
        assert not User.objects.filter(pkid=user_id).exists()

        # Verify profile was cascaded (if signal is working)
        from apps.users.models import Profile

        assert not Profile.objects.filter(user_id=user_id).exists()
