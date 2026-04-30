from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, Tuple
from decimal import Decimal
from django.conf import settings


class PaymentGatewayInterface(ABC):
    """Abstract interface for all payment gateways"""

    @abstractmethod
    def initialize(self, config: Dict[str, Any]) -> None:
        """Initialize gateway with configuration"""
        pass

    @abstractmethod
    def create_payment_intent(
        self,
        amount: Decimal,
        currency: str,
        payment_method: str,
        customer_data: Dict[str, Any],
        metadata: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Create a payment intent/quote
        Returns: {
            'gateway_reference': str,
            'status': str,
            'redirect_url': Optional[str],
            'requires_action': bool,
            'next_action': Optional[Dict],
            'fee_breakdown': Dict[str, Decimal]
        }
        """
        pass

    @abstractmethod
    def execute_payment(
        self, gateway_reference: str, customer_authorization: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Execute/confirm a payment
        """
        pass

    @abstractmethod
    def verify_payment(self, gateway_reference: str) -> Dict[str, Any]:
        """
        Verify payment status
        """
        pass

    @abstractmethod
    def process_webhook(
        self, payload: Dict[str, Any], signature: str
    ) -> Dict[str, Any]:
        """
        Process webhook/callback from gateway
        """
        pass

    @abstractmethod
    def initiate_refund(
        self,
        gateway_reference: str,
        amount: Optional[Decimal] = None,
        reason: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Initiate refund
        """
        pass

    @abstractmethod
    def cashout(
        self,
        amount: Decimal,
        currency: str,
        recipient_data: Dict[str, Any],
        metadata: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Send money to recipient (provider payout)
        """
        pass

    @abstractmethod
    def get_supported_methods(self) -> Dict[str, Any]:
        """
        Get supported payment methods
        """
        pass

    @abstractmethod
    def get_health_status(self) -> Dict[str, Any]:
        """
        Check gateway health
        """
        pass
