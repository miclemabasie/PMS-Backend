"""
Production settings for Django project
--------------------------------------
Imports everything from base.py and overrides with production-specific settings.
"""

from .base import *
import os

# -----------------------------
# Security
# -----------------------------
DEBUG = False  # Must be False in production
SECRET_KEY = env("SECRET_KEY")  # Must be set in production env

# Hosts allowed to access the application
ALLOWED_HOSTS = env.list("ALLOWED_HOSTS", default=["example.com"])  # e.g., your domain

# -----------------------------
# Database (PostgreSQL)
# -----------------------------
DATABASES = {
    "default": {
        "ENGINE": env("POSTGRES_ENGINE", default="django.db.backends.postgresql"),
        "NAME": env("POSTGRES_DB"),
        "USER": env("POSTGRES_USER"),
        "PASSWORD": env("POSTGRES_PASSWORD"),
        "HOST": env("PG_HOST", default="localhost"),
        "PORT": env("PG_PORT", default="5432"),
        "CONN_MAX_AGE": 600,  # Persistent DB connections for performance
        "OPTIONS": {"sslmode": "require"},  # Enforce SSL for production DB
    }
}

# -----------------------------
# Static & Media files
# -----------------------------
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"  # Collected static files
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "mediafiles"

# -----------------------------
# Email (production)
# -----------------------------
EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = env("EMAIL_HOST", default="smtp.gmail.com")
EMAIL_PORT = env("EMAIL_PORT", default=587)
EMAIL_USE_TLS = True
EMAIL_HOST_USER = env("EMAIL_HOST_USER")
EMAIL_HOST_PASSWORD = env("EMAIL_HOST_PASSWORD")
DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL", default="no-reply@example.com")

# -----------------------------
# Caching (production)
# -----------------------------
CACHES = {
    "default": {
        "BACKEND": env(
            "CACHE_BACKEND", default="django.core.cache.backends.redis.RedisCache"
        ),
        "LOCATION": env("CACHE_LOCATION", default="redis:redis:6379/1"),
        "OPTIONS": {
            "CLIENT_CLASS": env(
                "OPTIONS_CLIENT_CLASS", default="django_redis.client.DefaultClient"
            )
        },
    }
}

# -----------------------------
# Security headers
# -----------------------------
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_SSL_REDIRECT = True
SECURE_HSTS_SECONDS = 31536000  # 1 year
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

# -----------------------------
# Logging (production)
# -----------------------------
import logging

LOG_LEVEL = "INFO"  # Less verbose for production

for logger_name in ["", "apps", "channels", "channels.layers"]:
    logger = logging.getLogger(logger_name)
    logger.setLevel(LOG_LEVEL)

# -----------------------------
# Trusted origins for CSRF
# -----------------------------
CSRF_TRUSTED_ORIGINS = env.list("CSRF_TRUSTED_ORIGINS", default=ALLOWED_HOSTS)
