import uuid
from django.db import models
from django.utils.translation import gettext_lazy as _
from apps.core.models import TimeStampedUUIDModel
from django.core.validators import MinValueValidator, MaxValueValidator
from rest_framework.validators import ValidationError
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.core.validators import MinValueValidator, MaxValueValidator
from apps.core.models import TimeStampedUUIDModel
from apps.users.models import User
from django.conf import settings
from django.utils import timezone

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
    Reusable payment rule template.
    Can be:
    - System (global): owner=null, property=null  (admin‑created, read‑only for landlords)
    - Owner‑private: owner set, property=null
    - Property‑specific: owner set, property set (owner must be the property's primary owner)
    """

    name = models.CharField(_("Plan Name"), max_length=100)

    MODE_CHOICES = [("monthly", "Monthly"), ("yearly", "Yearly")]
    mode = models.CharField(
        _("Mode"), max_length=10, choices=MODE_CHOICES, default="monthly"
    )

    # Monthly mode
    allowed_monthly_terms = models.JSONField(
        _("Allowed Month Multiples"),
        default=list,
        blank=True,
        help_text=_("e.g., [1,3,6]. Empty means any up to max_months."),
    )
    max_months = models.PositiveIntegerField(
        _("Maximum Months per Payment"), default=12
    )

    # Yearly mode
    show_full_payment_option = models.BooleanField(
        _("Show Full Yearly Payment Option"), default=True
    )
    enforce_installment_order = models.BooleanField(
        _("Enforce Installment Order"), default=True
    )

    # Common
    allow_custom_amount = models.BooleanField(_("Allow Custom Amount"), default=False)
    amount_step = models.PositiveIntegerField(_("Amount Step (XAF)"), default=10)
    late_fee_rules = models.JSONField(_("Late Fee Rules"), default=dict, blank=True)

    # Ownership and scope
    owner = models.ForeignKey(
        "properties.Owner",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="payment_plans",
        verbose_name=_("Owner"),
        help_text=_(
            "If set, this plan is private to this landlord. If null, it is a system plan."
        ),
    )
    property = models.ForeignKey(
        "properties.Property",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="payment_plans",
        verbose_name=_("Property"),
        help_text=_(
            "If set, this plan is specific to this property. owner must also be set."
        ),
    )

    is_active = models.BooleanField(_("Active"), default=True)

    class Meta:
        verbose_name = _("Payment Plan")
        verbose_name_plural = _("Payment Plans")
        constraints = [
            # Prevent a plan from having both owner and property if property is set without owner, etc.
            models.CheckConstraint(
                check=(
                    models.Q(owner__isnull=True, property__isnull=True)
                    | models.Q(owner__isnull=False, property__isnull=True)
                    | models.Q(owner__isnull=False, property__isnull=False)
                ),
                name="paymentplan_valid_scope",
            )
        ]

    def clean(self):
        """Validate ownership consistency."""
        if self.property and not self.owner:
            raise ValidationError("Owner must be set when property is specified.")
        if self.property and self.owner:
            # Check that owner actually owns this property
            from apps.properties.models import PropertyOwnership

            if not PropertyOwnership.objects.filter(
                property=self.property, owner=self.owner
            ).exists():
                raise ValidationError("Owner does not own this property.")
        # System plans (both null) are allowed

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        scope = "System" if (self.owner is None and self.property is None) else ""
        if self.owner:
            scope = f"Owner: {self.owner.user.email}"
        if self.property:
            scope += f" / Property: {self.property.name}"
        return f"{self.name} ({scope})"

    def copy_to_agreement(self, agreement):
        """
        Create an AgreementPaymentPlan copy linked to the given agreement.
        """
        from .agreement_payment_plan import AgreementPaymentPlan

        return AgreementPaymentPlan.objects.create(
            agreement=agreement,
            name=self.name,
            mode=self.mode,
            allowed_monthly_terms=self.allowed_monthly_terms,
            max_months=self.max_months,
            show_full_payment_option=self.show_full_payment_option,
            enforce_installment_order=self.enforce_installment_order,
            allow_custom_amount=self.allow_custom_amount,
            amount_step=self.amount_step,
            late_fee_rules=self.late_fee_rules,
            is_active=True,
        )


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
    start_date = models.DateField(_("Start date"), default=timezone.now)

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


    # Terms
    terms_template = models.ForeignKey(
        "properties.TermTemplate",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="agreements",
        verbose_name=_("Terms Template"),
        help_text="The template used for this agreement (snapshot stored in terms_text).",
    )
    terms_text = models.TextField(
        _("Terms and conditions text"),
        blank=True,
        help_text="Full text of the agreement terms (snapshot at creation).",
        
    )
    acceptance_token = models.UUIDField(
        _("Acceptance token"),
        default=uuid.uuid4,
        # unique=True,
        editable=False,
    )
    terms_accepted_at = models.DateTimeField(_("Terms accepted at"), null=True, blank=True)
    terms_accepted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="accepted_agreements",
        verbose_name=_("Terms accepted by"),
        
    )
    is_active = models.BooleanField(_("Active"), default=False)  



    class Meta:
        verbose_name = _("Rental agreement")
        verbose_name_plural = _("Rental agreements")
        indexes = [
            models.Index(fields=["unit", "is_active"]),
            models.Index(fields=["tenant", "is_active"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["unit", "tenant"], name="unique_unit_tenant"
            ),
            models.CheckConstraint(
                name="check_coverage_end_date",
                check=models.Q(coverage_end_date__gte=models.F("start_date")),
            ),
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

        constraints = [
            models.UniqueConstraint(
                fields=["gateway_reference"],
                condition=models.Q(gateway_reference__isnull=False),
                name="unique_gateway_reference",
            ),
            models.UniqueConstraint(
                fields=["agreement"],
                condition=models.Q(status="pending"),
                name="unique_pending_payment_per_agreement",
            ),
        ]

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


class IdempotencyKey(models.Model):
    key = models.CharField(max_length=255, unique=True, db_index=True)
    resource_type = models.CharField(max_length=50)  # e.g., 'payment'
    resource_id = models.UUIDField(null=True, blank=True)
    response_data = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()

    class Meta:
        indexes = [models.Index(fields=["key", "resource_type"])]


class Disbursement(TimeStampedUUIDModel):
    """
    Tracks individual payout attempts for each owner's split of a payment.
    """

    STATUS_CHOICES = (
        ("pending", _("Pending")),
        ("processing", _("Processing")),
        ("completed", _("Completed")),
        ("failed", _("Failed")),
    )

    payment_split = models.ForeignKey(
        "properties.PaymentOwnerSplit",
        on_delete=models.CASCADE,
        related_name="disbursements",
    )
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default="pending", db_index=True
    )
    gateway_reference = models.CharField(
        max_length=255,
        blank=True,
        help_text=_(
            "Transaction ID from the payment gateway (e.g., PTN from SmobilPay)"
        ),
    )
    error_message = models.TextField(blank=True)
    processed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = _("Disbursement")
        verbose_name_plural = _("Disbursements")
        indexes = [
            models.Index(fields=["status"]),
            models.Index(fields=["payment_split", "status"]),
        ]

    def __str__(self):
        return (
            f"Disbursement {self.id} – {self.status} – {self.payment_split.amount} XAF"
        )


class LedgerEntry(TimeStampedUUIDModel):
    ENTRY_TYPES = (
        ("platform_fee", _("Platform Fee")),
        ("gateway_fee", _("Gateway Fee")),
        ("landlord_payout", _("Landlord Payout")),
        ("subscription_revenue", _("Subscription Revenue")),
    )

    payment = models.ForeignKey(
        Payment,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="ledger_entries",
    )
    owner = models.ForeignKey(
        "properties.Owner",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="ledger_entries",
    )
    amount = models.DecimalField(max_digits=10, decimal_places=0)
    entry_type = models.CharField(max_length=30, choices=ENTRY_TYPES)
    description = models.CharField(max_length=255, blank=True)

    class Meta:
        verbose_name = _("Ledger Entry")
        verbose_name_plural = _("Ledger Entries")
        indexes = [
            models.Index(fields=["entry_type"]),
            models.Index(fields=["payment", "entry_type"]),
        ]

    def __str__(self):
        return f"{self.get_entry_type_display()} - {self.amount} XAF"


class AuditLog(models.Model):
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True
    )
    action = models.CharField(max_length=50)
    target_model = models.CharField(max_length=100)
    target_id = models.CharField(max_length=36)
    changes = models.JSONField(default=dict)
    timestamp = models.DateTimeField(auto_now_add=True)


class AgreementAcceptance(TimeStampedUUIDModel):
    agreement = models.OneToOneField(
        RentalAgreement,
        on_delete=models.CASCADE,
        related_name="acceptance_record",
        verbose_name=_("Agreement"),
    )
    accepted_at = models.DateTimeField(_("Accepted at"), auto_now_add=True)
    ip_address = models.GenericIPAddressField(_("IP address"), null=True, blank=True)
    user_agent = models.CharField(_("User agent"), max_length=255, blank=True)
    terms_snapshot = models.TextField(_("Terms snapshot"), help_text="Copy of terms at acceptance time.")

    class Meta:
        verbose_name = _("Agreement Acceptance")
        verbose_name_plural = _("Agreement Acceptances")

    def __str__(self):
        return f"Acceptance of {self.agreement.id} at {self.accepted_at}"