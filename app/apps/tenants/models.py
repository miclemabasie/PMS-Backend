from django.db import models
from apps.core.models import TimeStampedUUIDModel
from apps.users.models import User
from phonenumber_field.modelfields import PhoneNumberField
from django.utils.translation import gettext_lazy as _
from model_utils import FieldTracker


# Create your models here.
class Tenant(TimeStampedUUIDModel):
    """
    Tenant (renter). Linked to a User account.
    """

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="tenant_profile",
        verbose_name=_("User"),
    )
    is_primary = models.BooleanField(_("Primary tenant"), default=False)
    id_number = models.CharField(_("ID number (CNI/Passport)"), max_length=50)
    id_document = models.FileField(
        _("ID scan"), upload_to="tenants/ids/", blank=True, null=True
    )
    emergency_contact_name = models.CharField(
        _("Emergency contact name"), max_length=255, blank=True
    )
    emergency_contact_phone = PhoneNumberField(_("Emergency contact phone"), blank=True)
    emergency_contact_relation = models.CharField(
        _("Relationship"), max_length=50, blank=True
    )
    employer = models.CharField(_("Employer"), max_length=255, blank=True)
    job_title = models.CharField(_("Job title"), max_length=100, blank=True)
    monthly_income = models.DecimalField(
        _("Monthly income (XAF)"),
        max_digits=12,
        decimal_places=0,
        blank=True,
        null=True,
    )
    guarantor_name = models.CharField(_("Guarantor name"), max_length=255, blank=True)
    guarantor_phone = PhoneNumberField(_("Guarantor phone"), blank=True)
    guarantor_email = models.EmailField(_("Guarantor email"), blank=True)
    guarantor_id_document = models.FileField(
        _("Guarantor ID scan"), upload_to="tenants/guarantors/", blank=True, null=True
    )
    notes = models.TextField(_("Notes"), blank=True)

    language = models.CharField(
        max_length=2, choices=[("en", "English"), ("fr", "French")], default="en"
    )
    emergency_contact_name_fr = models.CharField(
        _("Emergency contact name (French)"), max_length=255, blank=True
    )
    employer_fr = models.CharField(_("Employer (French)"), max_length=255, blank=True)
    job_title_fr = models.CharField(_("Job title (French)"), max_length=100, blank=True)
    notes_fr = models.TextField(_("Notes (French)"), blank=True)
    guarantor_name_fr = models.CharField(
        _("Guarantor name (French)"), max_length=255, blank=True
    )

    tracker = FieldTracker(
        fields=[
            "emergency_contact_name",
            "employer",
            "job_title",
            "notes",
            "guarantor_name",
        ]
    )

    class Meta:
        verbose_name = _("Tenant")
        verbose_name_plural = _("Tenants")
        indexes = [
            models.Index(fields=["user"]),
            models.Index(fields=["id_number"]),
        ]

    def __str__(self):
        return f"Tenant: {self.user.get_full_name()}"
