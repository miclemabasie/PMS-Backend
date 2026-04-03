import pytest
from django.core.exceptions import ValidationError
from apps.users.models import User
from apps.core.constants import AppConstants


@pytest.mark.django_db
class TestCustomUserManager:
    def test_email_validator_raises_for_invalid_email(self):
        with pytest.raises(
            ValidationError, match=AppConstants.USER_EMAIL_VALIDATION_ERROR_MESSAGE
        ):
            User.objects.email_validator("invalid-email")
