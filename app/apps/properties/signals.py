from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Property, PaymentConfiguration


@receiver(post_save, sender=Property)
def create_payment_config(sender, instance, created, **kwargs):
    if created:
        PaymentConfiguration.objects.get_or_create(property=instance)
