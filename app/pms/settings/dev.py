"""
Development settings for Django project
---------------------------------------
Imports everything from base.py and overrides development-specific settings.
"""

from .base import *
from pathlib import Path
import os

# -----------------------------
# Debugging
# -----------------------------
DEBUG = True
ALLOWED_HOSTS = [
    "localhost",
    "127.0.0.1",
    "leading-kite-wise.ngrok-free.app",
    "https://leading-kite-wise.ngrok-free.app",
]

# -----------------------------
# Secret key (development)
# -----------------------------
SECRET_KEY = env("SECRET_KEY", default="dev-secret-key")

# -----------------------------
# Database (PostgreSQL for dev)
# -----------------------------
DATABASES = {
    "default": {
        "ENGINE": env("POSTGRES_ENGINE", default="django.db.backends.postgresql"),
        "NAME": env("POSTGRES_DB", default="djangostarter"),
        "USER": env("POSTGRES_USER", default="postgresadmin"),
        "PASSWORD": env("POSTGRES_PASSWORD", default="postgrespass"),
        "HOST": env("PG_HOST", default="localhost"),
        "PORT": env("PG_PORT", default="5432"),
    }
}

# -----------------------------
# Cache (optional local dev cache)
# -----------------------------
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "unique-dev-cache",
    }
}

# -----------------------------
# Email backend (development)
# -----------------------------
EMAIL_BACKEND = env("EMAIL_BACKEND")  # 'database' or 'smtp'

# Fallback SMTP settings (used only if EMAIL_BACKEND='smtp' or no active EmailConfiguration)
EMAIL_HOST = env("EMAIL_HOST")
EMAIL_PORT = env.int("EMAIL_PORT", default=587)
EMAIL_HOST_USER = env("EMAIL_HOST_USER", default="")
EMAIL_HOST_PASSWORD = env("EMAIL_HOST_PASSWORD", default="")
EMAIL_USE_TLS = env.bool("EMAIL_USE_TLS", default=True)
DEFAULT_FROM_EMAIL = "Blizton <noreply@blizton.com>"

print(
    EMAIL_HOST,
    EMAIL_BACKEND,
    EMAIL_HOST_USER,
    EMAIL_HOST_PASSWORD,
    EMAIL_USE_TLS,
    DEFAULT_FROM_EMAIL,
)

# -----------------------------
# Static & Media files
# -----------------------------
STATIC_URL = "/staticfiles/"
MEDIA_URL = "/mediafiles/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"
MEDIA_ROOT = BASE_DIR / "mediafiles"

# -----------------------------
# Logging overrides for development
# -----------------------------
import logging

LOG_LEVEL = "DEBUG"  # Verbose logging for dev

for logger_name in ["", "apps", "channels", "channels.layers"]:
    logger = logging.getLogger(logger_name)
    logger.setLevel(logging.DEBUG)


# -----------------------------
# Dev tools (Django Extensions)
# -----------------------------
SHELL_PLUS_PRINT_SQL = True
GRAPH_MODELS = {"all_applications": True, "group_models": True}

# -----------------------------
# Trusted origins for dev
# -----------------------------
CSRF_TRUSTED_ORIGINS = [
    "http://localhost",
    "http://127.0.0.1",
    "https://leading-kite-wise.ngrok-free.app",
]
