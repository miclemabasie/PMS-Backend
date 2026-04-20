from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from .models import PaymentPlan, RentalAgreement, Unit, Tenant
from .services import PaymentPlanService, RentalAgreementService
from .serializers import (
    PaymentPlanSerializer,
    InstallmentSerializer,
    RentalAgreementSerializer,
    PaymentSerializer,
    PaymentOptionSerializer,
    MakePaymentSerializer,
)


class PaymentPlanListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        # Only show plans owned by the user's landlord profile? For now all
        plans = PaymentPlan.objects.filter(is_active=True)
        serializer = PaymentPlanSerializer(plans, many=True)
        return Response(serializer.data)

    def post(self, request):
        serializer = PaymentPlanSerializer(data=request.data)
        if serializer.is_valid():
            plan = PaymentPlanService.create_plan(serializer.validated_data)
            return Response(PaymentPlanSerializer(plan).data, status=201)
        return Response(serializer.errors, status=400)


class RentalAgreementCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        unit_id = request.data.get("unit_id")
        tenant_id = request.data.get("tenant_id")
        plan_id = request.data.get("payment_plan_id")

        unit = get_object_or_404(Unit, id=unit_id)
        tenant = get_object_or_404(Tenant, id=tenant_id)
        plan = get_object_or_404(PaymentPlan, id=plan_id)

        agreement = RentalAgreementService.create_agreement(unit, tenant, plan)
        serializer = RentalAgreementSerializer(agreement)
        return Response(serializer.data, status=201)


class AvailablePaymentOptionsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, agreement_id):
        agreement = get_object_or_404(RentalAgreement, id=agreement_id)
        options = RentalAgreementService.get_available_payment_options(agreement)
        return Response(options)


class MakePaymentView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, agreement_id):
        agreement = get_object_or_404(RentalAgreement, id=agreement_id)
        serializer = MakePaymentSerializer(data=request.data)
        if serializer.is_valid():
            try:
                payment = RentalAgreementService.make_payment(
                    agreement=agreement,
                    amount=serializer.validated_data["amount"],
                    payment_method=serializer.validated_data["payment_method"],
                    phone_number=serializer.validated_data.get("phone_number"),
                    provider=serializer.validated_data.get("provider"),
                )
                return Response(PaymentSerializer(payment).data, status=201)
            except Exception as e:
                return Response({"error": str(e)}, status=400)
        return Response(serializer.errors, status=400)
