import uuid

from django.conf import settings
from django.contrib.auth.models import (
    AbstractBaseUser,
    PermissionsMixin,
    Group,
    Permission,
)
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from django_countries.fields import CountryField
from phonenumber_field.modelfields import PhoneNumberField

from apps.core.models import Gender, TimeStampedUUIDModel
from .managers import CustomUserManager


class Role(models.TextChoices):
    ADMIN = "admin", _("Admin")
    MODERATOR = "moderator", _("Moderator")
    USER = "user", _("User")


class User(AbstractBaseUser, PermissionsMixin):
    pkid = models.BigAutoField(primary_key=True, editable=False)
    id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    username = models.CharField(_("Username"), max_length=250)
    first_name = models.CharField(_("First Name"), max_length=250)
    last_name = models.CharField(_("Last Name"), max_length=250)
    email = models.EmailField(_("Email Address"), unique=True)
    role = models.CharField(
        _("Role"),
        max_length=20,
        choices=Role.choices,
        default=Role.USER,
    )
    is_staff = models.BooleanField(default=False)
    is_active = models.BooleanField(default=False)
    date_joined = models.DateField(default=timezone.now)

    objects = CustomUserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["username", "first_name", "last_name"]

    groups = models.ManyToManyField(
        Group,
        related_name="custom_user_groups",
        blank=True,
    )
    user_permissions = models.ManyToManyField(
        Permission,
        related_name="custom_user_permissions",
        blank=True,
    )

    class Meta:
        verbose_name = _("User")
        verbose_name_plural = _("Users")
        indexes = [
            models.Index(fields=["email"]),
        ]

    def __str__(self):
        return f"{self.username} - {self.email}"

    def get_full_name(self):
        return f"{self.first_name.title()} {self.last_name.title()}"

    def get_short_name(self):
        return self.username

    def membership_duration(self):
        from django.utils.timesince import timesince

        return timesince(self.date_joined)

    def last_active(self):
        from django.utils.timesince import timesince

        return timesince(self.last_login) if self.last_login else "Never"


class Profile(TimeStampedUUIDModel):
    user = models.OneToOneField(User, related_name="profile", on_delete=models.CASCADE)
    bio = models.TextField(_("About me"), default="", blank=True, null=True)
    profile_photo = models.ImageField(
        _("Profile Photo"),
        default="profiles/default_profile.png",
        upload_to="profiles/",
    )
    gender = models.CharField(
        _("Gender"),
        choices=Gender.choices,
        default=Gender.OTHER,
        max_length=20,
    )
    country = CountryField(_("Country"), default="CMR", blank=False, null=False)
    city = models.CharField(_("City"), max_length=180, default="Bamenda")
    address = models.CharField(_("Address"), max_length=100, default="Address")
    phone_number = PhoneNumberField(
        _("Phone Number"), max_length=30, default="+237660181440"
    )

    class Meta:
        verbose_name = _("Profile")
        verbose_name_plural = _("Profiles")
        indexes = [
            models.Index(fields=["phone_number"]),
        ]

    def __str__(self):
        return f"{self.user.username}'s Profile"


class DataDeletionRequest(models.Model):
    """
    Google Play Store compliance – account/data deletion request.
    Fields for specific resources are abstracted into JSON for flexibility.
    """

    REQUEST_TYPES = (
        ("account", "Account Deletion"),
        ("data", "Data Deletion Only"),
    )
    STATUS_CHOICES = (
        ("pending", "Pending"),
        ("processing", "Processing"),
        ("completed", "Completed"),
        ("rejected", "Rejected"),
    )

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="deletion_requests",
        null=True,
        blank=True,
    )
    email = models.EmailField()
    request_type = models.CharField(max_length=20, choices=REQUEST_TYPES)
    verification_token = models.UUIDField(default=uuid.uuid4, editable=False)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    # Store which data to delete as JSON – makes it extendable without model changes
    data_to_delete = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    verified_at = models.DateTimeField(null=True, blank=True)
    processed_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.email} - {self.get_request_type_display()} - {self.status}"

    class Meta:
        ordering = ["-created_at"]
