from django.db import models
from django.utils.translation import gettext_lazy as _
from apps.core.models import TimeStampedUUIDModel
from django.core.validators import MinValueValidator, MaxValueValidator


# Create your models here.


class PaymentTerm(TimeStampedUUIDModel):
    """
    Defines a payment schedule interval.
    Examples: Monthly (1 month), Quarterly (3 months), Yearly (12 months).
    """

    name = models.CharField(_("Name"), max_length=50, unique=True)
    interval_months = models.PositiveSmallIntegerField(
        _("Interval (months)"),
        validators=[MinValueValidator(1)],
        help_text=_(
            "Number of months between payments (1 = monthly, 3 = quarterly, etc.)"
        ),
    )
    description = models.TextField(_("Description"), blank=True)

    class Meta:
        verbose_name = _("Payment term")
        verbose_name_plural = _("Payment terms")
        ordering = ["interval_months"]

    def __str__(self):
        return self.name
