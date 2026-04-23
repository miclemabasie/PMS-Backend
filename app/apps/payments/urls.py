from django.urls import path
from .views import (
    PaymentPlanListCreateView,
    RentalAgreementCreateView,
    AvailablePaymentOptionsView,
    MakePaymentView,
)

app_name = "payments"

urlpatterns = [
    path(
        "payment-plans/", PaymentPlanListCreateView.as_view(), name="payment-plan-list"
    ),
    path("agreements/", RentalAgreementCreateView.as_view(), name="agreement-create"),
    path(
        "agreements/<uuid:agreement_id>/options/",
        AvailablePaymentOptionsView.as_view(),
        name="payment-options",
    ),
    path(
        "agreements/<uuid:agreement_id>/pay/",
        MakePaymentView.as_view(),
        name="make-payment",
    ),
]
