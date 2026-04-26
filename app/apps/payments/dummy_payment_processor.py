import uuid
from decimal import Decimal


class DummyPaymentProcessor:
    """Mock payment gateway - always succeeds. Replace with real MTN/Orange API later."""

    @staticmethod
    def initiate_payment(amount: Decimal, phone_number: str, provider: str) -> dict:
        return {
            "success": True,
            "transaction_id": str(uuid.uuid4()),
            "status": "completed",
            "message": "Payment successful (dummy)",
            "provider": provider,
            "phone": phone_number,
            "amount": str(amount),
            "reference": str(uuid.uuid4())[:8].upper(),
        }

    @staticmethod
    def verify_payment(transaction_id: str) -> dict:
        return {"success": True, "status": "completed", "message": "Payment verified"}
