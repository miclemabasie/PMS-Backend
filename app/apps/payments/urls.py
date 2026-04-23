# apps/agreements/urls.py

from django.urls import path
from .views import (
    PaymentPlanListCreateView,
    InstallmentListCreateView,
    RentalAgreementCreateView,
    RentalAgreementDetailView,
    AvailablePaymentOptionsView,
    MakePaymentView,
    PaymentListView,
)

app_name = "agreements"

urlpatterns = [
    # Payment Plans
    path(
        "payment-plans/", PaymentPlanListCreateView.as_view(), name="payment-plan-list"
    ),
    path(
        "payment-plans/<uuid:plan_id>/installments/",
        InstallmentListCreateView.as_view(),
        name="installment-list-create",
    ),
    # Rental Agreements
    path("agreements/", RentalAgreementCreateView.as_view(), name="agreement-create"),
    path(
        "agreements/<uuid:agreement_id>/",
        RentalAgreementDetailView.as_view(),
        name="agreement-detail",
    ),
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
    # Payments
    path("payments/", PaymentListView.as_view(), name="payment-list"),
]
