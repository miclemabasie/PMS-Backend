from rest_framework import serializers
from .models import PaymentPlan, Installment, RentalAgreement, Payment
from apps.properties.serializers import UnitSerializer
from apps.tenants.serializers import TenantMinimalSerializer
from decimal import Decimal


class InstallmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Installment
        fields = ["id", "percent", "due_date", "order_index"]


class PaymentPlanSerializer(serializers.ModelSerializer):
    installments = InstallmentSerializer(many=True, read_only=True)

    class Meta:
        model = PaymentPlan
        fields = "__all__"


class RentalAgreementSerializer(serializers.ModelSerializer):
    unit_name = serializers.SerializerMethodField(read_only=True)
    tenant_name = serializers.CharField(
        source="tenant.user.get_full_name", read_only=True
    )
    payment_plan_name = serializers.CharField(
        source="payment_plan.name", read_only=True
    )

    class Meta:
        model = RentalAgreement
        fields = "__all__"

    def get_unit_name(self, obj):
        return (
            f"{obj.unit.property.name} - {obj.unit.unit_type} - {obj.unit.unit_number}"
            if obj.unit.unit_number
            else f"{obj.unit.property.name} - {obj.unit.unit_type}"
        )


class PaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = "__all__"


class MakePaymentSerializer(serializers.Serializer):
    amount = serializers.DecimalField(max_digits=10, decimal_places=0)
    payment_method = serializers.ChoiceField(
        choices=["mtn_momo", "orange_money", "bank_transfer", "cash"]
    )
    phone_number = serializers.CharField(required=False, allow_blank=True)
    provider = serializers.CharField(required=False, allow_blank=True)


class RentalAgreementDetailSerializer(serializers.ModelSerializer):
    unit = UnitSerializer(read_only=True)
    tenant = TenantMinimalSerializer(read_only=True)
    payment_plan = serializers.StringRelatedField()
    payments = PaymentSerializer(many=True, read_only=True)
    total_paid = serializers.SerializerMethodField()
    remaining_balance = serializers.SerializerMethodField()

    class Meta:
        model = RentalAgreement
        fields = "__all__"

    def get_total_paid(self, obj):
        if obj.payment_plan.mode == "monthly":
            # sum of completed payments?
            return sum(p.amount for p in obj.payments.filter(status="completed"))
        else:
            return Decimal(obj.installment_status.get("total_paid", 0))

    def get_remaining_balance(self, obj):
        if obj.payment_plan.mode == "monthly":
            monthly_rent = obj.unit.monthly_rent or obj.unit.default_rent_amount
            # calculate unpaid periods? simpler: just return 0 for now
            return Decimal(0)
        else:
            return Decimal(obj.installment_status.get("total_remaining", 0))
