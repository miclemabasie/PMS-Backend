# apps/agreements/views.py

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404

from apps.properties.services import UnitService
from apps.tenants.models import Tenant

from .services import PaymentPlanService, RentalAgreementService, PaymentService
from .serializers import (
    PaymentPlanSerializer,
    InstallmentSerializer,
    RentalAgreementSerializer,
    PaymentSerializer,
    MakePaymentSerializer,
)
from .permissions import (
    IsLandlordOrManagerOrSuperAdminForUnit,
    CanManageRentalAgreement,
)
from django.core.exceptions import PermissionDenied
from .serializers import RentalAgreementDetailSerializer
from .permissions import user_can_manage_agreement


# ----------------------------------------------------------------------
# Payment Plan Views
# ----------------------------------------------------------------------
class PaymentPlanListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.service = PaymentPlanService()

    def get(self, request):
        plans = self.service.get_active_plans()
        serializer = PaymentPlanSerializer(plans, many=True)
        return Response(serializer.data)

    def post(self, request):
        serializer = PaymentPlanSerializer(data=request.data)

        if serializer.is_valid():
            plan = self.service.create_payment_plan(
                request.user, serializer.validated_data
            )
            if plan:
                return Response(
                    PaymentPlanSerializer(plan).data, status=status.HTTP_201_CREATED
                )
            return Response({"detail": "Permission denied"}, status=403)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class InstallmentListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.service = PaymentPlanService()

    def get(self, request, plan_id):
        installments = self.service.get_installments(plan_id)
        serializer = InstallmentSerializer(installments, many=True)
        return Response(serializer.data)

    def post(self, request, plan_id):
        serializer = InstallmentSerializer(data=request.data)
        if serializer.is_valid():
            try:
                installment = self.service.add_installment(
                    plan_id=plan_id,
                    percent=serializer.validated_data["percent"],
                    due_date=serializer.validated_data.get("due_date"),
                    order_index=serializer.validated_data.get("order_index"),
                )
                return Response(
                    InstallmentSerializer(installment).data,
                    status=status.HTTP_201_CREATED,
                )
            except ValueError as e:
                return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# ----------------------------------------------------------------------
# Rental Agreement Views
# ----------------------------------------------------------------------
class RentalAgreementCreateView(APIView):
    permission_classes = [IsAuthenticated, IsLandlordOrManagerOrSuperAdminForUnit]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.service = RentalAgreementService()
        self.plan_service = PaymentPlanService()
        self.unit_service = UnitService()

    def post(self, request):
        unit_id = request.data.get("unit_id")
        tenant_id = request.data.get("tenant_id")
        plan_id = request.data.get("payment_plan_id")

        if not self.unit_service.user_can_manage_unit(request.user, unit_id):
            return Response(
                {
                    "error": "You do not have permission to create an agreement for this unit."
                },
                status=403,
            )

        unit = self.unit_service.get_by_id(unit_id)
        tenant = get_object_or_404(Tenant, id=tenant_id)
        plan = self.plan_service.get_by_id(plan_id)
        if not plan:
            return Response({"error": "Payment plan not found"}, status=404)

        agreement = self.service.create_agreement(unit, tenant, plan)
        serializer = RentalAgreementSerializer(agreement)
        return Response(serializer.data, status=201)

    def get(self, request):
        """Get all tenants aggreement"""
        agreements = self.service.get_all_agreements_for_tenant(request.user.pkid)
        serializer = RentalAgreementSerializer(agreements, many=True)
        return Response(serializer.data)


class RentalAgreementListView(APIView):
    permission_classes = [IsAuthenticated]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.service = RentalAgreementService()

    def get(self, request):
        agreements = self.service.get_agreements_for_user(request.user)
        serializer = RentalAgreementSerializer(agreements, many=True)
        return Response(serializer.data)


class RentalAgreementDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.service = RentalAgreementService()

    def get(self, request, agreement_id):
        try:
            agreement = self.service.get_agreement_for_user(agreement_id, request.user)
        except ValueError:
            return Response({"error": "Agreement not found"}, status=404)
        except PermissionDenied as e:
            return Response({"error": str(e)}, status=403)
        serializer = RentalAgreementSerializer(agreement)
        return Response(serializer.data)


class AvailablePaymentOptionsView(APIView):
    permission_classes = [IsAuthenticated]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.service = RentalAgreementService()

    def get(self, request, agreement_id):
        try:
            agreement = self.service.get_agreement_for_user(agreement_id, request.user)
        except ValueError:
            return Response({"error": "Agreement not found"}, status=404)
        except PermissionDenied as e:
            return Response({"error": str(e)}, status=403)
        options = self.service.get_available_payment_options(agreement)
        return Response(options)


class MakePaymentView(APIView):
    permission_classes = [IsAuthenticated, CanManageRentalAgreement]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.service = RentalAgreementService()

    def post(self, request, agreement_id):
        agreement = self.service.get_by_id(agreement_id)
        if not agreement:
            return Response({"error": "Agreement not found"}, status=404)
        serializer = MakePaymentSerializer(data=request.data)
        if serializer.is_valid():
            try:
                print("### got to the start")
                payment = self.service.make_payment(
                    agreement=agreement,
                    amount=serializer.validated_data["amount"],
                    payment_method=serializer.validated_data["payment_method"],
                    phone_number=serializer.validated_data.get("phone_number"),
                    provider=serializer.validated_data.get("provider"),
                )
                print("### made the payment")
                return Response(
                    PaymentSerializer(payment).data, status=status.HTTP_201_CREATED
                )
            except Exception as e:
                return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# ----------------------------------------------------------------------
# Payment Views
# ----------------------------------------------------------------------
class PaymentListView(APIView):
    permission_classes = [IsAuthenticated]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.agreement_service = RentalAgreementService()
        self.payment_service = PaymentService()

    def get(self, request):
        agreement_id = request.query_params.get("agreement")
        if not agreement_id:
            return Response({"error": "agreement query parameter required"}, status=400)
        try:
            agreement = self.agreement_service.get_agreement_for_user(
                agreement_id, request.user
            )
        except ValueError:
            return Response({"error": "Agreement not found"}, status=404)
        except PermissionDenied as e:
            return Response({"error": str(e)}, status=403)
        payments = self.payment_service.get_payments_for_agreement(agreement.id)
        serializer = PaymentSerializer(payments, many=True)
        return Response(serializer.data)


class TerminateAgreementView(APIView):
    permission_classes = [IsAuthenticated]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.service = RentalAgreementService()

    def post(self, request, agreement_id):
        try:
            reason = request.data.get("reason", "")
            mutual_agreement = request.data.get("mutual_agreement", False)
            agreement = self.service.terminate_agreement(
                agreement_id=agreement_id,
                requested_by_user=request.user,
                reason=reason,
                mutual_agreement=mutual_agreement,
            )
            serializer = RentalAgreementSerializer(agreement)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except PermissionDenied as e:
            return Response({"error": str(e)}, status=status.HTTP_403_FORBIDDEN)


class RentalAgreementDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, agreement_id):
        service = RentalAgreementService()
        agreement = service.get_by_id(agreement_id)
        if not agreement:
            return Response({"error": "Not found"}, status=404)
        # Check permission: landlord/manager can view if they own/manage the property
        if not user_can_manage_agreement(request.user, agreement):
            return Response({"error": "Permission denied"}, status=403)
        serializer = RentalAgreementDetailSerializer(agreement)
        return Response(serializer.data)
