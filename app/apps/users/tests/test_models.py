"""
Tests for User models.
Tests verify model behavior, constraints, and custom methods.

Run: make test-users
"""

import pytest
from django.contrib.auth import get_user_model
from apps.users.models import Profile, Role, DataDeletionRequest
from apps.users.tests.factories import (
    UserFactory,
    ProfileFactory,
    AdminUserFactory,
    LandlordUserFactory,
    TenantUserFactory,
)

User = get_user_model()


@pytest.mark.unit
class TestUserModel:
    """Test suite for User model"""

    def test_user_creation(self, db):
        """Test that we can create a user"""
        user = UserFactory.create(email="newuser@example.com")

        assert user.email == "newuser@example.com"
        assert user.is_active is True
        assert user.role == Role.USER
        assert hasattr(user, "profile")  # Signal creates profile

    def test_user_str_representation(self, db):
        """Test user string representation"""
        user = UserFactory.create(username="john_doe", email="john@example.com")

        assert str(user) == "john_doe - john@example.com"

    def test_user_full_name(self, db):
        """Test get_full_name method"""
        user = UserFactory.create(first_name="John", last_name="Doe")

        assert user.get_full_name() == "John Doe"

    def test_user_short_name(self, db):
        """Test get_short_name method"""
        user = UserFactory.create(username="johndoe")

        assert user.get_short_name() == "johndoe"

    # REPLACE the test_user_email_unique method:
    def test_user_email_unique(self, db):
        """Test email uniqueness constraint at database level"""
        from django.db import IntegrityError
        from apps.users.models import User as UserModel

        # Create first user normally
        user1 = UserFactory.create(email="unique@example.com")

        # Try to create another user with same email using raw model
        # This bypasses factory's django_get_or_create
        with pytest.raises(IntegrityError):
            UserModel.objects.create(
                username="different_user",
                email="unique@example.com",  # Same email
                first_name="Different",
                last_name="User",
                password="SecurePass123!",
            )

    def test_user_role_default(self, db):
        """Test default user role is USER"""
        user = UserFactory.create()

        assert user.role == Role.USER

    def test_admin_user_creation(self, db):
        """Test admin user has correct permissions"""
        admin = AdminUserFactory.create()

        assert admin.is_staff is True
        assert admin.is_superuser is True
        assert admin.role == Role.ADMIN

    def test_landlord_user_creation(self, db):
        """Test landlord user role"""
        landlord = LandlordUserFactory.create()

        assert landlord.role == Role.Owner

    def test_tenant_user_creation(self, db):
        """Test tenant user role"""
        tenant = TenantUserFactory.create()

        assert tenant.role == Role.Tenant

    def test_user_is_active_default(self, db):
        """Test user is_active defaults to True in factory"""
        user = UserFactory.create()

        assert user.is_active is True

    def test_user_password_hashed(self, db):
        """Test password is hashed, not stored in plain text"""
        user = UserFactory.create(password="plainpassword")

        # Password should be hashed (starts with algorithm identifier)
        assert not user.password == "plainpassword"
        assert user.password.startswith("pbkdf2_") or user.password.startswith("argon2")

    def test_user_membership_duration(self, db):
        """Test membership_duration method returns string"""
        user = UserFactory.create()

        duration = user.membership_duration()
        assert isinstance(duration, str)

    def test_user_last_active_never_logged_in(self, db):
        """Test last_active returns 'Never' when no login"""
        user = UserFactory.create(last_login=None)

        assert user.last_active() == "Never"


@pytest.mark.unit
class TestProfileModel:
    """Test suite for Profile model"""

    def test_profile_created_with_user(self, db):
        """Test that profile is auto-created via signal"""
        user = UserFactory.create()

        assert hasattr(user, "profile")
        assert user.profile is not None

    def test_profile_str_representation(self, db):
        """Test profile string representation"""
        user = UserFactory.create(username="testprofile")

        assert str(user.profile) == "testprofile's Profile"

    # REPLACE test_profile_default_country:
    def test_profile_default_country(self, db):
        """Test profile default country is Cameroon"""
        from django_countries import countries

        user = UserFactory.create()

        # CountryField returns Country object, compare with Country(code='CM')
        assert user.profile.country.name == dict(countries).get("CM")
        # OR compare the code:
        assert user.profile.country.code == "CM"

    def test_profile_default_city(self, db):
        """Test profile default city is Bamenda"""
        user = UserFactory.create()

        assert user.profile.city == "Bamenda"

    def test_profile_default_gender(self, db):
        """Test profile default gender is OTHER"""
        user = UserFactory.create()

        assert user.profile.gender == "other"

    def test_profile_phone_number_default(self, db):
        """Test profile default phone number"""
        user = UserFactory.create()

        assert user.profile.phone_number == "+237660181440"

    def test_profile_user_on_delete_cascade(self, db):
        """Test profile is deleted when user is deleted"""
        user = UserFactory.create()
        profile_id = user.profile.id

        user.delete()

        assert not Profile.objects.filter(id=profile_id).exists()

    def test_profile_bio_default(self, db):
        """Test profile default bio is empty string"""
        user = UserFactory.create()

        assert user.profile.bio == "" or user.profile.bio is None


@pytest.mark.unit
class TestDataDeletionRequestModel:
    """Test suite for DataDeletionRequest model"""

    def test_deletion_request_creation(self, db):
        """Test data deletion request can be created"""
        user = UserFactory.create()
        request = DataDeletionRequest.objects.create(
            user=user,
            email=user.email,
            request_type="account",
            status="pending",
        )

        assert request.email == user.email
        assert request.request_type == "account"
        assert request.status == "pending"
        assert request.verification_token is not None

    def test_deletion_request_str(self, db):
        """Test deletion request string representation"""
        user = UserFactory.create()
        request = DataDeletionRequest.objects.create(
            user=user,
            email=user.email,
            request_type="data",
            status="processing",
        )

        assert "data" in str(request).lower()
        assert "processing" in str(request).lower()

    def test_deletion_request_default_status(self, db):
        """Test default status is pending"""
        user = UserFactory.create()
        request = DataDeletionRequest.objects.create(
            user=user,
            email=user.email,
            request_type="account",
        )

        assert request.status == "pending"

    def test_deletion_request_data_to_delete_default(self, db):
        """Test data_to_delete defaults to empty dict"""
        user = UserFactory.create()
        request = DataDeletionRequest.objects.create(
            user=user,
            email=user.email,
            request_type="account",
        )

        assert request.data_to_delete == {}
