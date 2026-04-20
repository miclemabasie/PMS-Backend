from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from .models import PaymentPlan, RentalAgreement, Unit, Tenant
from .services import PaymentPlanService, RentalAgreementService
from .serializers import (
    PaymentPlanSerializer,
    RentalAgreementSerializer,
    PaymentSerializer,
    MakePaymentSerializer,
)


class PaymentPlanListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.service = PaymentPlanService()

    def get(self, request):
        plans = self.service.repository.find_active()
        serializer = PaymentPlanSerializer(plans, many=True)
        return Response(serializer.data)

    def post(self, request):
        serializer = PaymentPlanSerializer(data=request.data)
        if serializer.is_valid():
            plan = self.service.create(**serializer.validated_data)
            return Response(
                PaymentPlanSerializer(plan).data, status=status.HTTP_201_CREATED
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class RentalAgreementCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.service = RentalAgreementService()
        self.plan_service = PaymentPlanService()

    def post(self, request):
        unit_id = request.data.get("unit_id")
        tenant_id = request.data.get("tenant_id")
        plan_id = request.data.get("payment_plan_id")

        unit = get_object_or_404(Unit, id=unit_id)
        tenant = get_object_or_404(Tenant, id=tenant_id)
        plan = self.plan_service.get_by_id(plan_id)
        if not plan:
            return Response({"error": "Payment plan not found"}, status=404)

        agreement = self.service.create_agreement(unit, tenant, plan)
        serializer = RentalAgreementSerializer(agreement)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class AvailablePaymentOptionsView(APIView):
    permission_classes = [IsAuthenticated]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.service = RentalAgreementService()

    def get(self, request, agreement_id):
        agreement = get_object_or_404(RentalAgreement, id=agreement_id)
        options = self.service.get_available_payment_options(agreement)
        return Response(options)


class MakePaymentView(APIView):
    permission_classes = [IsAuthenticated]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.service = RentalAgreementService()

    def post(self, request, agreement_id):
        agreement = get_object_or_404(RentalAgreement, id=agreement_id)
        serializer = MakePaymentSerializer(data=request.data)
        if serializer.is_valid():
            try:
                payment = self.service.make_payment(
                    agreement=agreement,
                    amount=serializer.validated_data["amount"],
                    payment_method=serializer.validated_data["payment_method"],
                    phone_number=serializer.validated_data.get("phone_number"),
                    provider=serializer.validated_data.get("provider"),
                )
                return Response(
                    PaymentSerializer(payment).data, status=status.HTTP_201_CREATED
                )
            except Exception as e:
                return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
