from django.db.models.signals import post_save
from django.dispatch import receiver
from apps.properties.models import Owner
from .models import TemplateConfig


@receiver(post_save, sender=Owner)
def create_default_templates(sender, instance, created, **kwargs):
    if created:
        # Create default config for each template type
        for template_type in TemplateConfig.TemplateType.values:
            TemplateConfig.objects.create(
                landlord=instance,
                template_type=template_type,
                is_default=True,
                agency_name=instance.user.get_full_name(),
                agency_email=instance.user.email,
                agency_phone=instance.mobile_money_number or "",
            )
