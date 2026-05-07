from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from .services import MaintenanceService
from .serializers import MaintenanceRequestSerializer
from apps.properties.permissions import IsOwnerOrManagerOrSuperAdmin
from decimal import Decimal


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
