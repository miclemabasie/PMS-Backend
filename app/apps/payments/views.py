# apps/agreements/views.py

import logging

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, viewsets, permissions
from rest_framework.permissions import IsAuthenticated, IsAdminUser
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
    ManualPaymentSerializer,
    AgreementAcceptanceSerializer,
    RentalAgreementCreateSerializer
)
from .permissions import (
    IsLandlordOrManagerOrSuperAdminForUnit,
    CanManageRentalAgreement,
)
from django.core.exceptions import PermissionDenied
from .serializers import SubscriptionPlanSerializer
from .services import SubscriptionPlanService

from django.core.exceptions import ObjectDoesNotExist

logger = logging.getLogger(__name__)


# ----------------------------------------------------
# Payment Plan Views
# ----------------------------------------------------
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


# ----------------------------------------------------
# Rental Agreement Views
# ----------------------------------------------------
class RentalAgreementCreateView(APIView):
    permission_classes = [IsAuthenticated, IsLandlordOrManagerOrSuperAdminForUnit]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.service = RentalAgreementService()
        self.plan_service = PaymentPlanService()
        self.unit_service = UnitService()

    # def post(self, request):
    #     unit_id = request.data.get("unit_id")
    #     tenant_id = request.data.get("tenant_id")
    #     plan_id = request.data.get("payment_plan_id")

    #     if not self.unit_service.user_can_manage_unit(request.user, unit_id):
    #         return Response(
    #             {
    #                 "error": "You do not have permission to create an agreement for this unit."
    #             },
    #             status=403,
    #         )

    #     unit = self.unit_service.get_by_id(unit_id)
    #     tenant = get_object_or_404(Tenant, id=tenant_id)
    #     plan = self.plan_service.get_by_id(plan_id)
    #     if not plan:
    #         return Response({"error": "Payment plan not found"}, status=404)

    #     agreement = self.service.create_agreement(unit, tenant, plan)
    #     serializer = RentalAgreementSerializer(agreement)
    #     return Response(serializer.data, status=201)

    def post(self, request):
        serializer = RentalAgreementCreateSerializer(data=request.data)
        if serializer.is_valid():
            # Fetch objects
            unit = self.unit_service.get_by_id(serializer.validated_data['unit_id'])
            if not unit:
                return Response({"error": "Unit not found"}, status=404)

            tenant = get_object_or_404(Tenant, id=serializer.validated_data['tenant_id'])

            plan = self.plan_service.get_by_id(serializer.validated_data['payment_plan_id'])
            if not plan:
                return Response({"error": "Payment plan not found"}, status=404)

            service = RentalAgreementService()
            try:
                agreement = service.create_agreement(
                    unit=unit,
                    tenant=tenant,
                    payment_plan=plan,
                    terms_template_id=serializer.validated_data.get('terms_template_id'),
                    custom_terms=serializer.validated_data.get('terms_text'),
                )
                output = RentalAgreementSerializer(agreement)
                return Response(output.data, status=201)
            except ValueError as e:
                return Response({"error": str(e)}, status=400)
        return Response(serializer.errors, status=400)

    def get(self, request):
        """Get all tenants aggreement"""
        agreements = self.service.get_all_agreements_for_tenant(request.user.pkid)
        serializer = RentalAgreementSerializer(agreements, many=True)
        return Response(serializer.data)


# apps/payments/views.py (add this class)

class RentalAgreementUpdateTermsView(APIView):
    permission_classes = [IsAuthenticated, CanManageRentalAgreement]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.service = RentalAgreementService()

    def patch(self, request, agreement_id):
        try:
            agreement = self.service.get_agreement_for_user(agreement_id, request.user)
        except ValueError:
            return Response({"error": "Agreement not found"}, status=404)
        except PermissionDenied as e:
            return Response({"error": str(e)}, status=403)

        terms_text = request.data.get("terms_text")
        if terms_text is None:
            return Response({"error": "terms_text is required"}, status=400)

        # Update only the terms field
        agreement.terms_text = terms_text
        agreement.save(update_fields=["terms_text", "updated_at"])

        # Optionally log the update
        from apps.payments.services import AuditService
        AuditService.log(
            actor=request.user,
            action="update_terms",
            target=agreement,
            changes={"terms_text": terms_text[:100] + "..." if len(terms_text) > 100 else terms_text},
        )

        serializer = RentalAgreementSerializer(agreement)
        return Response(serializer.data, status=200)

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
        idempotency_key = request.headers.get("Idempotency-Key")
        serializer = MakePaymentSerializer(data=request.data)
        agreement = self.service.get_agreement_for_user(agreement_id, request.user)
        if serializer.is_valid():
            try:
                result = self.service.make_payment_with_idempotency(
                    agreement=agreement,
                    amount=serializer.validated_data["amount"],
                    payment_method=serializer.validated_data["payment_method"],
                    phone_number=serializer.validated_data.get("phone_number"),
                    provider=serializer.validated_data.get("provider"),
                    months=serializer.validated_data.get("months"),
                    installment_index=serializer.validated_data.get(
                        "installment_index"
                    ),
                    idempotency_key=idempotency_key,
                )
                return Response(result, status=status.HTTP_201_CREATED)
            except Exception as e:
                logger.exception("make_payment failed for agreement %s", agreement_id)
                return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        logger.warning(
            "MakePaymentView validation failed for agreement %s: %s",
            agreement_id,
            serializer.errors,
        )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# ----------------------------------------------------
# Payment Views
# ----------------------------------------------------
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


class VerifyPaymentView(APIView):
    permission_classes = [IsAuthenticated]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.service = RentalAgreementService()

    def get(self, request, payment_id):
        try:
            result = self.service.verify_payment(payment_id)
            return Response(result, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


# ----------------------------------------------------
# Public list – anyone authenticated can see active plans
# ----------------------------------------------------
class PublicSubscriptionPlanListView(APIView):
    permission_classes = [IsAuthenticated]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.service = SubscriptionPlanService()

    def get(self, request):
        plans = self.service.get_active_plans()
        serializer = SubscriptionPlanSerializer(plans, many=True)
        return Response(serializer.data)


# ----------------------------------------------------
# Admin management – full CRUD
# ----------------------------------------------------
class AdminSubscriptionPlanListCreateView(APIView):
    permission_classes = [IsAdminUser]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.service = SubscriptionPlanService()

    def get(self, request):
        """List all plans (including inactive) – admin only."""
        plans = self.service.get_all()  # from BaseService
        serializer = SubscriptionPlanSerializer(plans, many=True)
        return Response(serializer.data)

    def post(self, request):
        serializer = SubscriptionPlanSerializer(data=request.data)
        if serializer.is_valid():
            plan = self.service.create_plan(serializer.validated_data)
            output = SubscriptionPlanSerializer(plan)
            return Response(output.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class AdminSubscriptionPlanDetailView(APIView):
    permission_classes = [IsAdminUser]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.service = SubscriptionPlanService()

    def get(self, request, pk):
        plan = self.service.get_by_id(pk)
        if not plan:
            return Response({"detail": "Not found"}, status=status.HTTP_404_NOT_FOUND)
        serializer = SubscriptionPlanSerializer(plan)
        return Response(serializer.data)

    def put(self, request, pk):
        plan = self.service.get_by_id(pk)
        if not plan:
            return Response({"detail": "Not found"}, status=status.HTTP_404_NOT_FOUND)
        serializer = SubscriptionPlanSerializer(plan, data=request.data)
        if serializer.is_valid():
            updated = self.service.update_plan(pk, serializer.validated_data)
            output = SubscriptionPlanSerializer(updated)
            return Response(output.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        deleted = self.service.delete_plan(pk)
        if not deleted:
            return Response({"detail": "Not found"}, status=status.HTTP_404_NOT_FOUND)
        return Response(status=status.HTTP_204_NO_CONTENT)


class RecordManualPaymentView(APIView):
    permission_classes = [IsAuthenticated, CanManageRentalAgreement]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.service = RentalAgreementService()

    def post(self, request, agreement_id):
        serializer = ManualPaymentSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=400)

        try:
            payment = self.service.record_manual_payment(
                agreement_id=agreement_id,
                amount=serializer.validated_data["amount"],
                payment_method=serializer.validated_data["payment_method"],
                payment_date=serializer.validated_data.get("payment_date"),
                notes=serializer.validated_data.get("notes", ""),
                recorded_by_user=request.user,
            )

            from apps.payments.services import AuditService

            AuditService.log(
                actor=request.user,
                action="manual_payment",
                target=payment,
                changes={"amount": payment.amount, "method": payment.payment_method},
            )
            return Response(PaymentSerializer(payment).data, status=201)
        except ValueError as e:
            return Response({"error": str(e)}, status=400)


class PaymentWebhookView(APIView):
    permission_classes = []
    authentication_classes = []

    def post(self, request, gateway_name):
        service = PaymentService()
        try:
            # Pass both raw body (for signature) and parsed data
            result = service.process_webhook(
                gateway_name,
                request.data,  # parsed dict
                request.headers,
                request.body,  # raw bytes
            )
            return Response(result, status=200)
        except ValueError as e:
            return Response({"error": str(e)}, status=400)
        except Exception:
            logger.exception("Webhook error")
            return Response({"error": "Internal error"}, status=500)



class AgreementAcceptView(APIView):
    permission_classes = []  # No auth required for GET

    def get(self, request, token):
        """Public GET: fetch agreement details by token."""
        service = RentalAgreementService()
        try:
            agreement = service.repository.get_by_acceptance_token(token)
            if not agreement:
                return Response({"error": "Agreement not found"}, status=404)
            if agreement.is_active:
                return Response({"error": "Agreement already accepted"}, status=400)
            serializer = RentalAgreementSerializer(agreement)
            return Response(serializer.data, status=200)
        except Exception as e:
            return Response({"error": str(e)}, status=400)

    def post(self, request, token):
        """POST: accept agreement (requires authentication)."""
        service = RentalAgreementService()
        try:
            agreement, acceptance = service.accept_agreement(
                token=token,
                user=request.user,
                ip_address=self.get_client_ip(request),
                user_agent=request.META.get("HTTP_USER_AGENT", ""),
            )
            serializer = AgreementAcceptanceSerializer(acceptance)
            return Response(serializer.data, status=200)
        except ValueError as e:
            return Response({"error": str(e)}, status=400)
        except PermissionError as e:
            return Response({"error": str(e)}, status=403)

    def get_client_ip(self, request):
        x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        if x_forwarded_for:
            ip = x_forwarded_for.split(",")[0]
        else:
            ip = request.META.get("REMOTE_ADDR")
        return ip


class AgreementAcceptanceDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, agreement_id):
        service = RentalAgreementService()
        try:
            acceptance = service.get_acceptance_data(agreement_id)
            # Permission check
            agreement = acceptance.agreement
            user = request.user
            print("### we are here")
            if not (user.is_superuser or
                    (hasattr(user, "owner_profile") and agreement.unit.property.ownership_records.filter(owner=user.owner_profile).exists()) or
                    (hasattr(user, "tenant_profile") and user.tenant_profile == agreement.tenant)):
                print("### we are here 2")

                return Response({"detail": "Permission denied"}, status=403)
            serializer = AgreementAcceptanceSerializer(acceptance)
            return Response(serializer.data)
        except ValueError as e:
            print("### we are here 3", e)
            return Response({"error": str(e)}, status=404)





class ValidatePINView(APIView):
    """
    Validate the current user's owner payment PIN.
    POST: { "pin": "1234" }
    Returns 200 if valid, 400 otherwise.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        pin = request.data.get("pin")
        if not pin:
            return Response({"detail": "PIN is required."}, status=status.HTTP_400_BAD_REQUEST)

        user = request.user
        try:
            owner = user.owner_profile
        except ObjectDoesNotExist:
            return Response({"detail": "User is not an owner."}, status=status.HTTP_400_BAD_REQUEST)

        if owner.check_payment_pin(pin):
            return Response({"valid": True}, status=status.HTTP_200_OK)
        else:
            return Response({"valid": False, "detail": "Invalid PIN."}, status=status.HTTP_400_BAD_REQUEST)


class RecordManualPaymentView(APIView):
    permission_classes = [IsAuthenticated, CanManageRentalAgreement]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.service = RentalAgreementService()

    def post(self, request, agreement_id):
        # Check subscription status
        try:
            owner = request.user.owner_profile
        except ObjectDoesNotExist:
            return Response({"detail": "User is not an owner."}, status=403)

        if not owner.has_active_subscription():
            return Response(
                {"detail": "Manual payments are only available for subscribed landlords."},
                status=403
            )

        # Validate PIN
        pin = request.data.get("pin")
        if not pin:
            return Response({"detail": "Payment PIN is required."}, status=400)
        if not owner.check_payment_pin(pin):
            return Response({"detail": "Invalid PIN."}, status=400)

        # Proceed with manual payment
        serializer = ManualPaymentSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=400)

        try:
            payment = self.service.record_manual_payment(
                agreement_id=agreement_id,
                amount=serializer.validated_data["amount"],
                payment_method=serializer.validated_data["payment_method"],
                payment_date=serializer.validated_data.get("payment_date"),
                notes=serializer.validated_data.get("notes", ""),
                recorded_by_user=request.user,
            )
            # Trigger receipt generation
            from apps.payments.tasks import generate_receipt_task
            generate_receipt_task.delay(str(payment.id))

            from apps.payments.services import AuditService
            AuditService.log(
                actor=request.user,
                action="manual_payment",
                target=payment,
                changes={"amount": payment.amount, "method": payment.payment_method},
            )
            return Response(PaymentSerializer(payment).data, status=201)
        except ValueError as e:
            return Response({"error": str(e)}, status=400)