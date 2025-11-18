import uuid

from django.db import models
from django.utils.translation import gettext_lazy as _


class TimeStampedUUIDModel(models.Model):
    """
    Abstract base model providing:
    - Internal numeric primary key (performance-friendly)
    - Public UUID identifier (safe for APIs)
    - Creation & update timestamps
    """

    pkid = models.BigAutoField(
        primary_key=True,
        editable=False,
    )

    id = models.UUIDField(
        default=uuid.uuid4,
        editable=False,
        unique=True,
        db_index=True,   # Fast lookups for API usage
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        db_index=True,   # Useful for sorting & filtering
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        abstract = True
        ordering = ("-created_at",)  # Sensible default for most models

    def __str__(self):
        return str(self.id)


class Gender(models.TextChoices):
    """
    Enumerated gender choices.
    Stored values are stable and API-friendly.
    """

    MALE = "male", _("Male")
    FEMALE = "female", _("Female")
    OTHER = "other", _("Other")
