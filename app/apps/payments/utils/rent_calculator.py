# apps/payments/rent_calculator.py

from decimal import Decimal, ROUND_HALF_UP
from typing import Dict, Optional
from apps.properties.models import PaymentConfiguration


class RentCalculator:
    """
    Calculates final tenant payment and landlord net based on property's payment config.
    Supports both per‑transaction and subscription models.
    """

    def __init__(
        self,
        net_rent: Decimal,
        config: PaymentConfiguration,
        payout_method: str,
    ):
        """
        net_rent: amount landlord expects to receive (per month / per payment interval)
        config: PaymentConfiguration for this property
        payout_method: 'mtn_momo', 'orange_money', 'bank_transfer', etc.
        """
        self.net_rent = net_rent
        self.config = config
        self.payout_method = payout_method
        self._breakdown = None

    def calculate(self) -> Dict[str, Decimal]:
        """Perform calculations and return breakdown."""
        if self.config.pricing_model == "subscription":
            # No per‑transaction fees. Landlord receives net_rent, tenant pays net_rent.
            # Subscription fee is billed separately (e.g., monthly invoice) – not included here.
            return {
                "platform_fee": Decimal(0),
                "gateway_fee": Decimal(0),
                "fixed_extra": Decimal(0),
                "landlord_net": self.net_rent,
                "tenant_total": self.net_rent,
            }

        # --- Per‑transaction model ---
        # 1. Platform fee (capped)
        raw_platform = self.net_rent * (self.config.platform_fee_percent / Decimal(100))
        platform_fee = min(raw_platform, Decimal(str(self.config.platform_fee_cap)))
        platform_fee = platform_fee.quantize(Decimal("1."), rounding=ROUND_HALF_UP)

        # 2. Gateway fee – only if payout method is in gateway_methods list
        gateway_fee = Decimal(0)
        if self.payout_method in self.config.gateway_methods:
            # Gateway fee is a percentage of the amount that Blizton sends to landlord.
            # But the amount sent = net_rent adjusted by who pays which fees.
            # We need to solve iteratively because gateway fee itself affects the total.
            # For simplicity and accuracy, we calculate after we know landlord_net (before gateway).
            # However, the gateway fee is applied to the final disbursement. We'll use an approximation:
            # gateway_fee = (net_rent + fees_borne_by_landlord) * percent
            # But since landlord usually does not pay gateway fee (tenant pays), we can compute directly.
            # Better: calculate tenant_total first without gateway, then add gateway fee as extra tenant cost.
            # But the gateway fee is a cost on the transaction, not a tax on rent. For realistic pass‑through:
            # The tenant should pay the gateway fee as a separate line item. So we treat gateway_fee as an
            # additional amount that the tenant pays, and landlord receives net_rent (if tenant pays).
            # If landlord pays the gateway fee, we subtract it from landlord_net.
            # For simplicity, we assume gateway fee is a percentage of net_rent.
            gateway_fee = self.net_rent * (
                self.config.gateway_fee_percent / Decimal(100)
            )
            gateway_fee = gateway_fee.quantize(Decimal("1."), rounding=ROUND_HALF_UP)

        # 3. Distribute fees according to who pays
        platform_paid_by_tenant = self.config.platform_fee_payer == "tenant"
        gateway_paid_by_tenant = self.config.gateway_fee_payer == "tenant"

        landlord_net = self.net_rent
        tenant_total = self.net_rent

        if platform_paid_by_tenant:
            tenant_total += platform_fee
        else:
            landlord_net -= platform_fee

        if gateway_paid_by_tenant:
            tenant_total += gateway_fee
        else:
            landlord_net -= gateway_fee

        # Fixed extra fee always paid by tenant
        fixed_extra = self.config.fixed_extra_fee
        tenant_total += fixed_extra

        # Final rounding
        tenant_total = tenant_total.quantize(Decimal("1."), rounding=ROUND_HALF_UP)
        landlord_net = landlord_net.quantize(Decimal("1."), rounding=ROUND_HALF_UP)

        self._breakdown = {
            "platform_fee": platform_fee,
            "gateway_fee": gateway_fee,
            "fixed_extra": fixed_extra,
            "landlord_net": landlord_net,
            "tenant_total": tenant_total,
        }
        return self._breakdown

    def get_breakdown(self) -> Dict[str, Decimal]:
        if self._breakdown is None:
            self.calculate()
        return self._breakdown

    def get_tenant_total(self) -> Decimal:
        return self.get_breakdown()["tenant_total"]

    def get_landlord_net(self) -> Decimal:
        return self.get_breakdown()["landlord_net"]
