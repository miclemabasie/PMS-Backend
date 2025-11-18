# =========== Logging ==============
class LoggingConstants:
    LOG_LEVEL = "INFO"
    LOG_FILE_NAME = "django.log"


class AppConstants:
    USER_EMAIL_VALIDATION_ERROR_MESSAGE = "You must provide a valid email address"
    NO_USERNAME_ERROR_MESSAGE = "You must provide a valid username"
    NO_FIRSTNAME_ERROR_MESSAGE = "User must provide a first name"
    NO_LASTNAME_ERROR_MESSAGE = "User must provide a last name"
    NO_PASSWORD_ERROR_MESSAGE = "You must provide a valid password"
    NO_EMAIL_SET_ERROR_MESSAGE = "The email must be set"
    CREATE_SUPERUSER_IS_STAFF_IS_NOT_TRUE_ERROR_MESSAGE = (
        "Superuser must have is_staff=True"
    )
    CREATE_SUPERUSER_IS_SUPERUSER_IS_NOT_TRUE_ERROR_MESSAGE = (
        "Superuser must have is_superuser=True."
    )
