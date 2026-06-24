from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Property, PropertyPaymentConfig


@receiver(post_save, sender=Property)
def create_property_payment_config(sender, instance, created, **kwargs):
    if created:
        PropertyPaymentConfig.objects.get_or_create(property=instance)
