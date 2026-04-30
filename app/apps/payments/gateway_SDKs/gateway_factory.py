# apps/payments/gateways/factory.py
"""
Factory for creating payment gateway instances
"""

from typing import Dict, Any
import logging

from .smobilpay_gateway import SmobilPayGateway

# from .stripe_gateway import StripeGateway
# from .paypal_gateway import PayPalGateway

logger = logging.getLogger(__name__)


class GatewayFactory:
    """Factory to create payment gateway instances"""

    _gateways = {
        "smobilpay": SmobilPayGateway,
        # 'stripe': StripeGateway,
        # 'paypal': PayPalGateway,
    }

    @classmethod
    def create_gateway(cls, gateway_type: str, config: Dict[str, Any]):
        """Create and initialize a gateway instance"""
        gateway_class = cls._gateways.get(gateway_type.lower())

        if not gateway_class:
            raise ValueError(f"Unsupported gateway type: {gateway_type}")

        try:
            gateway = gateway_class()
            gateway.initialize(config)
            return gateway
        except Exception as e:
            logger.error(f"Failed to create gateway {gateway_type}: {str(e)}")
            raise

    @classmethod
    def register_gateway(cls, name: str, gateway_class):
        """Register a new gateway type"""
        cls._gateways[name.lower()] = gateway_class


# Convenience instance
gateway_factory = GatewayFactory()
