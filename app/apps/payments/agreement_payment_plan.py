from django.db import models
from apps.core.models import TimeStampedUUIDModel
from django.utils.translation import gettext_lazy as _


class AgreementPaymentPlan(TimeStampedUUIDModel):
    """
    Per‑agreement copy of a PaymentPlan.
    This is the working copy that can be customised per tenant without affecting the template.
    """

    agreement = models.OneToOneField(
        "payments.RentalAgreement",
        on_delete=models.CASCADE,
        related_name="payment_plan_config",
        verbose_name=_("Rental Agreement"),
    )

    # Copied fields (mirror PaymentPlan)
    name = models.CharField(_("Plan Name"), max_length=100)
    mode = models.CharField(
        _("Mode"),
        max_length=10,
        choices=[("monthly", "Monthly"), ("yearly", "Yearly")],
        default="monthly",
    )
    allowed_monthly_terms = models.JSONField(default=list, blank=True)
    max_months = models.PositiveIntegerField(default=12)
    show_full_payment_option = models.BooleanField(default=True)
    enforce_installment_order = models.BooleanField(default=True)
    allow_custom_amount = models.BooleanField(default=False)
    amount_step = models.PositiveIntegerField(default=10)
    late_fee_rules = models.JSONField(default=dict, blank=True)

    is_active = models.BooleanField(_("Active"), default=True)

    class Meta:
        verbose_name = _("Agreement Payment Plan")
        verbose_name_plural = _("Agreement Payment Plans")

    def __str__(self):
        return f"Agreement Plan for {self.agreement.id[:8]}"
