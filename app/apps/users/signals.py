import logging
from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver

from apps.users.models import Profile

User = settings.AUTH_USER_MODEL
logger = logging.getLogger(__name__)


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)
        logger.info(f"Profile created for user {instance.email}")


@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    # This will also create the profile if it doesn't exist (e.g., when created via shell)
    profile, _ = Profile.objects.get_or_create(user=instance)
    profile.save()
