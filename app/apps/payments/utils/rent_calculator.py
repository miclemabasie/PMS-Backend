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

    def _ensure_decimal(self, config: dict, keys: list):
        """Convert numeric config values to Decimal."""
        for key in keys:
            if key in config and config[key] is not None:
                if not isinstance(config[key], Decimal):
                    config[key] = Decimal(str(config[key]))

    def _resolve_config(self) -> Dict:
        """
        Resolve the final fee configuration using the precedence chain.
        Returns a dictionary with all fee parameters.
        """
        # 1. Start with global defaults as a dict
        config = {
            "platform_fee_percent": Decimal(1.0),
            "platform_fee_cap": 1000,
            "gateway_fee_percent": Decimal(2.0),
            "fixed_extra_fee": Decimal(0),
            "gateway_methods": ["mtn_momo", "orange_money"],
            "platform_fee_payer": "tenant",
            "gateway_fee_payer": "tenant",
            "wallet_fee_payer": "tenant",
            "pricing_model": "per_transaction",
        }

        # Override with actual PlatformSettings if they exist
        settings = PlatformSettings.get_settings()
        config.update(
            {
                "platform_fee_percent": settings.platform_fee_percent,
                "platform_fee_cap": settings.platform_fee_cap,
                "gateway_fee_percent": settings.gateway_fee_percent,
                "fixed_extra_fee": settings.fixed_extra_fee,
                "gateway_methods": settings.gateway_methods,
            }
        )

        # 2. Owner-level defaults (OwnerPaymentConfig)
        if hasattr(self.owner, "payment_config"):
            oc = self.owner.payment_config
            for field in [
                "platform_fee_percent",
                "platform_fee_cap",
                "gateway_fee_percent",
                "fixed_extra_fee",
                "platform_fee_payer",
                "gateway_fee_payer",
                "wallet_fee_payer",
                "gateway_methods",
                "pricing_model",
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
            # If pricing_model is subscription, waive fees (only if subscription is actually active)
            if config.get("pricing_model") == "subscription":
                if plan and plan.monthly_price == 0:
                    config["pricing_model"] = "per_transaction"
                else:
                    # Paid subscription: waive platform and fixed extra only – gateway remains
                    config["platform_fee_percent"] = Decimal(0)
                    # gateway_fee_percent stays as is (from owner/property/platform)
                    config["fixed_extra_fee"] = Decimal(0)
            # Else apply discounts from plan (if any)
            if (
                plan
                and hasattr(plan, "transaction_fee_discount_percent")
                and plan.transaction_fee_discount_percent
            ):
                discount = plan.transaction_fee_discount_percent / Decimal(100)
                config["platform_fee_percent"] = max(
                    Decimal(0), config["platform_fee_percent"] * (Decimal(1) - discount)
                )
            if (
                plan
                and hasattr(plan, "platform_fee_cap_override")
                and plan.platform_fee_cap_override is not None
            ):
                config["platform_fee_cap"] = plan.platform_fee_cap_override
        else:
            # Subscription not active: force per_transaction pricing
            config["pricing_model"] = "per_transaction"

        return config

    def calculate(self) -> Dict[str, Decimal]:
        """Perform calculations and return breakdown."""
        config = self.effective_config

        # Convert numeric config values to Decimal
        for key in [
            "platform_fee_percent",
            "platform_fee_cap",
            "gateway_fee_percent",
            "fixed_extra_fee",
        ]:
            if (
                key in config
                and config[key] is not None
                and not isinstance(config[key], Decimal)
            ):
                config[key] = Decimal(str(config[key]))

        net_rent = self.net_rent

        # ---- Common gateway fee calculation ----
        # This is used in both modes
        gateway_fee = Decimal(0)
        methods = config.get("gateway_methods", [])
        payout_method = self._get_payout_method()
        if payout_method in methods:
            gateway_percent = config["gateway_fee_percent"] / Decimal(100)
            gateway_fee = (net_rent * gateway_percent).quantize(
                Decimal("1."), rounding=ROUND_HALF_UP
            )

        # ---- Subscription mode: waive platform and fixed extra ----
        if config.get("pricing_model") == "subscription":
            platform_fee = Decimal(0)
            fixed_extra = Decimal(0)

            # Distribute only the gateway fee based on payer rules
            tenant_total = net_rent
            landlord_net = net_rent

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
            else:  # "landlord"
                landlord_net -= gateway_fee

            # No fixed extra, already zero
            tenant_total = tenant_total.quantize(Decimal("1."), rounding=ROUND_HALF_UP)
            landlord_net = landlord_net.quantize(Decimal("1."), rounding=ROUND_HALF_UP)
            landlord_net = max(landlord_net, Decimal(0))

            self._breakdown = {
                "platform_fee": platform_fee,
                "gateway_fee": gateway_fee,
                "fixed_extra": fixed_extra,
                "landlord_net": landlord_net,
                "tenant_total": tenant_total,
            }
            return self._breakdown

        # ---- Per‑transaction model ----
        # 1. Platform fee (capped)
        platform_percent = config["platform_fee_percent"] / Decimal(100)
        raw_platform = net_rent * platform_percent
        platform_fee = min(raw_platform, Decimal(config["platform_fee_cap"]))
        platform_fee = platform_fee.quantize(Decimal("1."), rounding=ROUND_HALF_UP)

        # 2. Fixed extra fee (always tenant)
        fixed_extra = Decimal(config.get("fixed_extra_fee", 0))

        # 3. Distribute both platform and gateway fees
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
        else:  # "landlord"
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
        else:  # "landlord"
            landlord_net -= gateway_fee

        # Add fixed extra to tenant
        tenant_total += fixed_extra

        # Final rounding
        tenant_total = tenant_total.quantize(Decimal("1."), rounding=ROUND_HALF_UP)
        landlord_net = landlord_net.quantize(Decimal("1."), rounding=ROUND_HALF_UP)
        landlord_net = max(landlord_net, Decimal(0))

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
