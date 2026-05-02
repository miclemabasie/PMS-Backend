from decimal import Decimal
from apps.properties.models import PaymentConfiguration
from apps.core.models import PlatformSettings


class RentCalculator:
    def __init__(
        self, net_rent: Decimal, config: PaymentConfiguration, payout_method: str
    ):
        self.net_rent = net_rent
        self.config = config
        self.payout_method = payout_method
        self.global_settings = PlatformSettings.get_settings()

    def calculate(self):
        if self.config.pricing_model == "subscription":
            return {
                "platform_fee": Decimal(0),
                "gateway_fee": Decimal(0),
                "fixed_extra": Decimal(0),
                "landlord_net": self.net_rent,
                "tenant_total": self.net_rent,
            }
        # Get global values
        platform_percent = self.global_settings.platform_fee_percent / Decimal(100)
        platform_cap = Decimal(self.global_settings.platform_fee_cap)
        gateway_percent = self.global_settings.gateway_fee_percent / Decimal(100)
        fixed_extra = Decimal(self.global_settings.fixed_extra_fee)

        raw_platform = self.net_rent * platform_percent
        platform_fee = min(raw_platform, platform_cap).quantize(Decimal("1."))
        gateway_fee = Decimal(0)
        methods = self.config.gateway_methods or self.global_settings.gateway_methods
        if self.payout_method in methods:
            gateway_fee = (self.net_rent * gateway_percent).quantize(Decimal("1."))

        tenant_total = self.net_rent
        landlord_net = self.net_rent

        if self.config.platform_fee_payer == "tenant":
            tenant_total += platform_fee
        else:
            landlord_net -= platform_fee

        if self.config.gateway_fee_payer == "tenant":
            tenant_total += gateway_fee
        else:
            landlord_net -= gateway_fee

        tenant_total += fixed_extra

        # Ensure landlord_net never goes negative
        landlord_net = max(landlord_net, Decimal(0))
        return {
            "platform_fee": platform_fee,
            "gateway_fee": gateway_fee,
            "fixed_extra": fixed_extra,
            "landlord_net": landlord_net,
            "tenant_total": tenant_total,
        }
