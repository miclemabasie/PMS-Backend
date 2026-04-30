import logging
from typing import Dict, Optional, Any
from decimal import Decimal
from django.utils import timezone

from . import PaymentGatewayInterface
from clients.smobilpay_client import SmobilPayClient

logger = logging.getLogger(__name__)


class SmobilPayGateway(PaymentGatewayInterface):
    """SmobilPay (Maviance) gateway implementation for MTN/Orange Money"""

    # Update the __init__ method and add missing attributes:
    def __init__(self):
        self.client = None
        self.config = {}

        # Add these attributes
        self.supports_cashin = True
        self.supports_cashout = True
        self.supports_refunds = True  # Add this too
        self.supports_recurring = False  # Add this too

        self.supported_methods = {
            "mtn_momo": {
                "name": "MTN Mobile Money",
                "cashin_supported": True,
                "cashout_supported": True,
                "currencies": ["XAF"],
                "requires_service_number": True,
                "service_number_label": "MTN Phone Number",
                "validation_regex": r"^237[0-9]{9}$",
            },
            "orange_money": {
                "name": "Orange Money",
                "cashin_supported": True,
                "cashout_supported": True,
                "currencies": ["XAF"],
                "requires_service_number": True,
                "service_number_label": "Orange Phone Number",
                "validation_regex": r"^237[0-9]{9}$",
            },
        }

    # Update the initialize method to set attributes from config:
    def initialize(self, config: Dict[str, Any]) -> None:
        """Initialize SmobilPay gateway"""
        self.config = config

        # Set capabilities from config
        self.supports_cashin = config.get("supports_cashin", True)
        self.supports_cashout = config.get("supports_cashout", True)
        self.supports_refunds = config.get("supports_refunds", True)
        self.supports_recurring = config.get("supports_recurring", False)

        # Initialize the SDK client
        self.client = SmobilPayClient(
            api_url=config.get("api_url"),
            public_token=config.get("public_token"),
            secret_key=config.get("secret_key"),
            live_mode=config.get("live_mode", True),
        )

        logger.info(f"SmobilPay gateway initialized: {config.get('name')}")

    def execute_payment(
        self, gateway_reference: str, customer_authorization: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Execute payment (collection) on SmobilPay
        """
        try:
            # Get phone number from customer data
            customer_phone = customer_authorization.get("phone_number")
            if not customer_phone:
                return {"error": "Customer phone number required", "status": "failed"}

            # Execute collection
            collection_data = {
                "quoteId": gateway_reference,
                "customerPhonenumber": customer_phone,
                "customerEmailaddress": customer_authorization.get("email", ""),
                "serviceNumber": customer_phone,  # For MoMo, service number is phone number
                "trid": f"TRX-{timezone.now().timestamp()}",
            }

            collection_response = self.client.execute_collection(collection_data)

            if isinstance(collection_response, dict):
                if collection_response.get("ptn"):
                    return {
                        "gateway_transaction_id": collection_response.get("ptn"),
                        "status": (
                            "completed"
                            if collection_response.get("status").lower() == "success"
                            else "pending"
                        ),
                        "receipt_number": collection_response.get("receiptNumber"),
                        "verification_code": collection_response.get("veriCode"),
                        "agent_balance": collection_response.get("agentBalance"),
                        "gateway_data": collection_response,
                    }
                else:
                    return {"error": str(collection_response), "status": "failed"}

        except Exception as e:
            logger.error(f"SmobilPay payment execution failed: {str(e)}")
            return {"error": str(e), "status": "failed"}

    def verify_payment(self, gateway_reference: str) -> Dict[str, Any]:
        """Verify payment status using PTN"""
        try:
            status_response = self.client.fetch_payment_status(ptn=gateway_reference)
            if status_response.get("ptn", None):
                verified = (
                    True
                    if status_response.get("status").lower() == "success"
                    else False
                )
                return {
                    "gateway_transaction_id": status_response.get("ptn"),
                    "status": status_response.get("status").lower(),
                    "verified": verified,
                    "timestamp": status_response.get("timestamp"),
                    "clearing_date": status_response.get("clearingDate"),
                    "gateway_data": status_response,
                    "errorCode": status_response.get("errorCode", None),
                    "errorMessage": status_response.get("errorMessage", None),
                }
            else:
                return {
                    "error": str(status_response),
                    "status": "unknown",
                    "verified": False,
                }

        except Exception as e:
            logger.error(f"SmobilPay payment verification failed: {str(e)}")
            return {"error": str(e), "status": "unknown", "verified": False}

    def cashout(
        self,
        amount: Decimal,
        currency: str,
        recipient_data: Dict[str, Any],
        metadata: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Cashout to provider/customer (send money)
        """
        try:
            # Determine payment method for cashout (MTN or Orange)
            payment_method = recipient_data.get("payment_method", "mtn_momo")
            pay_item_id = self._get_pay_item_id(payment_method, "cashout")

            if not pay_item_id:
                return {
                    "error": f"Cashout not supported for {payment_method}",
                    "status": "failed",
                }
            # Log the payment method for debuging
            logger.info(f"Payment Item ID:::::::::: {pay_item_id}")
            # Request quote for cashout
            quote_response = self.client.request_quote(
                pay_item_id=pay_item_id, amount=float(amount)
            )

            # if not hasattr(quote_response, "quoteId"):
            #     return {"error": f"Quote failed: {quote_response}", "status": "failed"}

            # Execute cashout collection
            collection_data = {
                "quoteId": quote_response.get("quoteId"),
                "customerPhonenumber": recipient_data["phone_number"],
                "customerEmailaddress": recipient_data.get("email", ""),
                "serviceNumber": recipient_data["phone_number"],
                "trid": f"CASHOUT-{timezone.now().timestamp()}",
            }

            collection_response = self.client.execute_collection(collection_data)
            print(collection_response)
            if collection_response.get("status").lower() not in ["success", "pending"]:
                return {
                    "error": f"Collection failed: {collection_response}",
                    "status": "failed",
                }
            if isinstance(collection_response, dict):
                if collection_response.get("ptn"):
                    return {
                        "gateway_transaction_id": collection_response.get("ptn"),
                        "status": collection_response.get(
                            "status", ""
                        ).lower(),  # Use actual status
                        "type": "cashout",
                        "amount_sent": collection_response.get("priceLocalCur"),
                        "recipient": recipient_data["phone_number"],
                        "receipt_number": collection_response.get("receiptNumber"),
                        "gateway_data": collection_response,  # ✅ Just the dict, not __dict__
                    }
                else:
                    return {
                        "error": f"No PTN in response: {collection_response}",
                        "status": "failed",
                    }
            else:
                return {"error": str(collection_response), "status": "failed"}

        except Exception as e:
            logger.error(f"SmobilPay cashout failed: {str(e)}")
            return {"error": str(e), "status": "failed"}

    def _get_pay_item_id(self, payment_method: str, operation: str) -> Optional[str]:
        """Get SmobilPay payItemId from configuration"""
        from django.conf import settings

        logger.info("Calling get_pay_item_id")
        # First try environment variables
        if hasattr(settings, "SMOBILPAY_PAYITEM_IDS"):
            pay_item_map = settings.SMOBILPAY_PAYITEM_IDS
            if pay_item_map and payment_method in pay_item_map:
                print("Payment items from settings @@@@@@@@@@@@@@@@@@@@@@@@@@@@@@")
                print(settings.SMOBILPAY_PAYITEM_IDS)
                return pay_item_map[payment_method].get(operation)
        else:
            logger.warning("No SMOBILPAY_PAYITEM_IDS found in settings")
            print("this are teh settings for smobilpay", settings.SMOBILPAY_PAYITEM_IDS)
        # Fallback to config stored in gateway
        gateway_config = self.config.get("pay_item_map", {})
        if gateway_config and payment_method in gateway_config:
            return gateway_config[payment_method].get(operation)

        # Final fallback to defaults (for testing only)
        default_pay_item_map = {
            "mtn_momo": {
                "cashout": "S-112-948-MTNMOMO-20052-200050001-1",
                "cashin": "S-112-948-MTNMOMO-20053-200050002-1",
            },
            "orange_money": {
                "cashin": "S-112-948-ORANGEMONEY-20052-200050001-1",
                "cashout": "S-112-948-ORANGEMONEY-20053-200050002-1",
            },
        }

        return default_pay_item_map.get(payment_method, {}).get(operation)

    def get_supported_methods(self) -> Dict[str, Any]:
        return self.supported_methods

    def get_health_status(self) -> Dict[str, Any]:
        try:
            ping_response = self.client.ping()

            # Check if ping was successful
            if ping_response.get("status") == "success":
                return {
                    "healthy": True,
                    "response_time": ping_response.get("time"),
                    "version": ping_response.get("version"),
                }
            else:
                # Even if ping fails, check if we can get account info
                try:
                    account_info = self.client.get_account_info()
                    if account_info.get("status") == "success":
                        return {
                            "healthy": True,  # Mark as healthy since account works
                            "ping_error": ping_response.get("error"),
                            "account_balance": account_info.get("balance"),
                            "version": "3.0.0",  # Default version
                        }
                except:
                    pass

                return {
                    "healthy": False,
                    "error": ping_response.get("error"),
                    "response_time": None,
                    "version": None,
                }

        except Exception as e:
            logger.error(f"Health check failed: {str(e)}")
            return {"healthy": False, "error": str(e)}

    # Update the create_payment_intent method to handle responses better:
    def create_payment_intent(
        self,
        amount: Decimal,
        currency: str,
        payment_method: str,
        customer_data: Dict[str, Any],
        metadata: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Create payment intent using SmobilPay quote system
        """
        try:
            # 1. Find the right payItemId based on payment method
            pay_item_id = self._get_pay_item_id(payment_method, "cashin")
            if not pay_item_id:
                return {
                    "error": f"Payment method {payment_method} not supported",
                    "status": "failed",
                }
            # Log the payment method for debuging
            logger.info(f"Payment Item ID:::::::::: {pay_item_id}")
            print(f"#################### Payment Item ID:::::::::: {pay_item_id}")
            # 2. Request quote from SmobilPay
            quote_response = self.client.request_quote(
                pay_item_id=pay_item_id, amount=amount
            )

            if (
                quote_response.get("status") == "success"
                and "quoteId" in quote_response
            ):
                return {
                    "gateway_reference": quote_response["quoteId"],
                    "status": "pending",
                    "requires_action": True,
                    "next_action": {
                        "type": "customer_authorization",
                        "description": "Customer needs to authorize payment on their phone",
                    },
                    "fee_breakdown": {
                        "gateway_fee": Decimal(
                            str(quote_response.get("priceSystemCur", 0))
                        )
                        - Decimal(str(quote_response.get("amountLocalCur", 0))),
                        "total_amount": Decimal(
                            str(quote_response.get("priceLocalCur", 0))
                        ),
                        "service_amount": Decimal(
                            str(quote_response.get("amountLocalCur", 0))
                        ),
                    },
                    "expires_at": quote_response.get("expiresAt"),
                    "gateway_data": {
                        "pay_item_id": pay_item_id,
                        "quote_id": quote_response["quoteId"],
                    },
                }
            else:
                return {
                    "error": quote_response.get("error", "Quote request failed"),
                    "status": "failed",
                }

        except Exception as e:
            logger.error(f"SmobilPay payment intent creation failed: {str(e)}")
            return {"error": str(e), "status": "failed"}

    def process_webhook(
        self, payload: Dict[str, Any], signature: str
    ) -> Dict[str, Any]:
        """
        Process webhook/callback from SmobilPay
        Now delegates to the secure webhook handler
        """
        logger.warning(
            "This method should not be called directly. Use the webhook endpoint instead."
        )
        return {
            "status": "use_webhook_endpoint",
            "message": "Use /api/v1/payments/webhooks/smobilpay/endpoint",
            "requires_secure_processing": True,
        }

    def initiate_refund(
        self,
        gateway_reference: str,
        amount: Optional[Decimal] = None,
        reason: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Initiate refund for a transaction
        Note: SmobilPay doesn't have direct refund API, so we simulate it
        """
        try:
            # First, get the payment status to verify it exists
            payment_status = self.verify_payment(gateway_reference)

            if not payment_status.get("verified", False):
                return {
                    "status": "failed",
                    "error": "Payment not found or not verified",
                    "reference": gateway_reference,
                }

            # For SmobilPay, "refund" is actually a cashout to the customer
            # You need to have stored the customer's phone number from the original payment

            logger.warning(
                f"SmobilPay refund requested - Reference: {gateway_reference}, "
                f"Amount: {amount}, Reason: {reason}"
            )

            # Return a response indicating manual processing required
            return {
                "status": "requires_manual_action",
                "refund_reference": f"REF-{gateway_reference}-{int(timezone.now().timestamp())}",
                "original_reference": gateway_reference,
                "amount": float(amount) if amount else None,
                "message": "SmobilPay requires manual refund via cashout",
                "next_action": {
                    "type": "manual_cashout",
                    "description": "Process refund as cashout to customer's phone number",
                    "instructions": "Use cashout endpoint with customer's phone number",
                },
            }

        except Exception as e:
            logger.error(f"Refund initiation failed: {str(e)}")
            return {"error": str(e), "status": "failed"}

    # Optional: Add a method to handle SmobilPay-specific webhook validation
    def _verify_webhook_signature(self, payload: str, signature: str) -> bool:
        """Verify webhook signature from SmobilPay"""
        # TODO: Implement based on SmobilPay documentation
        # This is placeholder implementation
        return True
