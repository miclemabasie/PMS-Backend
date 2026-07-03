from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, viewsets, parsers
from rest_framework.permissions import IsAuthenticated
from .services import MaintenanceService
from .serializers import (
    MaintenanceRequestSerializer,
    MaintenanceRequestCreateSerializer,
    MaintenanceRequestStatusSerializer
)
from rest_framework.decorators import action


from apps.properties.permissions import IsOwnerOrManagerOrSuperAdmin
from decimal import Decimal


from rest_framework import viewsets, status, parsers
from django.db import transaction
from apps.maintenance.permissions import CanManageMaintenanceRequest



class ApproveMaintenanceView(APIView):
    permission_classes = [IsAuthenticated, IsOwnerOrManagerOrSuperAdmin]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.service = MaintenanceService()

    def post(self, request, pk):
        try:
            req = self.service.approve_request(
                pk,
                (
                    request.user.manager_profile.id
                    if hasattr(request.user, "manager_profile")
                    else None
                ),
            )
            return Response(
                MaintenanceRequestSerializer(req).data, status=status.HTTP_200_OK
            )
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class CompleteMaintenanceView(APIView):
    permission_classes = [IsAuthenticated, IsOwnerOrManagerOrSuperAdmin]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.service = MaintenanceService()

    def post(self, request, pk):
        actual_cost = request.data.get("actual_cost")
        if not actual_cost:
            return Response({"error": "actual_cost required"}, status=400)
        notes = request.data.get("notes", "")
        try:
            expense = self.service.complete_request(pk, Decimal(actual_cost), notes)
            return Response(
                {
                    "expense_id": str(expense.id),
                    "message": "Request completed and expense recorded",
                },
                status=200,
            )
        except ValueError as e:
            return Response({"error": str(e)}, status=400)

class MaintenanceRequestViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, CanManageMaintenanceRequest]
    parser_classes = [parsers.MultiPartParser, parsers.FormParser, parsers.JSONParser]

    lookup_field = 'id'
    lookup_url_kwarg = 'pk' 

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.service = MaintenanceService()

    def get_queryset(self):
        queryset = self.service.get_requests_for_user(self.request.user)
        filters = {
            'status': self.request.query_params.get('status'),
            'priority': self.request.query_params.get('priority'),
            'property': self.request.query_params.get('property'),
        }
        return self.service.apply_filters(queryset, filters)

    def get_serializer_class(self):
        if self.action == 'create':
            return MaintenanceRequestCreateSerializer
        if self.action in ['update', 'partial_update']:
            return MaintenanceRequestCreateSerializer
        return MaintenanceRequestSerializer

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        validated_data = serializer.validated_data

        # Get tenant_id if the user is a tenant
        tenant_id = None
        if hasattr(request.user, 'tenant_profile'):
            tenant_id = str(request.user.tenant_profile.id)

        try:
            request_obj = self.service.create_request(
                unit_id=str(validated_data['unit_id']),
                title=validated_data['title'],
                description=validated_data['description'],
                priority=validated_data['priority'],
                tenant_id=tenant_id,
                notes=validated_data.get('notes', ''),
                images=validated_data.get('images', [])
            )
            output_serializer = MaintenanceRequestSerializer(request_obj)
            return Response(output_serializer.data, status=status.HTTP_201_CREATED)
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['patch'])
    @transaction.atomic
    def status(self, request, pk=None):
        serializer = MaintenanceRequestStatusSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            updated = self.service.update_status(
                request_id=pk,
                new_status=serializer.validated_data['status'],
                user=request.user
            )
            output_serializer = MaintenanceRequestSerializer(updated)
            return Response(output_serializer.data)
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    @transaction.atomic
    def complete(self, request, pk=None):
        actual_cost = request.data.get('actual_cost')
        notes = request.data.get('notes', '')
        if not actual_cost:
            return Response(
                {"error": "actual_cost is required"},
                status=status.HTTP_400_BAD_REQUEST
            )
        try:
            updated = self.service.complete_request(
                request_id=pk,
                actual_cost=Decimal(str(actual_cost)),
                notes=notes
            )
            output_serializer = MaintenanceRequestSerializer(updated)
            return Response(output_serializer.data)
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
