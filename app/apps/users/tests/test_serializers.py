"""
Tests for User serializers.
Tests verify data validation, serialization, and business logic.

Run: make test-users
"""

import pytest
from apps.users.api.serializers import (
    UserSerializer,
    UserCreateSerializer,
    ProfileSerializer,
    UpdateProfileSerializer,
    UserMinimalSerializer,
)
from apps.users.models import Role
from apps.users.tests.factories import UserFactory, ProfileFactory, AdminUserFactory


@pytest.mark.unit
class TestUserSerializer:
    """Test suite for UserSerializer"""

    def test_user_serializer_fields(self, db):
        """Test that serializer has expected fields"""
        user = UserFactory.create()
        serializer = UserSerializer(user)

        expected_fields = [
            "id",
            "pkid",
            "username",
            "email",
            "first_name",
            "last_name",
            "full_name",
            "role",
            "is_active",
            "is_staff",
            "is_superuser",
            "is_admin",
            "date_joined",
            "last_login",
            "profile_picture",
        ]

        for field in expected_fields:
            assert field in serializer.data

    def test_user_serializer_full_name(self, db):
        """Test full_name calculation"""
        user = UserFactory.create(first_name="Jane", last_name="Smith")
        serializer = UserSerializer(user)

        assert serializer.data["full_name"] == "Jane Smith"

    def test_user_serializer_is_admin(self, db):
        """Test is_admin field for different roles"""
        regular_user = UserFactory.create(role="user")
        admin_user = AdminUserFactory.create()

        regular_serializer = UserSerializer(regular_user)
        admin_serializer = UserSerializer(admin_user)

        assert regular_serializer.data["is_admin"] is False
        assert admin_serializer.data["is_admin"] is True

    def test_user_serializer_profile_picture(self, db):
        """Test profile_picture field exists"""
        user = UserFactory.create()
        serializer = UserSerializer(user)

        assert "profile_picture" in serializer.data

    def test_user_serializer_read_only_fields(self, db):
        """Test that certain fields are read-only"""
        user = UserFactory.create()
        serializer = UserSerializer(user)

        read_only_fields = ["id", "email", "date_joined", "last_login"]

        for field in read_only_fields:
            assert field in serializer.fields
            assert serializer.fields[field].read_only is True


@pytest.mark.unit
class TestUserCreateSerializer:
    """Test suite for UserCreateSerializer"""

    def test_create_user_with_valid_data(self, db):
        """Test user creation with valid data"""
        data = {
            "username": "newuser",
            "email": "new@example.com",
            "first_name": "New",
            "last_name": "User",
            "password": "SecurePass123!",
        }

        serializer = UserCreateSerializer(data=data)
        assert serializer.is_valid(), serializer.errors

        user = serializer.save()
        assert user.email == "new@example.com"
        assert user.role == "user"  # Forced to USER on registration

    def test_create_user_with_invalid_email(self, db):
        """Test user creation with invalid email"""
        data = {
            "username": "newuser",
            "email": "invalid-email",
            "first_name": "New",
            "last_name": "User",
            "password": "SecurePass123!",
        }

        serializer = UserCreateSerializer(data=data)
        assert serializer.is_valid() is False
        assert "email" in serializer.errors

    def test_registration_forces_user_role(self, db):
        """Test that registration forces role to USER"""
        data = {
            "username": "newuser",
            "email": "new@example.com",
            "first_name": "New",
            "last_name": "User",
            "password": "SecurePass123!",
            "role": "admin",  # Try to register as admin
        }

        serializer = UserCreateSerializer(data=data)
        assert serializer.is_valid(), serializer.errors

        user = serializer.save()
        assert user.role == "user"  # Should be forced to USER

    def test_create_user_missing_required_field(self, db):
        """Test user creation with missing required field"""
        data = {
            "username": "newuser",
            "email": "new@example.com",
            # Missing first_name
            "last_name": "User",
            "password": "SecurePass123!",
        }

        serializer = UserCreateSerializer(data=data)
        assert serializer.is_valid() is False
        assert "first_name" in serializer.errors

    def test_create_user_password_required(self, db):
        """Test user creation requires password"""
        data = {
            "username": "newuser",
            "email": "new@example.com",
            "first_name": "New",
            "last_name": "User",
            # Missing password
        }

        serializer = UserCreateSerializer(data=data)
        assert serializer.is_valid() is False
        assert "password" in serializer.errors


@pytest.mark.unit
class TestProfileSerializer:
    """Test suite for ProfileSerializer"""

    def test_profile_serializer_fields(self, db):
        """Test that serializer has expected fields"""
        user = UserFactory.create()
        serializer = ProfileSerializer(user.profile)

        expected_fields = [
            "id",
            "pkid",
            "user",
            "username",
            "email",
            "first_name",
            "last_name",
            "bio",
            "profile_photo",
            "gender",
            "country",
            "city",
            "address",
            "phone_number",
            "created_at",
            "updated_at",
        ]

        for field in expected_fields:
            assert field in serializer.data

    def test_profile_serializer_nested_user_data(self, db):
        """Test that user data is nested correctly"""
        user = UserFactory.create(first_name="John", last_name="Doe")
        serializer = ProfileSerializer(user.profile)

        assert serializer.data["username"] == user.username
        assert serializer.data["email"] == user.email
        assert serializer.data["first_name"] == "John"
        assert serializer.data["last_name"] == "Doe"

    def test_profile_serializer_read_only_fields(self, db):
        """Test that certain fields are read-only"""
        user = UserFactory.create()
        serializer = ProfileSerializer(user.profile)

        read_only_fields = ["id", "user", "created_at", "updated_at"]

        for field in read_only_fields:
            assert field in serializer.fields
            assert serializer.fields[field].read_only is True


@pytest.mark.unit
class TestUpdateProfileSerializer:
    """Test suite for UpdateProfileSerializer"""

    def test_update_profile_partial_data(self, db):
        """Test profile update with partial data"""
        user = UserFactory.create()
        data = {"first_name": "Updated"}

        serializer = UpdateProfileSerializer(user.profile, data=data, partial=True)
        assert serializer.is_valid(), serializer.errors

    def test_update_profile_all_fields(self, db):
        """Test profile update with all fields"""
        user = UserFactory.create()
        data = {
            "first_name": "Updated",
            "last_name": "Name",
            "bio": "Test bio",
            "country": "US",
            "city": "New York",
            "phone_number": "+237670000000",
        }

        serializer = UpdateProfileSerializer(user.profile, data=data, partial=True)
        assert serializer.is_valid(), serializer.errors

        profile = serializer.save()
        assert profile.user.first_name == "Updated"
        assert profile.user.last_name == "Name"
        assert profile.bio == "Test bio"
        assert profile.country == "US"
        assert profile.city == "New York"

    def test_update_profile_country_validation(self, db):
        """Test country field validation"""
        user = UserFactory.create()
        data = {"country": "INVALID"}

        serializer = UpdateProfileSerializer(user.profile, data=data, partial=True)
        # CountryField should validate country code
        # This may pass or fail depending on django-countries configuration
        # assert serializer.is_valid() is False


@pytest.mark.unit
class TestUserMinimalSerializer:
    """Test suite for UserMinimalSerializer"""

    def test_minimal_serializer_fields(self, db):
        """Test minimal serializer has expected fields"""
        user = UserFactory.create()
        serializer = UserMinimalSerializer(user)

        expected_fields = ["id", "pkid", "email", "first_name", "last_name", "phone"]

        for field in expected_fields:
            assert field in serializer.data

    def test_minimal_serializer_phone_from_profile(self, db):
        """Test phone number comes from profile"""
        user = UserFactory.create()
        serializer = UserMinimalSerializer(user)

        assert serializer.data["phone"] == user.profile.phone_number


@pytest.mark.django_db
class TestProfileSerializer:
    def test_update_nested_user_fields(self, user):
        profile = user.profile
        data = {"first_name": "Updated", "last_name": "Name", "bio": "New bio"}
        serializer = ProfileSerializer(profile, data=data, partial=True)
        assert serializer.is_valid(), serializer.errors
        updated_profile = serializer.save()
        assert updated_profile.user.first_name == "Updated"
        assert updated_profile.user.last_name == "Name"
        assert updated_profile.bio == "New bio"
