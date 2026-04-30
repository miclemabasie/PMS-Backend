"""
SmobilPay Client Wrapper - Simplified version
"""

import logging
from typing import Dict, Any, Optional
from decimal import Decimal
from django.conf import settings

from ..smobilpay.services.account_service import AccountService
from ..smobilpay.services.quote_service import QuoteService
from ..smobilpay.services.collection_service import CollectionService
from ..smobilpay.services.payment_status_service import PaymentStatusService
from ..smobilpay.services.ping_service import PingService
from decimal import Decimal, ROUND_HALF_UP

logger = logging.getLogger(__name__)


class SmobilPayClient:
    """Simplified client for SmobilPay API"""

    def __init__(
        self, api_url: str, public_token: str, secret_key: str, live_mode: bool = True
    ):
        self.api_url = api_url
        self.public_token = public_token
        self.secret_key = secret_key
        self.live_mode = live_mode

        # Initialize services
        self.quote_service = QuoteService(
            public_token=self.public_token, secret_key=self.secret_key
        )

        self.collection_service = CollectionService(
            public_token=self.public_token, secret_key=self.secret_key
        )

        self.payment_status_service = PaymentStatusService(
            public_token=self.public_token, secret_key=self.secret_key
        )

        self.ping_service = PingService(
            public_token=self.public_token, secret_key=self.secret_key
        )

        self.account_service = AccountService(
            public_token=self.public_token, secret_key=self.secret_key
        )

    def ping(self) -> Dict[str, Any]:
        """Test connection to SmobilPay API"""
        try:
            response = self.ping_service.ping()

            # Debug: Log what we're getting
            logger.debug(f"Ping response type: {type(response)}")
            logger.debug(f"Ping response attributes: {dir(response)}")

            # Check if response is a string error
            if isinstance(response, str):
                logger.error(f"Ping returned string error: {response}")
                return {"error": response, "status": "failed"}

            # Check if it's a PingModel with error attribute
            if hasattr(response, "error") and response.error:
                return {"error": response.error, "status": "failed"}

            # If it has time and version, it's successful
            if hasattr(response, "time") and response.time:
                return {
                    "time": response.time,
                    "version": response.version,
                    "status": "success",
                }
            else:
                # Check if it's a dict
                if isinstance(response, dict):
                    if response.get("error"):
                        return {"error": response.get("error"), "status": "failed"}
                    elif response.get("time"):
                        return {
                            "time": response.get("time"),
                            "version": response.get("version"),
                            "status": "success",
                        }

                logger.warning(f"Unexpected ping response format: {response}")
                return {"error": "Unexpected response format", "status": "failed"}

        except Exception as e:
            logger.error(f"Ping failed with exception: {str(e)}")
            return {"error": str(e), "status": "failed"}

    def _round_amount(self, amount: float) -> int:
        """
        Round amount to nearest integer for XAF
        Uses standard rounding (0.5 rounds up)
        """
        # Convert to Decimal for precise rounding
        amount_decimal = Decimal(str(amount))
        rounded = amount_decimal.quantize(Decimal("1"), rounding=ROUND_HALF_UP)
        return int(rounded)

    def request_quote(self, pay_item_id: str, amount: float) -> Dict[str, Any]:
        """Request quote for payment"""
        try:
            # Round amount to nearest integer
            amount_rounded = self._round_amount(amount)

            response = self.quote_service.request_quote(
                payment_item_id=pay_item_id, amount=amount_rounded
            )
            # end

            if isinstance(response, str) and "error" in response.lower():
                return {"error": response, "status": "failed"}

            if hasattr(response, "quoteId"):
                return {
                    "quoteId": response.quoteId,
                    "expiresAt": response.expiresAt,
                    "amountLocalCur": response.amountLocalCur,
                    "priceLocalCur": response.priceLocalCur,
                    "priceSystemCur": response.priceSystemCur,
                    "localCur": response.localCur,
                    "systemCur": response.systemCur,
                    "status": "success",
                }
            else:
                return {"error": str(response), "status": "failed"}

        except Exception as e:
            logger.error(f"Quote request failed: {str(e)}")
            return {"error": str(e), "status": "failed"}

    def execute_collection(self, collection_data: Dict[str, Any]) -> Dict[str, Any]:
        """Execute collection (payment)"""
        try:
            response = self.collection_service.execute_collection(collection_data)

            if isinstance(response, str) and "error" in response.lower():
                return {"error": response, "status": "failed"}

            if hasattr(response, "ptn"):
                return {
                    "ptn": response.ptn,
                    "status": response.status,
                    "receiptNumber": response.receiptNumber,
                    "veriCode": response.veriCode,
                    "agentBalance": response.agentBalance,
                    "priceLocalCur": response.priceLocalCur,
                    "priceSystemCur": response.priceSystemCur,
                    "localCur": response.localCur,
                    "systemCur": response.systemCur,
                    "trid": response.trid,
                    "timestamp": response.timestamp,
                }
            else:
                return {"error": str(response), "status": "failed"}

        except Exception as e:
            logger.error(f"Collection failed: {str(e)}")
            return {"error": str(e), "status": "failed"}

    def fetch_payment_status(self, ptn: str) -> Dict[str, Any]:
        """Fetch payment status using verifytx endpoint"""
        try:
            response = self.payment_status_service.fetch_payment_status(ptn=ptn)
            if isinstance(response, str) and "error" in response.lower():
                return {"error": response, "status": "failed"}

            error_dictionary = {
                "703202": "Transaction rejected by customer",
                "703108": "Low account balance",
                "703201": "Transaction was not confirmed",
                "703000": "Transaction failed",
            }

            if isinstance(response, list) and len(response) > 0:
                payment = response[0]
                error_message = error_dictionary.get(str(payment.errorCode), None)
                return {
                    "ptn": payment.ptn,
                    "status": payment.status.lower(),
                    "timestamp": payment.timestamp,
                    "clearingDate": payment.clearingDate,
                    "receiptNumber": payment.receiptNumber,
                    "priceLocalCur": payment.priceLocalCur,
                    "priceSystemCur": payment.priceSystemCur,
                    "localCur": payment.localCur,
                    "systemCur": payment.systemCur,
                    "verified": True if payment.status.lower() == "success" else False,
                    "errorCode": payment.errorCode,
                    "errorMessage": error_message,
                }
            else:
                return {"error": "No payment found", "status": "failed"}

        except Exception as e:
            logger.error(f"Payment status fetch failed: {str(e)}")
            return {"error": str(e), "status": "failed"}

    def get_account_info(self) -> Dict[str, Any]:
        """Get account information"""
        try:
            response = self.account_service.fetch_account_info()

            if isinstance(response, str) and "error" in response.lower():
                return {"error": response, "status": "failed"}

            if hasattr(response, "balance"):
                return {
                    "balance": response.balance,
                    "currency": response.currency,
                    "agentId": response.agentId,
                    "agentName": response.agentName,
                    "status": "success",
                }
            else:
                return {"error": str(response), "status": "failed"}

        except Exception as e:
            logger.error(f"Account info fetch failed: {str(e)}")
            return {"error": str(e), "status": "failed"}
