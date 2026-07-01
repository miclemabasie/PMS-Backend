from django.contrib.auth import get_user_model
from django_countries.serializer_fields import CountryField
from djoser.serializers import UserCreateSerializer as DjoserUserCreateSerializer
from rest_framework import serializers

from apps.users.models import Profile, Role

User = get_user_model()


class UserMinimalSerializer(serializers.ModelSerializer):
    """Minimal user info for nested relations."""

    phone = serializers.CharField(source="profile.phone_number", read_only=True)

    class Meta:
        model = User
        fields = ["id", "pkid", "email", "first_name", "last_name", "phone"]


class UserCreateSerializer(DjoserUserCreateSerializer):
    class Meta(DjoserUserCreateSerializer.Meta):
        model = User
        fields = [
            "id",
            "pkid",
            "username",
            "email",
            "first_name",
            "last_name",
            "password",
            "role",
        ]
        read_only_fields = ("id", "role")

    def create(self, validated_data):
        validated_data["role"] = Role.USER
        return super().create(validated_data)


class ProfileSerializer(serializers.ModelSerializer):
    """
    Profile serializer used inside UserSerializer.
    Does NOT nest UserSerializer to avoid circular import.
    """

    username = serializers.CharField(source="user.username", read_only=True)
    email = serializers.EmailField(source="user.email", read_only=True)
    first_name = serializers.CharField(source="user.first_name")
    last_name = serializers.CharField(source="user.last_name")
    country = CountryField(name_only=True)

    class Meta:
        model = Profile
        fields = [
            "id",
            "pkid",
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
        read_only_fields = ("id", "pkid", "created_at", "updated_at")

    def update(self, instance, validated_data):
        # Simple update – no nested user fields here
        return super().update(instance, validated_data)


class UserSerializer(serializers.ModelSerializer):
    """
    Full user serializer for the frontend.
    Includes nested profile and owner (if landlord).
    """

    full_name = serializers.SerializerMethodField()
    is_admin = serializers.SerializerMethodField()
    profile_picture = serializers.ImageField(source="profile.profile_photo", read_only=True)
    profile = serializers.SerializerMethodField()
    owner = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
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
            "profile",
            "owner",
        ]
        read_only_fields = ("id", "pkid", "email", "date_joined", "last_login")

    def get_full_name(self, obj):
        return obj.get_full_name()

    def get_is_admin(self, obj):
        return obj.role == Role.ADMIN

    def get_profile(self, obj):
        if hasattr(obj, "profile") and obj.profile:
            return ProfileSerializer(obj.profile).data
        return None

    def get_owner(self, obj):
        # Lazy import to avoid circular dependency
        from apps.properties.serializers import OwnerSerializer

        if hasattr(obj, "owner_profile") and obj.owner_profile:
            return OwnerSerializer(obj.owner_profile).data
        return None


class UpdateProfileSerializer(serializers.ModelSerializer):
    """Simpler serializer for partial updates (avoids nesting complexities)."""

    first_name = serializers.CharField(source="user.first_name", required=False)
    last_name = serializers.CharField(source="user.last_name", required=False)
    country = CountryField(name_only=True, required=False)

    class Meta:
        model = Profile
        fields = [
            "first_name",
            "last_name",
            "bio",
            "profile_photo",
            "gender",
            "country",
            "city",
            "address",
            "phone_number",
        ]

    def update(self, instance, validated_data):
        user_data = validated_data.pop("user", {})
        user = instance.user
        for attr, value in user_data.items():
            setattr(user, attr, value)
        user.save()
        return super().update(instance, validated_data)