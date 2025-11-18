from django.contrib.auth import get_user_model
from django_countries.serializer_fields import CountryField
from djoser.serializers import UserCreateSerializer as DjoserUserCreateSerializer
from phonenumber_field.serializerfields import PhoneNumberField
from rest_framework import serializers

from apps.users.models import Profile, Role

User = get_user_model()


class UserCreateSerializer(DjoserUserCreateSerializer):
    class Meta(DjoserUserCreateSerializer.Meta):
        model = User
        fields = [
            "id",
            "username",
            "email",
            "first_name",
            "last_name",
            "password",
            "role",
        ]
        read_only_fields = (
            "id",
            "role",
        )  # role can only be set by admin, not during registration

    def create(self, validated_data):
        # force role to USER on registration
        validated_data["role"] = Role.USER
        return super().create(validated_data)


class UserSerializer(serializers.ModelSerializer):
    full_name = serializers.SerializerMethodField()
    is_admin = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id",
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
        ]
        read_only_fields = ("id", "email", "date_joined", "last_login")

    def get_full_name(self, obj):
        return obj.get_full_name()

    def get_is_admin(self, obj):
        return obj.role == Role.ADMIN


class ProfileSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    username = serializers.CharField(source="user.username", read_only=True)
    email = serializers.EmailField(source="user.email", read_only=True)
    first_name = serializers.CharField(source="user.first_name")
    last_name = serializers.CharField(source="user.last_name")
    country = CountryField(name_only=True)

    class Meta:
        model = Profile
        fields = [
            "id",
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
        read_only_fields = ("id", "user", "created_at", "updated_at")

    def update(self, instance, validated_data):
        # Handle nested user fields
        user_data = validated_data.pop("user", {})
        user = instance.user
        for attr, value in user_data.items():
            setattr(user, attr, value)
        user.save()
        return super().update(instance, validated_data)


class UpdateProfileSerializer(serializers.ModelSerializer):
    """Simpler serializer for partial updates (avoids nesting complexities)"""

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
