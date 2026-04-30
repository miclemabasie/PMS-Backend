# apps/payments/managers/payment_manager.py
"""
Main payment manager - orchestrates everything
"""

import logging
from typing import Dict, Any, Optional, Tuple
from decimal import Decimal
from django.db import transaction
from django.utils import timezone
from apps.properties.models import Appointment
from apps.payments.models import (
    Payment,
    PaymentMethod,
    PaymentGateway,
    PlatformFeeConfiguration,
    EscrowTransaction,
    WebhookEvent,
)
import hashlib
from apps.payments.gateway_SDKs.gateway_factory import gateway_factory
from apps.payments.utils.rent_calculator import PaymentCalculator

logger = logging.getLogger(__name__)


class PaymentManager:
    """Orchestrates all payment operations"""

    def __init__(self, gateway_code: str = None):
        self.gateway = None
        self.gateway_code = gateway_code or self._get_default_gateway_code()
        self._initialize_gateway()
        self.is_staging = self._check_if_staging()

    def _check_if_staging(self):
        """Check if we're in staging mode"""
        from django.conf import settings

        return getattr(settings, "STAGING_MODE", False) or getattr(
            settings, "DEBUG", False
        )

    def _handle_staging_auto_completion(self, payment):
        """Special handling for staging auto-completed payments"""
        if self.is_staging and payment.current_status == "completed":
            from apps.payments.models import EscrowTransaction

            if not EscrowTransaction.objects.filter(
                payment=payment, transaction_type="hold"
            ).exists():
                self._create_escrow_transaction(payment)
                logger.info(
                    f"Staging: Created escrow for auto-completed payment {payment.id}"
                )

    def _get_default_gateway_code(self) -> str:
        """Get default gateway from database or settings"""
        try:
            default_gateway = PaymentGateway.objects.filter(
                is_default=True, is_active=True
            ).first()
            return default_gateway.code if default_gateway else "smobilpay_default"
        except:
            return "smobilpay_default"

    def _initialize_gateway(self):
        """Initialize payment gateway"""
        try:
            gateway_config = self._get_gateway_config()
            self.gateway = gateway_factory.create_gateway(
                gateway_type=gateway_config["gateway_type"], config=gateway_config
            )
            logger.info(f"Payment gateway initialized: {self.gateway_code}")
        except Exception as e:
            logger.error(f"Failed to initialize gateway {self.gateway_code}: {str(e)}")
            raise

    def _get_gateway_config(self) -> Dict[str, Any]:
        """Get gateway configuration from database"""
        try:
            gateway = PaymentGateway.objects.get(code=self.gateway_code, is_active=True)
            return {
                "gateway_type": gateway.gateway_type,
                "name": gateway.name,
                "config": gateway.config,
                "supports_cashin": gateway.supports_cashin,
                "supports_cashout": gateway.supports_cashout,
            }
        except PaymentGateway.DoesNotExist:
            # Fallback to settings
            from django.conf import settings

            return settings.PAYMENT_GATEWAYS.get(self.gateway_code, {})

    def initiate_payment(
        self,
        appointment_id: str,
        payment_method_code: str,
        customer_data: Dict[str, Any],
        metadata: Dict[str, Any] = None,
        execute_immediately: bool = True,  # New parameter to control execution
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Initiate AND optionally execute payment - SINGLE ENDPOINT FOR FRONTEND

        Args:
            execute_immediately: If True, executes payment immediately.
                                If False, just creates payment intent.

        Returns: (success, payment_data)
        """
        with transaction.atomic():
            try:
                # 1. Get appointment and validate
                appointment = Appointment.objects.select_related(
                    "service", "client", "provider"
                ).get(id=appointment_id)

                # 2. Get payment method
                payment_method = PaymentMethod.objects.get(
                    method_code=payment_method_code,
                    is_active=True,
                    gateway__is_active=True,
                )
                print("this is the service price", appointment.service.price)
                payment_calculator = PaymentCalculator(appointment.service.price)

                # 4. Create payment record
                payment = Payment.objects.create(
                    appointment=appointment,
                    payment_method=payment_method,
                    amount=payment_calculator.calculate_payment(),
                    currency=appointment.currency,
                    platform_fee=payment_calculator.get_platform_fee(),
                    gateway_fee=payment_calculator.get_gateway_fee(),
                    provider_payout_amount=payment_calculator.get_provider_payout(),
                    from_user=appointment.client.user,
                    to_user=appointment.provider.user,
                    payment_method_details={
                        "customer_phone": customer_data.get("phone_number"),
                        "customer_email": customer_data.get("email"),
                        "service_number": customer_data.get("service_number"),
                    },
                    metadata=metadata or {},
                )

                # 5. Create payment intent with gateway
                gateway_response = self.gateway.create_payment_intent(
                    amount=payment_calculator.get_customer_total(),
                    currency=appointment.currency,
                    payment_method=payment_method_code,
                    customer_data=customer_data,
                    metadata={
                        "payment_id": str(payment.id),
                        "appointment_id": str(appointment.id),
                        "frontend_token": str(payment.frontend_token),
                    },
                )

                # 6. Check if payment intent creation was successful
                if gateway_response.get("status") == "failed":
                    payment.current_status = "failed"
                    payment.save()
                    return False, {
                        "error": gateway_response.get(
                            "error", "Gateway payment initiation failed"
                        ),
                        "payment_id": str(payment.id),
                    }

                # 7. Update payment with gateway response
                payment.gateway_reference = gateway_response.get("gateway_reference")

                # 8. EXECUTE PAYMENT IMMEDIATELY if requested
                if execute_immediately:
                    # For gateways that require authorization data, we need to check customer_data
                    # SmobilPay typically uses phone number as authorization
                    authorization_data = {
                        "phone_number": customer_data.get("phone_number"),
                        # Add any other authorization data needed by the gateway
                        **gateway_response.get("authorization_required_fields", {}),
                    }

                    # Execute the payment
                    execution_response = self.gateway.execute_payment(
                        gateway_reference=payment.gateway_reference,
                        customer_authorization=authorization_data,
                    )

                    if execution_response.get("status") in [
                        "completed",
                        "success",
                        "paid",
                        "pending",
                    ]:

                        print("########### the payment was done success")
                        # Payment executed successfully
                        payment.current_status = "pending"
                        payment.gateway_transaction_id = execution_response.get(
                            "gateway_transaction_id"
                        )
                        payment.processed_at = timezone.now()
                        payment.payment_status = "held_in_escrow"
                        payment.escrow_status = "held"
                        payment.receipt_number = execution_response.get(
                            "receipt_number"
                        )

                        # Add execution details to callback data
                        payment.frontend_callback_data = {
                            "executed": True,
                            "gateway_transaction_id": payment.gateway_transaction_id,
                            "receipt_number": payment.receipt_number,
                            "execution_timestamp": timezone.now().isoformat(),
                            **gateway_response.get("gateway_data", {}),
                        }

                        payment.save()
                        # Trigger payment completed event
                        # self._trigger_payment_event("payment_completed", payment)

                        return True, {
                            "ptn": str(
                                execution_response.get("gateway_transaction_id")
                            ),
                            "payment_id": str(payment.id),
                            "frontend_token": str(payment.frontend_token),
                            "status": payment.current_status,
                            "amount": float(payment.amount),
                            "currency": payment.currency,
                            "gateway_transaction_id": payment.gateway_transaction_id,
                            "receipt_number": payment.receipt_number,
                            "executed": True,
                            "message": "Payment completed successfully",
                            "fee_breakdown": payment_calculator.get_payment_breakdown(),
                            "payment_method": {
                                "code": payment_method.method_code,
                                "name": payment_method.get_method_code_display(),
                                "instructions": payment_method.instructions,
                            },
                        }
                    else:
                        # Execution failed
                        payment.current_status = "failed"
                        payment.save()

                        # Trigger payment failed event
                        self._trigger_payment_event("payment_failed", payment)

                        return False, {
                            "error": execution_response.get(
                                "error", "Payment execution failed"
                            ),
                            "payment_id": str(payment.id),
                            "frontend_token": str(payment.frontend_token),
                            "status": "failed",
                        }
                else:
                    # Just create payment intent without execution (original behavior)
                    payment.current_status = "pending"
                    payment.frontend_callback_data = {
                        "requires_action": gateway_response.get(
                            "requires_action", False
                        ),
                        "next_action": gateway_response.get("next_action"),
                        "redirect_url": gateway_response.get("redirect_url"),
                        "gateway_data": gateway_response.get("gateway_data", {}),
                    }
                    payment.save()

                    # Trigger payment initiated event
                    self._trigger_payment_event("payment_initiated", payment)

                    return True, {
                        "payment_id": str(payment.id),
                        "frontend_token": str(payment.frontend_token),
                        "status": payment.current_status,
                        "amount": float(payment.amount),
                        "currency": payment.currency,
                        "requires_action": gateway_response.get(
                            "requires_action", False
                        ),
                        "next_action": gateway_response.get("next_action"),
                        "redirect_url": gateway_response.get("redirect_url"),
                        "executed": False,
                        "fee_breakdown": payment_calculator.get_payment_breakdown,
                        "payment_method": {
                            "code": payment_method.method_code,
                            "name": payment_method.get_method_code_display(),
                            "instructions": payment_method.instructions,
                        },
                    }

            except Exception as e:
                logger.error(f"Payment initiation failed: {str(e)}")
            return False, {"error": str(e), "code": "payment_initiation_failed"}

    def confirm_payment(
        self, frontend_token: str, authorization_data: Dict[str, Any]
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Confirm/execute payment after customer authorization
        """
        try:
            payment = Payment.objects.get(
                frontend_token=frontend_token, current_status="pending"
            )

            # Execute payment with gateway
            gateway_response = self.gateway.execute_payment(
                gateway_reference=payment.gateway_reference,
                customer_authorization=authorization_data,
            )

            if gateway_response.get("status") in ["completed", "success"]:
                payment.current_status = "completed"
                payment.gateway_transaction_id = gateway_response.get(
                    "gateway_transaction_id"
                )
                payment.processed_at = timezone.now()
                payment.payment_status = "held_in_escrow"
                payment.escrow_status = "held"
                payment.save()

                # Trigger payment completed event
                self._trigger_payment_event("payment_completed", payment)

                # Create escrow transaction
                self._create_escrow_transaction(payment)

                return True, {
                    "payment_id": str(payment.id),
                    "status": "completed",
                    "transaction_id": payment.gateway_transaction_id,
                    "receipt_number": gateway_response.get("receipt_number"),
                    "message": "Payment completed successfully",
                }
            else:
                payment.current_status = "failed"
                payment.save()

                self._trigger_payment_event("payment_failed", payment)

                return False, {
                    "error": gateway_response.get("error", "Payment execution failed"),
                    "status": "failed",
                }

        except Payment.DoesNotExist:
            return False, {"error": "Payment not found or already processed"}
        except Exception as e:
            logger.error(f"Payment confirmation failed: {str(e)}")
            return False, {"error": str(e)}

    # Update the get_payment_status method:

    logger = logging.getLogger(__name__)

    def get_payment_status(self, frontend_token: str) -> Dict[str, Any]:
        """
        Get payment status for frontend polling with webhook fallback logic
        If webhook wasn't called, this method replicates webhook behavior
        """
        try:
            payment = Payment.objects.get(frontend_token=frontend_token)

            # If payment is already completed via webhook, return status
            if payment.current_status == "completed":
                return self._build_payment_response(payment, gateway_response={})

            # If pending, check with gateway via verifytx
            if payment.current_status == "pending":
                gateway_response = self.gateway.verify_payment(
                    gateway_reference=payment.gateway_transaction_id
                )

                if gateway_response.get("status") in [
                    "completed",
                    "success",
                    "errored",
                    "pending",
                ]:
                    status = gateway_response.get("status", "").upper()

                    print("******************** we got the status", status)

                    # Handle successful payment (replicate webhook logic)
                    if status in ["SUCCESS", "COMPLETED", "PAID"]:
                        return self._handle_successful_payment_via_status_check(
                            payment, gateway_response
                        )

                    # Handle failed payment
                    elif status in ["FAILED", "ERROR", "ERRORED"]:
                        return self._handle_failed_payment_via_status_check(
                            payment, gateway_response
                        )

                    # Handle other statuses (pending, in process, etc.)
                    else:
                        logger.info(f"Payment {payment.id} is still {status}")
                        # Just return current status, don't update anything

            return self._build_payment_response(payment, gateway_response={})

        except Payment.DoesNotExist:
            return {"error": "Payment not found", "status": "not_found"}

    def _handle_successful_payment_via_status_check(
        self, payment: Payment, gateway_response: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Replicate webhook logic for successful payments when webhook wasn't called
        """
        try:
            # Check if we've already processed this payment
            if payment.current_status == "completed":
                return self._build_payment_response(payment, gateway_response={})

            # Double-check with gateway to ensure payment is really successful
            if not self._confirm_payment_status_with_gateway(payment):
                logger.warning(f"Payment {payment.id} not confirmed by gateway")
                return self._build_payment_response(payment, gateway_response={})

            # Use atomic transaction to ensure data consistency
            from django.db import transaction

            with transaction.atomic():
                # === REPLICATE WEBHOOK LOGIC ===

                # 1. Update payment status (same as webhook)
                payment.current_status = "completed"
                payment.status = "success"
                payment.escrow_status = "held"
                payment.processed_at = timezone.now()

                # Update gateway transaction ID if available
                if gateway_response.get("gateway_transaction_id"):
                    payment.gateway_transaction_id = gateway_response.get(
                        "gateway_transaction_id"
                    )

                payment.save()

                # 2. Create escrow transaction (same as webhook)
                if not self._escrow_already_exists(payment):
                    self._create_escrow_from_status_check(payment, gateway_response)

                # 3. Update appointment (same as webhook)
                if payment.appointment:
                    payment.appointment.status = "confirmed"
                    payment.appointment.payment_status = "held_in_escrow"
                    payment.appointment.save()

                # 4. Create a synthetic webhook event for tracking
                self._create_synthetic_webhook_event(payment, gateway_response)

                # 5. Trigger payment completion event
                self._trigger_payment_event("payment_completed", payment)

                logger.info(
                    f"Payment {payment.id} completed via status check (webhook fallback)"
                )

            return self._build_payment_response(
                payment, gateway_response=gateway_response
            )

        except Exception as e:
            logger.exception(f"Error handling successful payment via status check: {e}")
            # Return current state even if update failed
            return self._build_payment_response(payment, gateway_response={})

    def _handle_failed_payment_via_status_check(
        self, payment: Payment, gateway_response: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Replicate webhook logic for failed payments
        """
        try:
            if payment.current_status == "failed":
                return self._build_payment_response(
                    payment, gateway_response=gateway_response
                )

            payment.current_status = "failed"
            payment.status = "failed"
            payment.save()

            if payment.appointment:
                payment.appointment.status = "payment_failed"
                payment.appointment.save()

            # Create synthetic webhook event for tracking
            self._create_synthetic_webhook_event(payment, gateway_response)

            self._trigger_payment_event("payment_failed", payment)

            logger.info(f"Payment {payment.id} marked as failed via status check")

            return self._build_payment_response(
                payment, gateway_response=gateway_response
            )

        except Exception as e:
            logger.exception(f"Error handling failed payment via status check: {e}")
            return self._build_payment_response(payment, gateway_response={})

    def _confirm_payment_status_with_gateway(self, payment: Payment) -> bool:
        """
        Double-check payment status with gateway to be absolutely sure
        """
        try:
            # Call verifytx endpoint with PTN if available
            if payment.gateway_transaction_id:
                gateway_response = self.gateway.verify_payment(
                    gateway_reference=payment.gateway_transaction_id
                )
            else:
                gateway_response = self.gateway.verify_payment(
                    gateway_reference=payment.gateway_reference
                )

            status = gateway_response.get("status", "").upper()
            return status in ["SUCCESS", "COMPLETED", "PAID"]

        except Exception as e:
            logger.error(f"Failed to confirm payment status with gateway: {e}")
            return False

    def _escrow_already_exists(self, payment: Payment) -> bool:
        """Check if escrow already exists for this payment"""
        return EscrowTransaction.objects.filter(
            payment=payment, transaction_type="hold", status="completed"
        ).exists()

    def _create_escrow_from_status_check(
        self, payment: Payment, gateway_response: Dict[str, Any]
    ) -> bool:
        """
        Create escrow transaction from status check (replicates webhook logic)
        """
        try:
            EscrowTransaction.objects.create(
                payment=payment,
                transaction_type="hold",
                amount=payment.amount,
                currency=payment.currency,
                recipient_type="platform",
                status="completed",
                metadata={
                    "hold_reason": "Service payment held in escrow",
                    "appointment_id": (
                        str(payment.appointment.id) if payment.appointment else None
                    ),
                    "status_check_status": gateway_response.get("status", "unknown"),
                    "status_check_timestamp": timezone.now().isoformat(),
                    "gateway_transaction_id": payment.gateway_transaction_id,
                    "processed_via": "status_check_fallback",
                    "original_webhook_missing": True,
                    "gateway_response": gateway_response,
                },
                processed_at=timezone.now(),
            )
            return True
        except Exception as e:
            logger.error(f"Failed to create escrow from status check: {e}")
            return False

    def _create_synthetic_webhook_event(
        self, payment: Payment, gateway_response: Dict[str, Any]
    ) -> None:
        """
        Create a synthetic webhook event for tracking when we process via status check
        """
        try:
            # Create a unique signature hash similar to webhook
            signature_hash = hashlib.sha256(
                f"{payment.gateway_transaction_id}:status_check:{timezone.now().timestamp()}".encode()
            ).hexdigest()

            WebhookEvent.objects.create(
                source="smobilpay",
                event_type=f"payment.{gateway_response.get('status', 'unknown').lower()}",
                signature="SYNTHETIC_STATUS_CHECK",
                delivery_id=f"status_check_{payment.id}_{int(timezone.now().timestamp())}",
                ptn=payment.gateway_transaction_id or payment.gateway_reference,
                signature_hash=signature_hash,
                payload={
                    "raw": gateway_response,
                    "headers": {
                        "X-Delivery": f"status_check_{payment.id}",
                        "X-Ptn": payment.gateway_transaction_id
                        or payment.gateway_reference,
                        "X-Signature": "SYNTHETIC_STATUS_CHECK",
                    },
                    "body": gateway_response,
                },
                status="completed",
                payment=payment,
                processed_at=timezone.now(),
            )
        except Exception as e:
            logger.error(f"Failed to create synthetic webhook event: {e}")

    def _build_payment_response(
        self, payment: Payment, gateway_response: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Build consistent payment response
        """
        return {
            "payment_id": str(payment.id),
            "status": payment.current_status,
            "amount": float(payment.amount),
            "currency": payment.currency,
            "created_at": (
                payment.created_at.isoformat() if payment.created_at else None
            ),
            "processed_at": (
                payment.processed_at.isoformat() if payment.processed_at else None
            ),
            "payment_method": (
                payment.payment_method.get_method_code_display()
                if payment.payment_method
                else None
            ),
            "gateway_transaction_id": payment.gateway_transaction_id,
            "receipt_number": getattr(payment, "receipt_number", None),
            "escrow_status": payment.escrow_status,
            "appointment_status": (
                payment.appointment.status if payment.appointment else None
            ),
            "processed_via": (
                "webhook"
                if payment.current_status == "completed"
                and not getattr(payment, "_processed_via_status_check", False)
                else "status_check"
            ),
            "errorCode": gateway_response.get("errorCode", None),
            "errorMessage": gateway_response.get("errorMessage", None),
        }

    def _calculate_fees(
        self, amount: Decimal, payment_method: PaymentMethod, service: Any
    ) -> Dict[str, Decimal]:
        """
        Calculate all fees and breakdown
        """
        # Platform fee
        platform_fee_config = payment_method.fee_configuration
        print("this is fee configuration", platform_fee_config)
        if platform_fee_config:
            platform_fee = platform_fee_config.calculate_fee(amount)
            print("this is the platform fee", platform_fee)
        else:
            # Default 5% platform fee
            platform_fee = amount * Decimal("0.05")

        # Gateway fee (estimated, will be confirmed by gateway)
        # SmobilPay typically charges 1-2%
        gateway_fee = amount * Decimal("0.02")  # 2%

        # Provider payout (service amount minus provider fee if any)
        provider_payout = amount - platform_fee

        # Total amount customer pays
        total_amount = amount + platform_fee + gateway_fee

        return {
            "service_amount": amount,
            "platform_fee": platform_fee,
            "gateway_fee": gateway_fee,
            "provider_payout": provider_payout,
            "total_amount": total_amount,
            "breakdown": {
                "service_amount": float(amount),
                "platform_fee_percentage": (
                    float((platform_fee / amount) * 100) if amount > 0 else 0
                ),
                "gateway_fee_percentage": (
                    float((gateway_fee / amount) * 100) if amount > 0 else 0
                ),
                "provider_payout_percentage": (
                    float((provider_payout / amount) * 100) if amount > 0 else 0
                ),
            },
        }

    def _trigger_payment_event(self, event_type: str, payment: Payment):
        """Trigger payment events for escrow system"""
        # This would integrate with your existing EscrowTriggerEvent system
        # try:
        #     from apps.payments.models import EscrowTriggerEvent, EscrowTriggerType

        #     trigger_type = EscrowTriggerType.objects.filter(
        #         payment_event=event_type, is_active=True
        #     ).first()

        #     if trigger_type:
        #         EscrowTriggerEvent.objects.create(
        #             trigger_type=trigger_type,
        #             payment=payment,
        #             trigger_data={
        #                 "payment_id": str(payment.id),
        #                 "amount": float(payment.amount),
        #                 "status": payment.current_status,
        #                 "appointment_id": str(payment.appointment.id),
        #             },
        #         )
        # except Exception as e:
        #     logger.error(f"Failed to trigger payment event: {str(e)}")
        return True

    def _create_escrow_transaction(self, payment: Payment):
        """Create initial escrow transaction when payment is held"""
        try:
            from apps.payments.models import EscrowTransaction

            EscrowTransaction.objects.create(
                payment=payment,
                transaction_type="hold",
                amount=payment.amount,
                currency=payment.currency,
                recipient_type="platform",
                status="completed",
                metadata={
                    "hold_reason": "Service payment held in escrow",
                    "appointment_id": str(payment.appointment.id),
                },
            )
        except Exception as e:
            logger.error(f"Failed to create escrow transaction: {str(e)}")

    # Additional methods for refunds, cashouts, etc.
