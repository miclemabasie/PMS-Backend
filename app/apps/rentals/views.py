from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404

from .services import PropertyService
from .serializers import PropertySerializer
from .permissions import IsOwnerOrManagerOrSuperAdmin  # custom permission


class PropertyListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.service = PropertyService()

    def get(self, request):
        """List properties accessible to the current user."""
        properties = self.service.get_properties_for_user(request.user)
        serializer = PropertySerializer(
            properties, many=True, context={"request": request}
        )
        return Response(serializer.data)

    def post(self, request):
        """Create a new property."""
        # The user creating the property becomes the owner
        # We assume the user has an owner_profile; you may need to create it if missing
        if not hasattr(request.user, "owner_profile"):
            return Response(
                {"detail": "User does not have an owner profile."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = PropertySerializer(data=request.data, context={"request": request})
        if serializer.is_valid():
            property = self.service.create_property(
                data=serializer.validated_data,
                owner=request.user.owner_profile,
                managers=request.data.get("managers", []),
            )
            output_serializer = PropertySerializer(
                property, context={"request": request}
            )
            return Response(output_serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class PropertyDetailView(APIView):
    permission_classes = [IsAuthenticated, IsOwnerOrManagerOrSuperAdmin]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.service = PropertyService()

    def get(self, request, pk):
        property = self.service.get_by_id(pk)
        if not property:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        self.check_object_permissions(request, property)  # DRF permission check
        serializer = PropertySerializer(property, context={"request": request})
        return Response(serializer.data)

    def put(self, request, pk):
        property = self.service.get_by_id(pk)
        if not property:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        self.check_object_permissions(request, property)

        serializer = PropertySerializer(
            property, data=request.data, partial=False, context={"request": request}
        )
        if serializer.is_valid():
            updated = self.service.update_property(pk, serializer.validated_data)
            output_serializer = PropertySerializer(
                updated, context={"request": request}
            )
            return Response(output_serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def patch(self, request, pk):
        property = self.service.get_by_id(pk)
        if not property:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        self.check_object_permissions(request, property)

        serializer = PropertySerializer(
            property, data=request.data, partial=True, context={"request": request}
        )
        if serializer.is_valid():
            updated = self.service.update_property(pk, serializer.validated_data)
            output_serializer = PropertySerializer(
                updated, context={"request": request}
            )
            return Response(output_serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        property = self.service.get_by_id(pk)
        if not property:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        self.check_object_permissions(request, property)

        self.service.delete(pk)
        return Response(status=status.HTTP_204_NO_CONTENT)
