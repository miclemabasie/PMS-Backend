from decimal import Decimal, ROUND_HALF_UP
from typing import Dict, Optional
from apps.core.models import PlatformSettings
from apps.properties.models import (
    Property,
    Owner,
    PropertyPaymentConfig,
    OwnerPaymentConfig,
)


class RentCalculator:
    """
    Calculates final tenant payment and landlord net based on:
      - Property-specific overrides (PropertyPaymentConfig)
      - Owner-level defaults (OwnerPaymentConfig)
      - Subscription status and discounts
      - Global PlatformSettings (fallback)

    Fee resolution precedence (highest to lowest):
        1. Property.fee_overrides (JSON)
        2. PropertyPaymentConfig fields (pricing_model, payer rules, gateway methods)
        3. OwnerPaymentConfig (rates, caps, fixed fee)
        4. Subscription plan discounts (if active)
        5. Global PlatformSettings
    """

    def __init__(self, net_rent: Decimal, property_obj: Property, owner: Owner):
        """
        Args:
            net_rent: Amount the landlord expects to receive (before fees)
            property_obj: The Property instance
            owner: The Owner instance (landlord)
        """
        self.net_rent = net_rent
        self.property_obj = property_obj
        self.owner = owner
        self._breakdown = None
        self.effective_config = self._resolve_config()

    def _resolve_config(self) -> Dict:
        """
        Resolve the final fee configuration using the precedence chain.
        Returns a dictionary with all fee parameters.
        """
        # 1. Start with global defaults
        config = PlatformSettings.get_settings()

        # 2. Owner-level defaults (OwnerPaymentConfig)
        if hasattr(self.owner, "payment_config"):
            oc: OwnerPaymentConfig = self.owner.payment_config
            for field in [
                "platform_fee_percent",
                "platform_fee_cap",
                "gateway_fee_percent",
                "fixed_extra_fee",
            ]:
                val = getattr(oc, field, None)
                if val is not None:
                    config[field] = val

        # 3. Property-level configuration (PropertyPaymentConfig)
        prop_config: Optional[PropertyPaymentConfig] = getattr(
            self.property_obj, "property_payment_config", None
        )
        if prop_config:
            # Apply property-specific distribution rules
            config["pricing_model"] = prop_config.pricing_model
            config["platform_fee_payer"] = prop_config.platform_fee_payer
            config["gateway_fee_payer"] = prop_config.gateway_fee_payer
            config["wallet_fee_payer"] = prop_config.wallet_fee_payer
            config["gateway_methods"] = prop_config.gateway_methods
            # Highest priority: fee_overrides
            for k, v in prop_config.fee_overrides.items():
                config[k] = v

        # 4. Apply subscription discounts or fee waiver
        if self.owner.subscription_status in ["active", "trial"]:
            plan = self.owner.subscription_plan
            # If plan is free (price 0) and pricing_model is subscription, force per_transaction
            if config.get("pricing_model") == "subscription":
                if plan and plan.monthly_price == 0:
                    # Free plan: do not waive fees
                    config["pricing_model"] = "per_transaction"
                else:
                    # Paid subscription: waive all per-transaction fees
                    config["platform_fee_percent"] = 0
                    config["gateway_fee_percent"] = 0
                    config["fixed_extra_fee"] = 0
            # Else apply discounts from plan (if any)
            if plan and plan.transaction_fee_discount_percent:
                discount = plan.transaction_fee_discount_percent / Decimal(100)
                config["platform_fee_percent"] = max(
                    0, config["platform_fee_percent"] * (1 - discount)
                )
            if plan and plan.platform_fee_cap_override is not None:
                config["platform_fee_cap"] = plan.platform_fee_cap_override
        else:
            # Subscription not active: force per_transaction pricing
            config["pricing_model"] = "per_transaction"

        return config

    def calculate(self) -> Dict[str, Decimal]:
        """Perform calculations and return breakdown."""
        config = self.effective_config
        net_rent = self.net_rent

        # If subscription model is set AND subscription is active, no fees
        # (already handled in _resolve_config, but re-check for safety)
        if config.get("pricing_model") == "subscription":
            return {
                "platform_fee": Decimal(0),
                "gateway_fee": Decimal(0),
                "fixed_extra": Decimal(0),
                "landlord_net": net_rent,
                "tenant_total": net_rent,
            }

        # ----- Per‑transaction model -----
        # 1. Platform fee (capped)
        platform_percent = config["platform_fee_percent"] / Decimal(100)
        raw_platform = net_rent * platform_percent
        platform_fee = min(raw_platform, Decimal(config["platform_fee_cap"]))
        platform_fee = platform_fee.quantize(Decimal("1."), rounding=ROUND_HALF_UP)

        # 2. Gateway fee – only if payout method is in gateway_methods list
        gateway_fee = Decimal(0)
        methods = config.get("gateway_methods", [])
        payout_method = self._get_payout_method()
        if payout_method in methods:
            gateway_percent = config["gateway_fee_percent"] / Decimal(100)
            gateway_fee = (net_rent * gateway_percent).quantize(
                Decimal("1."), rounding=ROUND_HALF_UP
            )

        # 3. Fixed extra fee (always tenant)
        fixed_extra = Decimal(config.get("fixed_extra_fee", 0))

        # 4. Distribute fees based on payer rules
        tenant_total = net_rent
        landlord_net = net_rent

        # Platform fee distribution
        platform_payer = config.get("platform_fee_payer", "tenant")
        if platform_payer == "tenant":
            tenant_total += platform_fee
        elif platform_payer == "split":
            half = (platform_fee / Decimal(2)).quantize(
                Decimal("1."), rounding=ROUND_HALF_UP
            )
            other_half = platform_fee - half
            tenant_total += half
            landlord_net -= other_half
        else:  # "landlord" (default)
            landlord_net -= platform_fee

        # Gateway fee distribution
        gateway_payer = config.get("gateway_fee_payer", "tenant")
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

        # Add fixed extra to tenant
        tenant_total += fixed_extra

        # Final rounding
        tenant_total = tenant_total.quantize(Decimal("1."), rounding=ROUND_HALF_UP)
        landlord_net = landlord_net.quantize(Decimal("1."), rounding=ROUND_HALF_UP)
        landlord_net = max(landlord_net, Decimal(0))  # safety

        self._breakdown = {
            "platform_fee": platform_fee,
            "gateway_fee": gateway_fee,
            "fixed_extra": fixed_extra,
            "landlord_net": landlord_net,
            "tenant_total": tenant_total,
        }
        return self._breakdown

    def _get_payout_method(self) -> str:
        """Get the landlord's preferred payout method."""
        if self.owner.preferred_payout_method:
            return self.owner.preferred_payout_method
        return "bank_transfer"  # fallback

    def get_breakdown(self) -> Dict[str, Decimal]:
        if self._breakdown is None:
            self.calculate()
        return self._breakdown

    def get_tenant_total(self) -> Decimal:
        return self.get_breakdown()["tenant_total"]

    def get_landlord_net(self) -> Decimal:
        return self.get_breakdown()["landlord_net"]
