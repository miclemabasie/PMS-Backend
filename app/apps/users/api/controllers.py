from rest_framework import permissions, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.logging import CustomLogger
from apps.users.models import Profile, User

from .exceptions import ProfileNotFoundException, NotYourProfileException
from .renderers import ProfileJSONRenderer
from .serializers import (
    ProfileSerializer,
    UpdateProfileSerializer,
    UnifiedProfileSerializer,
)

logger = CustomLogger(__name__)


class GetProfileAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    renderer_classes = [ProfileJSONRenderer]

    def get(self, request):
        logger.action(
            action="get_own_profile",
            actor=request.user.username,
        )

        profile = request.user.profile
        serializer = ProfileSerializer(profile, context={"request": request})

        logger.state(
            "Profile retrieved successfully",
            profile_id=profile.id,
        )

        return Response(serializer.data, status=status.HTTP_200_OK)


class UpdateProfileAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    renderer_classes = [ProfileJSONRenderer]
    serializer_class = UpdateProfileSerializer

    def patch(self, request, username):
        logger.action(
            action="attempt_profile_update",
            actor=request.user.username,
            target=username,
        )

        try:
            profile = Profile.objects.get(user__username=username)
        except Profile.DoesNotExist:
            logger.failure(
                "Profile not found",
                target=username,
            )
            raise ProfileNotFoundException("Profile does not exist")

        if request.user.username != username:
            logger.failure(
                "Unauthorized profile update attempt",
                actor=request.user.username,
                target=username,
            )
            raise NotYourProfileException(
                "You do not have permission to update this profile."
            )

        serializer = self.serializer_class(
            instance=profile,
            data=request.data,
            partial=True,
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()

        logger.action(
            action="profile_updated",
            actor=request.user.username,
            updated_fields=list(serializer.validated_data.keys()),
        )

        return Response(serializer.data, status=status.HTTP_200_OK)


@api_view(["GET", "PUT", "PATCH"])
@permission_classes([permissions.IsAuthenticated])
def profile_update(request):
    """
    Unified profile endpoint
    - GET: retrieve current user's profile
    - PUT/PATCH: update user + profile fields
    """
    user: User = request.user

    logger.action(
        action="profile_endpoint_accessed",
        actor=user.username,
        method=request.method,
    )

    if request.method in ["PUT", "PATCH"]:
        serializer = UnifiedProfileSerializer(
            user,
            data=request.data,
            partial=request.method == "PATCH",
        )

        if not serializer.is_valid():
            logger.failure(
                "Profile update validation failed",
                actor=user.username,
                errors=serializer.errors,
            )
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        validated_data = serializer.validated_data

        logger.state(
            "Validated profile payload",
            fields=list(validated_data.keys()),
        )

        # ---- Update User fields ----
        user.first_name = validated_data.get("first_name", user.first_name)
        user.last_name = validated_data.get("last_name", user.last_name)
        user.save(update_fields=["first_name", "last_name"])

        # ---- Update Profile fields ----
        profile = user.profile
        profile_data = validated_data.get("profile", {})

        profile.phone_number = validated_data.get(
            "phone_number",
            profile.phone_number,
        )
        profile.bio = profile_data.get("bio", profile.bio)
        profile.gender = profile_data.get("gender", profile.gender)
        profile.country = profile_data.get("country", profile.country)
        profile.city = profile_data.get("city", profile.city)
        profile.address = profile_data.get("address", profile.address)

        if "profile_photo" in profile_data:
            profile.profile_photo = profile_data["profile_photo"]
            logger.state(
                "Profile photo updated",
                actor=user.username,
            )

        profile.save()

        logger.action(
            action="profile_fully_updated",
            actor=user.username,
        )

        return Response(serializer.data, status=status.HTTP_200_OK)

    # ---- GET ----
    serializer = UnifiedProfileSerializer(user)

    logger.state(
        "Profile returned via unified endpoint",
        actor=user.username,
    )

    return Response(serializer.data, status=status.HTTP_200_OK)
