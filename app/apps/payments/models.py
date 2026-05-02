from django.db import models
from django.utils.translation import gettext_lazy as _
from apps.core.models import TimeStampedUUIDModel
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.core.validators import MinValueValidator, MaxValueValidator
from apps.core.models import TimeStampedUUIDModel
from apps.users.models import User
from django.conf import settings

# Create your models here.
TERMINATION_REASON_CHOICES = [
    ("landlord_initiated", "Landlord Initiated"),
    ("tenant_initiated", "Tenant Initiated"),
    ("mutual_agreement", "Mutual Agreement"),
    ("landlord_forced", "Landlord Forced (No Active Payment)"),
    ("expired", "Auto‑expired"),
]


class PaymentPlan(TimeStampedUUIDModel):
    """
    Defines payment rules for a unit.
    - mode: 'monthly' or 'yearly'
    - For monthly: allowed_monthly_terms (list of ints), max_months, allow_custom_amount
    - For yearly: installments (linked via Installment model), show_full_payment_option, enforce_installment_order
    """

    MODE_CHOICES = [
        ("monthly", _("Monthly")),
        ("yearly", _("Yearly")),
    ]
    name = models.CharField(_("Plan name"), max_length=100)
    mode = models.CharField(
        _("Mode"), max_length=10, choices=MODE_CHOICES, default="monthly"
    )

    # Monthly mode fields
    allowed_monthly_terms = models.JSONField(
        _("Allowed month multiples"),
        default=list,
        blank=True,
        help_text=_(
            "List of integers, e.g., [1,3,6]. Empty means any up to max_months."
        ),
    )
    max_months = models.PositiveIntegerField(
        _("Maximum months per payment"), default=12
    )

    # Yearly mode fields (installments are in separate model)
    show_full_payment_option = models.BooleanField(
        _("Show full yearly payment option"), default=True
    )
    enforce_installment_order = models.BooleanField(
        _("Enforce installment order"), default=True
    )

    # Common fields
    allow_custom_amount = models.BooleanField(_("Allow custom amount"), default=False)
    amount_step = models.PositiveIntegerField(
        _("Amount step (XAF)"),
        default=10,
        help_text=_("Payment amounts must be multiples of this value."),
    )

    # Late fee rules (optional, JSON)
    late_fee_rules = models.JSONField(_("Late fee rules"), default=dict, blank=True)

    is_active = models.BooleanField(_("Active"), default=True)

    class Meta:
        verbose_name = _("Payment plan")
        verbose_name_plural = _("Payment plans")

    def __str__(self):
        return f"{self.name} ({self.mode})"


class Installment(models.Model):
    """
    Defines an installment for a yearly payment plan.
    """

    payment_plan = models.ForeignKey(
        PaymentPlan, on_delete=models.CASCADE, related_name="installments"
    )
    percent = models.DecimalField(
        _("Percentage"),
        max_digits=5,
        decimal_places=2,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
    )
    due_date = models.DateField(_("Due date"), null=True, blank=True)
    order_index = models.PositiveIntegerField(_("Order"))

    class Meta:
        ordering = ["order_index"]
        unique_together = [["payment_plan", "order_index"]]

    def __str__(self):
        return f"{self.payment_plan.name} - {self.percent}%"


class RentalAgreement(TimeStampedUUIDModel):
    """
    Links a tenant to a unit with a specific payment plan.
    Tracks coverage for monthly mode or installment status for yearly mode.
    """

    unit = models.ForeignKey(
        "properties.Unit", on_delete=models.CASCADE, related_name="agreements"
    )
    tenant = models.ForeignKey(
        "tenants.Tenant", on_delete=models.CASCADE, related_name="agreements"
    )
    payment_plan = models.ForeignKey(PaymentPlan, on_delete=models.PROTECT)
    start_date = models.DateField(_("Start date"), auto_now_add=True)

    # For monthly mode: the date until which rent is paid
    coverage_end_date = models.DateField(_("Coverage end date"), null=True, blank=True)

    # For yearly mode: JSON status of installments
    installment_status = models.JSONField(
        _("Installment status"), default=dict, blank=True
    )

    termination_date = models.DateField(_("Termination date"), null=True, blank=True)
    termination_reason_text = models.TextField(_("Termination reason"), blank=True)
    termination_type = models.CharField(
        _("Termination type"),
        max_length=30,
        choices=TERMINATION_REASON_CHOICES,
        null=True,
        blank=True,
    )
    terminated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="terminated_agreements",
        verbose_name=_("Terminated by"),
    )

    is_active = models.BooleanField(_("Active"), default=True)

    class Meta:
        verbose_name = _("Rental agreement")
        verbose_name_plural = _("Rental agreements")
        indexes = [
            models.Index(fields=["unit", "is_active"]),
            models.Index(fields=["tenant", "is_active"]),
        ]

    def __str__(self):
        return f"{self.tenant} @ {self.unit} ({self.payment_plan.name})"


class Payment(TimeStampedUUIDModel):
    """
    Records a payment made towards a rental agreement.
    """

    agreement = models.ForeignKey(
        RentalAgreement, on_delete=models.CASCADE, related_name="payments"
    )
    amount = models.DecimalField(_("Amount (XAF)"), max_digits=10, decimal_places=0)
    months_covered = models.DecimalField(
        _("Months covered"),
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        help_text=_("For monthly mode, fractional months if partial payment."),
    )
    period_start = models.DateField(_("Period start"))
    period_end = models.DateField(_("Period end"))
    payment_date = models.DateField(_("Payment date"), auto_now_add=True)
    payment_method = models.CharField(
        _("Payment method"),
        max_length=20,
        choices=[
            ("mtn_momo", "MTN MoMo"),
            ("orange_money", "Orange Money"),
            ("bank_transfer", "Bank transfer"),
            ("cash", "Cash"),
            ("other", "Other"),
        ],
    )
    status = models.CharField(
        _("Status"),
        max_length=20,
        choices=[
            ("pending", "Pending"),
            ("completed", "Completed"),
            ("failed", "Failed"),
            ("refunded", "Refunded"),
        ],
        default="pending",
    )
    transaction_id = models.CharField(_("Transaction ID"), max_length=255, blank=True)
    # For mobile money
    mobile_provider = models.CharField(_("Mobile provider"), max_length=50, blank=True)
    mobile_phone = models.CharField(_("Payer phone number"), max_length=30, blank=True)
    mobile_reference = models.CharField(
        _("Mobile money reference"), max_length=255, blank=True
    )
    # For bank/cash
    bank_name = models.CharField(_("Bank name"), max_length=100, blank=True)
    check_number = models.CharField(_("Check number"), max_length=50, blank=True)
    notes = models.TextField(_("Notes"), blank=True)
    # Dummy payment gateway response
    gateway_response = models.JSONField(_("Gateway response"), default=dict, blank=True)
    net_landlord_amount = models.DecimalField(
        _("Net amount to landlord (XAF)"),
        max_digits=10,
        decimal_places=0,
        null=True,
        blank=True,
        help_text="Amount that will be paid out to the landlord after fees",
    )
    fee_breakdown = models.JSONField(
        _("Fee breakdown"),
        default=dict,
        blank=True,
        help_text="Detailed breakdown of platform/gateway fees",
    )

    gateway_reference = models.CharField(
        _("Gateway reference"), max_length=255, blank=True
    )
    gateway_transaction_id = models.CharField(
        _("Gateway transaction ID"), max_length=255, blank=True
    )

    class Meta:
        verbose_name = _("Payment")
        verbose_name_plural = _("Payments")
        ordering = ["-payment_date"]

    def __str__(self):
        return (
            f"{self.amount} XAF - {self.get_payment_method_display()} - {self.status}"
        )


class SubscriptionPlan(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    monthly_price = models.DecimalField(max_digits=10, decimal_places=0)
    # Limits
    max_properties = models.PositiveIntegerField(
        null=True, blank=True, help_text="Null = unlimited"
    )
    max_units_total = models.PositiveIntegerField(null=True, blank=True)
    max_units_per_property = models.PositiveIntegerField(null=True, blank=True)
    # Feature flags
    has_api_access = models.BooleanField(default=False)
    has_advanced_reports = models.BooleanField(default=False)
    has_priority_support = models.BooleanField(default=False)
    has_bulk_sms = models.BooleanField(default=False)
    features = models.JSONField(default=list, blank=True)  # human‑readable list
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} – {self.monthly_price} XAF/mo"
