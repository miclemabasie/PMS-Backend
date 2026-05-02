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
    TerminateAgreementView,
    RentalAgreementListView,
    RentalAgreementDetailView,
    VerifyPaymentView,
    PublicSubscriptionPlanListView,
    AdminSubscriptionPlanListCreateView,
    AdminSubscriptionPlanDetailView,
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
    path("agreements/all/", RentalAgreementListView.as_view(), name="agreements-all"),
    path(
        "agreements/<uuid:agreement_id>/detail/",
        RentalAgreementDetailView.as_view(),
        name="agreement-detail-payments",
    ),
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
    path(
        "agreements/<uuid:agreement_id>/terminate/",
        TerminateAgreementView.as_view(),
        name="agreement-terminate",
    ),
    path(
        "verify/<uuid:payment_id>/", VerifyPaymentView.as_view(), name="verify-payment"
    ),
    # Public (authenticated) list of active subscription plans
    path(
        "subscription-plans/",
        PublicSubscriptionPlanListView.as_view(),
        name="subscription-plans-list",
    ),
    # Admin endpoints (full management)
    path(
        "admin/subscription-plans/",
        AdminSubscriptionPlanListCreateView.as_view(),
        name="admin-subscription-plans",
    ),
    path(
        "admin/subscription-plans/<uuid:pk>/",
        AdminSubscriptionPlanDetailView.as_view(),
        name="admin-subscription-plan-detail",
    ),
]
