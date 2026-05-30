from decimal import Decimal, ROUND_HALF_UP
from typing import Dict
from apps.properties.models import PaymentConfiguration
from apps.core.models import PlatformSettings


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
        net_rent: amount landlord expects to receive (per payment interval)
        config: PaymentConfiguration for this property
        payout_method: 'mtn_momo', 'orange_money', 'bank_transfer', etc.
        """
        self.net_rent = net_rent
        self.config = config
        self.payout_method = payout_method
        self._breakdown = None

    def calculate(self) -> Dict[str, Decimal]:
        """Perform calculations and return breakdown."""
        # Subscription model: no per‑transaction fees
        if self.config.pricing_model == "subscription":
            return {
                "platform_fee": Decimal(0),
                "gateway_fee": Decimal(0),
                "fixed_extra": Decimal(0),
                "landlord_net": self.net_rent,
                "tenant_total": self.net_rent,
            }

        # ----- Per‑transaction model -----
        # Get global platform settings (singleton)
        settings = PlatformSettings.get_settings()

        # 1. Platform fee (capped)
        platform_percent = settings.platform_fee_percent / Decimal(100)
        raw_platform = self.net_rent * platform_percent
        platform_fee = min(raw_platform, Decimal(settings.platform_fee_cap))
        platform_fee = platform_fee.quantize(Decimal("1."), rounding=ROUND_HALF_UP)

        # 2. Gateway fee – only if payout method is in gateway_methods list
        gateway_fee = Decimal(0)
        methods = self.config.gateway_methods or settings.gateway_methods
        if self.payout_method in methods:
            gateway_percent = settings.gateway_fee_percent / Decimal(100)
            gateway_fee = (self.net_rent * gateway_percent).quantize(
                Decimal("1."), rounding=ROUND_HALF_UP
            )

        # 3. Fixed extra fee (always tenant)
        fixed_extra = Decimal(settings.fixed_extra_fee)

        # 4. Distribute fees based on who pays.
        # NOTE: each *_fee_payer is one of {"tenant", "landlord", "split"}.
        # Previously this used `if tenant: ... else: landlord -= fee`, which silently
        # treated `"split"` the same as `"landlord"`. We now handle each case
        # explicitly so a 50/50 split is actually applied.
        tenant_total = self.net_rent
        landlord_net = self.net_rent

        platform_payer = self.config.platform_fee_payer
        if platform_payer == "tenant":
            tenant_total += platform_fee
        elif platform_payer == "split":
            half = (platform_fee / Decimal(2)).quantize(
                Decimal("1."), rounding=ROUND_HALF_UP
            )
            other_half = platform_fee - half  # avoid rounding loss
            tenant_total += half
            landlord_net -= other_half
        else:  # "landlord" (default)
            landlord_net -= platform_fee

        gateway_payer = self.config.gateway_fee_payer
        if gateway_payer == "tenant":
            tenant_total += gateway_fee
        elif gateway_payer == "split":
            half = (gateway_fee / Decimal(2)).quantize(
                Decimal("1."), rounding=ROUND_HALF_UP
            )
            other_half = gateway_fee - half
            tenant_total += half
            landlord_net -= other_half
        else:  # "landlord" (default)
            landlord_net -= gateway_fee

        tenant_total += fixed_extra

        # Final rounding
        tenant_total = tenant_total.quantize(Decimal("1."), rounding=ROUND_HALF_UP)
        landlord_net = landlord_net.quantize(Decimal("1."), rounding=ROUND_HALF_UP)

        # Ensure landlord net never negative (shouldn't happen, but safety)
        landlord_net = max(landlord_net, Decimal(0))

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
