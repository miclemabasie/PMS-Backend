from django.contrib.auth.base_user import BaseUserManager
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.utils.translation import gettext_lazy as _

from apps.core.constants import (
    AppConstants,
)


class CustomUserManager(BaseUserManager):
    def email_validator(self, email):
        try:
            validate_email(email)
        except ValidationError:
            raise ValidationError(_(AppConstants.USER_EMAIL_VALIDATION_ERROR_MESSAGE))

    def create_user(
        self, username, first_name, last_name, email, password, **extra_fields
    ):
        if not username:
            raise ValueError(_(AppConstants.NO_USERNAME_ERROR_MESSAGE))
        if not first_name:
            raise ValueError(_(AppConstants.NO_FIRSTNAME_ERROR_MESSAGE))
        if not last_name:
            raise ValueError(_(AppConstants.NO_LASTNAME_ERROR_MESSAGE))
        if not email:
            raise ValueError(_(AppConstants.NO_EMAIL_SET_ERROR_MESSAGE))
        if not password:
            raise ValueError(_(AppConstants.NO_PASSWORD_ERROR_MESSAGE))

        email = self.normalize_email(email)
        self.email_validator(email)

        user = self.model(
            username=username,
            first_name=first_name,
            last_name=last_name,
            email=email,
            **extra_fields,
        )
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(
        self, username, first_name, last_name, email, password, **extra_fields
    ):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)
        extra_fields.setdefault("role", "admin")  # set role to admin

        if extra_fields.get("is_staff") is not True:
            raise ValueError(
                _(AppConstants.CREATE_SUPERUSER_IS_STAFF_IS_NOT_TRUE_ERROR_MESSAGE)
            )
        if extra_fields.get("is_superuser") is not True:
            raise ValueError(
                _(AppConstants.CREATE_SUPERUSER_IS_SUPERUSER_IS_NOT_TRUE_ERROR_MESSAGE)
            )
        if not password:
            raise ValueError(_(AppConstants.NO_PASSWORD_ERROR_MESSAGE))
        if not email:
            raise ValueError(_(AppConstants.NO_EMAIL_SET_ERROR_MESSAGE))

        return self.create_user(
            username, first_name, last_name, email, password, **extra_fields
        )
