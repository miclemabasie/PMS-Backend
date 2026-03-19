from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from .permissions import (
    IsOwnerOrManagerOrSuperAdmin,
    CanManageProperty,
    IsTenantOrReadOnly,
)

from .serializers import (
    PropertySerializer,
    OwnerSerializer,
    PropertyOwnershipSerializer,
    ManagerSerializer,
    UnitSerializer,
)
from .services import (
    PropertyService,
    OwnerService,
    PropertyOwnershipService,
    ManagerService,
    UnitService,
)
from .utils import StandardResultsSetPagination, UnitResultsSetPagination


# ----------------------------------------------------------------------
# Owner Views
# ----------------------------------------------------------------------
class OwnerListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.service = OwnerService()
        self.paginator = StandardResultsSetPagination()

    def get(self, request):
        # Only superadmin can list all owners; others see only themselves
        if request.user.is_superuser:
            owners = self.service.get_all()
        else:
            # raise an exception if the user is not superadmin
            return Response({"detail": "Permission denied"}, status=403)

        page = self.paginator.paginate_queryset(owners, request)
        serializer = OwnerSerializer(page, many=True)
        return self.paginator.get_paginated_response(serializer.data)

    def post(self, request):
        # Only superadmin can create arbitrary owners; otherwise create for self
        serializer = OwnerSerializer(data=request.data)
        if serializer.is_valid():
            if request.user.role != "superadmin":
                serializer.validated_data["user"] = request.user
            owner = self.service.create(**serializer.validated_data)
            output = OwnerSerializer(owner)
            return Response(output.data, status=201)
        return Response(serializer.errors, status=400)


class OwnerDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.service = OwnerService()

    def get(self, request, pk):
        owner = self.service.get_by_id(pk)
        if not owner:
            return Response({"detail": "Not found"}, status=404)
        # Only owner themselves or superadmin can view
        if not request.user.is_superuser and owner.user != request.user:
            return Response({"detail": "Permission denied"}, status=403)
        serializer = OwnerSerializer(owner)
        return Response(serializer.data)

    def put(self, request, pk):
        owner = self.service.get_by_id(pk)
        if not owner:
            return Response({"detail": "Not found"}, status=404)
        if not request.user.is_superuser and owner.user != request.user:
            return Response({"detail": "Permission denied"}, status=403)
        serializer = OwnerSerializer(owner, data=request.data, partial=True)
        if serializer.is_valid():
            updated = self.service.update(pk, **serializer.validated_data)
            output = OwnerSerializer(updated)
            return Response(output.data)
        return Response(serializer.errors, status=400)


# ----------------------------------------------------------------------
# Property Views
# ----------------------------------------------------------------------
class PropertyListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.service = PropertyService()
        self.paginator = StandardResultsSetPagination()

    def get(self, request):
        properties = self.service.get_properties_for_user(request.user)
        page = self.paginator.paginate_queryset(properties, request)
        serializer = PropertySerializer(page, many=True, context={"request": request})
        return self.paginator.get_paginated_response(serializer.data)

    def post(self, request):
        # Ensure user has owner profile
        owner_service = OwnerService()
        owner = owner_service.get_or_create_for_user(request.user)
        serializer = PropertySerializer(data=request.data, context={"request": request})
        if serializer.is_valid():
            property = self.service.create_property(
                data=serializer.validated_data,
                owner=owner,
                # manager_ids=request.data.get("manager_ids", []),
            )
            output = PropertySerializer(property, context={"request": request})
            return Response(output.data, status=201)
        return Response(serializer.errors, status=400)


class PropertyDetailView(APIView):
    permission_classes = [IsAuthenticated, IsOwnerOrManagerOrSuperAdmin]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.service = PropertyService()

    def get(self, request, pk):
        property = self.service.get_by_id(pk)
        if not property:
            return Response({"detail": "Not found"}, status=404)
        self.check_object_permissions(request, property)
        serializer = PropertySerializer(property, context={"request": request})
        return Response(serializer.data)

    def put(self, request, pk):
        property = self.service.get_by_id(pk)
        if not property:
            return Response({"detail": "Not found"}, status=404)
        self.check_object_permissions(request, property)
        serializer = PropertySerializer(
            property, data=request.data, partial=False, context={"request": request}
        )
        if serializer.is_valid():
            updated = self.service.update_property(
                pk, serializer.validated_data, manager_ids=request.data.get("managers")
            )
            output = PropertySerializer(updated, context={"request": request})
            return Response(output.data)
        return Response(serializer.errors, status=400)

    def patch(self, request, pk):
        property = self.service.get_by_id(pk)
        if not property:
            return Response({"detail": "Not found"}, status=404)
        self.check_object_permissions(request, property)
        serializer = PropertySerializer(
            property, data=request.data, partial=True, context={"request": request}
        )
        if serializer.is_valid():
            updated = self.service.update_property(
                pk, serializer.validated_data, manager_ids=request.data.get("managers")
            )
            output = PropertySerializer(updated, context={"request": request})
            return Response(output.data)
        return Response(serializer.errors, status=400)

    def delete(self, request, pk):
        property = self.service.get_by_id(pk)
        if not property:
            return Response({"detail": "Not found"}, status=404)
        self.check_object_permissions(request, property)
        # Check if any units exist
        if property.units.exists():
            return Response(
                {"detail": "Cannot delete property with units. Delete units first."},
                status=400,
            )
        self.service.delete(pk)
        return Response(status=204)


# ----------------------------------------------------------------------
# Unit Views
# ----------------------------------------------------------------------
class UnitListCreateView(APIView):
    permission_classes = [IsAuthenticated, CanManageProperty]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.service = UnitService()
        self.paginator = UnitResultsSetPagination()

    def get(self, request):

        property_id = request.query_params.get("property")
        print("this is the property id", property_id)
        if property_id:
            units = self.service.get_units_for_property(property_id)
        else:
            units = self.service.get_all()
        page = self.paginator.paginate_queryset(units, request)
        serializer = UnitSerializer(page, many=True, context={"request": request})
        return self.paginator.get_paginated_response(serializer.data)

    def post(self, request):
        serializer = UnitSerializer(data=request.data, context={"request": request})
        if serializer.is_valid():
            unit = self.service.create(**serializer.validated_data)
            output = UnitSerializer(unit, context={"request": request})
            return Response(output.data, status=201)
        return Response(serializer.errors, status=400)


class UnitDetailView(APIView):
    permission_classes = [IsAuthenticated, IsOwnerOrManagerOrSuperAdmin]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.service = UnitService()

    def get(self, request, pk):
        unit = self.service.get_by_id(pk)
        if not unit:
            return Response({"detail": "Not found"}, status=404)
        self.check_object_permissions(request, unit)
        serializer = UnitSerializer(unit, context={"request": request})
        return Response(serializer.data)

    def put(self, request, pk):
        unit = self.service.get_by_id(pk)
        if not unit:
            return Response({"detail": "Not found"}, status=404)
        self.check_object_permissions(request, unit)
        serializer = UnitSerializer(
            unit, data=request.data, partial=True, context={"request": request}
        )
        if serializer.is_valid():
            updated = self.service.update(pk, **serializer.validated_data)
            output = UnitSerializer(updated, context={"request": request})
            return Response(output.data)
        return Response(serializer.errors, status=400)

    def delete(self, request, pk):
        unit = self.service.get_by_id(pk)
        if not unit:
            return Response({"detail": "Not found"}, status=404)
        self.check_object_permissions(request, unit)
        if unit.status == "occupied":
            return Response({"detail": "Cannot delete occupied unit"}, status=400)
        self.service.delete(pk)
        return Response(status=204)


class ManagerListCreateView(APIView):
    permission_classes = [IsAuthenticated, CanManageProperty]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.service = ManagerService()
        self.paginator = UnitResultsSetPagination()

    def get(self, request):
        managers_qs = self.service.get_all_for_user(request.user)
        page = self.paginator.paginate_queryset(managers_qs, request)
        serializer = ManagerSerializer(page, many=True, context={"request": request})
        return self.paginator.get_paginated_response(serializer.data)

    def post(self, request):
        serializer = ManagerSerializer(data=request.data)
        if serializer.is_valid():
            manager = self.service.create(**serializer.validated_data)
            output = ManagerSerializer(manager)
            return Response(output.data, status=201)
        return Response(serializer.errors, status=400)


class ManagerDetailView(APIView):
    permission_classes = [IsAuthenticated, CanManageProperty]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.service = ManagerService()

    def get(self, request, pk):
        manager = self.service.get_by_id(pk)
        if not manager:
            return Response({"detail": "Not found"}, status=404)
        serializer = ManagerSerializer(manager)
        return Response(serializer.data)

    def put(self, request, pk):
        manager = self.service.get_by_id(pk)
        if not manager:
            return Response({"detail": "Not found"}, status=404)
        serializer = ManagerSerializer(manager, data=request.data)
        if serializer.is_valid():
            updated = self.service.update(pk, **serializer.validated_data)
            output = ManagerSerializer(updated)
            return Response(output.data)
        return Response(serializer.errors, status=400)
