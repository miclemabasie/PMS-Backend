from rest_framework import serializers
from .models import PaymentPlan, Installment, RentalAgreement, Payment


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
