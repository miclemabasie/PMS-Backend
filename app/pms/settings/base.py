"""
Django Base Settings File
-------------------------
This file contains the core Django settings for the project, including:

- Installed applications (Django, third-party, and local apps)
- Middleware
- Database and cache configuration
- Authentication, REST framework, JWT, Djoser
- Static & media files
- Channels (WebSocket)
- Logger configuration
"""

import logging
import logging.config
from datetime import timedelta
from pathlib import Path

import environ
from django.utils.log import DEFAULT_LOGGING

import helpers.cloudflare.settings  # Cloudflare storage integration

# -----------------------------
# Environment configuration
# -----------------------------
env = environ.Env(DEBUG=(bool, False))
BASE_DIR = Path(__file__).resolve().parent.parent.parent
environ.Env.read_env(BASE_DIR / ".env")

# -----------------------------
# Security
# -----------------------------
SECRET_KEY = env(
    "SECRET_KEY", default="django-insecure-t+4t*bp23a-n1o8##..."
)  # Keep secret in production
DEBUG = env("DEBUG", default=True)
ALLOWED_HOSTS = env.list("ALLOWED_HOSTS", default=[])

# -----------------------------
# Applications
# -----------------------------
DJANGO_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    # "django.contrib.sites",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
]

LOCAL_APPS = [
    "apps.users.apps.UsersConfig",
    "apps.core.apps.CoreConfig",
    "apps.notifications.apps.NotificationsConfig",
    "apps.rentals.apps.RentalsConfig",
    "apps.tenants.apps.TenantsConfig",
    "apps.properties.apps.PropertiesConfig",
    "apps.payments.apps.PaymentsConfig",
]

THIRD_PARTY_APPS = [
    "modeltranslation",
    "autoslug",
    "django_extensions",
    # "django_elasticsearch_dsl",
    "allauth",
    "allauth.socialaccount",
    "allauth.socialaccount.providers.google",
    "allauth.account",
    "corsheaders",
    "rest_framework",
    "rest_framework_simplejwt",
    "djoser",
    "djcelery_email",
    "drf_spectacular",
]

INSTALLED_APPS = DJANGO_APPS + LOCAL_APPS + THIRD_PARTY_APPS

# -----------------------------
# Middleware
# -----------------------------
MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "allauth.account.middleware.AccountMiddleware",
]

ROOT_URLCONF = "pms.urls"

DOMAIN = env("DOMAIN", default="http://localhost")

# -----------------------------
# Templates
# -----------------------------
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "pms.wsgi.application"

# -----------------------------
# Channels (WebSocket)
# -----------------------------
CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {
            "hosts": [("redis", 6379)],
        },
    },
}

# -----------------------------
# Storage
# -----------------------------
# STORAGES = {
#     "default": {
#         "BACKEND": "helpers.cloudflare.storages.MediaFileStorage",
#         "OPTIONS": helpers.cloudflare.settings.CLOUDFLARE_R2_CONFIG_OPTIONS,
#     },
#     "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
# }

# -----------------------------
# Database
# -----------------------------
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

# -----------------------------
# Elasticsearch
# -----------------------------
# ELASTICSEARCH_DSL = {"default": {"hosts": "http://elasticsearch:9200"}}

# -----------------------------
# Email & CORS
# -----------------------------
DEFAULT_FROM_EMAIL = "example@gmail.com"
CORS_ALLOW_ALL_ORIGINS = True
CORS_ALLOW_CREDENTIALS = True
CORS_ALLOW_HEADERS = [
    "content-type",
    "authorization",
    "x-requested-with",
    "accept",
    "origin",
]
CORS_ALLOW_METHODS = ["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"]

SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

# -----------------------------
# Caches
# -----------------------------
CACHES = {
    "default": {
        "BACKEND": env("CACHE_BACKEND"),
        "LOCATION": env("CACHE_LOCATION"),
        "OPTIONS": {"CLIENT_CLASS": env("OPTIONS_CLIENT_CLASS")},
    }
}

CSRF_TRUSTED_ORIGINS = ["http://localhost", "http://127.0.0.1"]

SITE_ID = 1


# -----------------------------
# Authentication & Accounts
# -----------------------------
AUTH_USER_MODEL = "users.User"
LOGIN_REDIRECT_URL = "/"
LOGOUT_REDIRECT_URL = "/"

ACCOUNT_AUTHENTICATION_METHOD = "email"
ACCOUNT_USERNAME_REQUIRED = False
ACCOUNT_EMAIL_REQUIRED = True
ACCOUNT_UNIQUE_EMAIL = True
ACCOUNT_EMAIL_VERIFICATION = "optional"

AUTHENTICATION_BACKENDS = [
    "django.contrib.auth.backends.ModelBackend",
    "allauth.account.auth_backends.AuthenticationBackend",
]

# -----------------------------
# Password validation
# -----------------------------
AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"
    },
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# -----------------------------
# Django REST Framework
# -----------------------------
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
    "DEFAULT_FILTER_BACKENDS": ["django_filters.rest_framework.DjangoFilterBackend"],
    "DEFAULT_RENDERER_CLASSES": ("rest_framework.renderers.JSONRenderer",),
    "NON_FIELD_ERRORS_KEY": "error",
    "EXCEPTION_HANDLER": "rest_framework.views.exception_handler",
}

SIMPLE_JWT = {
    "AUTH_HEADER_TYPES": ("Bearer", "JWT"),
    "ACCESS_TOKEN_LIFETIME": timedelta(days=10),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=20),
    "SIGNING_KEY": env("SIGNING_KEY"),
    "AUTH_HEADER_NAME": "HTTP_AUTHORIZATION",
    "AUTH_TOKEN_CLASSES": ("rest_framework_simplejwt.tokens.AccessToken",),
}

# -----------------------------
# Djoser
# -----------------------------
DJOSER = {
    "LOGIN_FIELD": "email",
    "USER_CREATE_PASSWORD_RETYPE": True,
    "SEND_ACTIVATION_EMAIL": False,
    "SEND_CONFIRMATION_EMAIL": False,
    "ACTIVATION_URL": "activate/{uid}/{token}",
    "PASSWORD_RESET_CONFIRM_URL": "password-reset/{uid}/{token}",
    "USERNAME_RESET_CONFIRM_URL": "username-reset/{uid}/{token}",
    "SERIALIZERS": {
        "user_create": "apps.users.api.serializers.UserCreateSerializer",
        "user_create_password_retype": "apps.users.api.serializers.UserCreateSerializer",
        "user": "apps.users.api.serializers.UserSerializer",
        "current_user": "apps.users.api.serializers.UserSerializer",
        "user_delete": "djoser.serializers.UserDeleteSerializer",
    },
    "PERMISSIONS": {
        "user_create": ["rest_framework.permissions.AllowAny"],
        "user": ["rest_framework.permissions.IsAuthenticated"],
        "user_delete": ["rest_framework.permissions.IsAuthenticated"],
        "current_user": ["rest_framework.permissions.IsAuthenticated"],
        "activation": ["rest_framework.permissions.AllowAny"],
        "password_reset": ["rest_framework.permissions.AllowAny"],
        "password_reset_confirm": ["rest_framework.permissions.AllowAny"],
        "password_change": ["rest_framework.permissions.IsAuthenticated"],
        "password_change_confirm": ["rest_framework.permissions.IsAuthenticated"],
        "user_list": ["rest_framework.permissions.IsAuthenticated"],
    },
    "HIDE_USERS": False,
    "PASSWORD_RESET_SHOW_EMAIL_NOT_FOUND": True,
}
# -----------------------------
# Internationalization
# -----------------------------
LANGUAGE_CODE = "en-us"
TIME_ZONE = "Africa/Douala"
USE_I18N = True
USE_TZ = True

# -----------------------------
# Static & Media
# -----------------------------
STATIC_URL = "/staticfiles/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"]

MEDIA_URL = "/mediafiles/"
MEDIA_ROOT = BASE_DIR / "mediafiles"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"


# --- Notifications ---
SITE_NAME = env("SITE_NAME", default="Django Starter")
EMAIL_BACKEND = env("EMAIL_BACKEND", default="database")  # 'database' or 'smtp'

# Fallback SMTP settings (used only if EMAIL_BACKEND='smtp' or no active EmailConfiguration)
EMAIL_HOST = env("EMAIL_HOST", default="smtp.gmail.com")
EMAIL_PORT = env.int("EMAIL_PORT", default=587)
EMAIL_HOST_USER = env("EMAIL_HOST_USER", default="")
EMAIL_HOST_PASSWORD = env("EMAIL_HOST_PASSWORD", default="")
EMAIL_USE_TLS = env.bool("EMAIL_USE_TLS", default=True)
DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL", default="noreply@example.com")
# -----------------------------
# Logger configuration
# -----------------------------
LOG_FILE_NAME = "django.log"
LOG_LEVEL = env("LOG_LEVEL", default="INFO")

logging.config.dictConfig(
    {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            # Console formatter with safe context
            "console": {
                "format": "%(asctime)s %(name)-30s %(levelname)-8s %(message)s %(context)s",
                "class": "apps.core.logger_formatter.SafeContextFormatter",
            },
            "file": {
                "format": "%(asctime)s %(name)-30s %(levelname)-8s %(message)s %(context)s",
                "class": "apps.core.logger_formatter.SafeContextFormatter",
            },
            "django.server": DEFAULT_LOGGING["formatters"]["django.server"],
        },
        "handlers": {
            "console": {"class": "logging.StreamHandler", "formatter": "console"},
            "file": {
                "level": LOG_LEVEL,
                "class": "logging.FileHandler",
                "formatter": "file",
                "filename": BASE_DIR / "logs" / LOG_FILE_NAME,
            },
            "django.server": DEFAULT_LOGGING["handlers"]["django.server"],
        },
        "loggers": {
            "": {
                "level": LOG_LEVEL,
                "handlers": ["console", "file"],
                "propagate": False,
            },
            "apps": {
                "level": LOG_LEVEL,
                "handlers": ["console", "file"],
                "propagate": False,
            },
            "django.server": DEFAULT_LOGGING["loggers"]["django.server"],
            "channels": {
                "level": "DEBUG",
                "handlers": ["console", "file"],
                "propagate": False,
            },
            "channels.layers": {
                "level": "DEBUG",
                "handlers": ["console", "file"],
                "propagate": False,
            },
        },
    }
)
