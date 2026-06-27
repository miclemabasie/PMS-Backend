from django.db.models.signals import post_save
from django.dispatch import receiver
from decimal import Decimal
from apps.core.models import PlatformSettings
from .models import Property, PropertyPaymentConfig


@receiver(post_save, sender=Property)
def create_property_payment_config(sender, instance, created, **kwargs):
    if created:
        # Get global platform settings (auto-creates with defaults if missing)
        settings = PlatformSettings.get_settings()

        # Prepare fee_overrides with platform fee settings
        fee_overrides = {
            "platform_fee_percent": float(settings.platform_fee_percent),
            "platform_fee_cap": settings.platform_fee_cap,
        }

        # Also optionally include gateway fee settings if you want them overridden
        # fee_overrides["gateway_fee_percent"] = float(settings.gateway_fee_percent)

        # Create config with sensible defaults
        PropertyPaymentConfig.objects.get_or_create(
            property=instance,
            defaults={
                "pricing_model": "per_transaction",
                "platform_fee_payer": "tenant",
                "gateway_fee_payer": "tenant",
                "wallet_fee_payer": "tenant",
                "gateway_methods": settings.gateway_methods
                or ["mtn_momo", "orange_money"],
                "fee_overrides": fee_overrides,
                "enable_wallet_payments": True,
                "allow_manual_payments": False,
                "manual_payment_requires_verification": True,
                "currency": "XAF",
                "is_active": True,
            },
        )

    # check if ppoerty was updated
    if not created:
        # update primary image if not none
        if not instance.get_primary_image():
            # get all the images associated with this property
            images = instance.property_images.all()
            if images:
                # get the first image
                image = images.first()
                # set the image as primary
                image.is_primary = True
                image.save()
                print("#### image updated", image)
