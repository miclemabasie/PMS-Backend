# 📄 `docs/GETTING_STARTED/env-variables.md`

> **Purpose**: Complete reference for all environment variables used by the PMS backend.  
> **Sync Check**: This file is validated against `app/.env.example` via `make docs-check`.

---

## 🗂️ Table of Contents

- [📄 `docs/GETTING_STARTED/env-variables.md`](#-docsgetting_startedenv-variablesmd)
  - [🗂️ Table of Contents](#️-table-of-contents)
  - [🔑 Project Identification](#-project-identification)
  - [⚙️ Django Core](#️-django-core)
  - [🗄️ Database (PostgreSQL)](#️-database-postgresql)
  - [⚡ Redis / Celery](#-redis--celery)
  - [📧 Email Configuration](#-email-configuration)
  - [📱 SMS Configuration](#-sms-configuration)
  - [☁️ Cloudflare R2 / S3 Storage](#️-cloudflare-r2--s3-storage)
  - [🔑 Third-Party API Keys](#-third-party-api-keys)
  - [🐳 Docker / CI/CD](#-docker--cicd)
  - [🔐 Security Best Practices](#-security-best-practices)
  - [🔄 How to Add a New Variable](#-how-to-add-a-new-variable)

---

## 🔑 Project Identification

| Variable           | Required | Default     | Description                                                                                          |
| ------------------ | -------- | ----------- | ---------------------------------------------------------------------------------------------------- |
| `PROJECT_NAME_ENV` | ✅       | `pms`       | Project identifier used by Makefile and `rename_project` command                                     |
| `SITE_NAME`        | ✅       | `Blizton`   | Human-readable name for emails, templates, and branding                                              |
| `DOMAIN`           | ✅       | `localhost` | Base URL for absolute links (activation, password reset). Use `https://yourdomain.com` in production |

---

## ⚙️ Django Core

| Variable               | Required | Default                                       | Description                                                                                                                                                           |
| ---------------------- | -------- | --------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `SECRET_KEY`           | ✅       | _(none)_                                      | Django cryptographic signing key. **Generate securely**: `python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"` |
| `SIGNING_KEY`          | ✅       | _(none)_                                      | JWT token signing key. Must be different from `SECRET_KEY` and equally strong                                                                                         |
| `DEBUG`                | ✅       | `True`                                        | Enable debug mode. **Set to `False` in production**                                                                                                                   |
| `ALLOWED_HOSTS`        | ✅       | `localhost,127.0.0.1`                         | Comma-separated list of host/domain names Django will serve. Use `*` only for local dev                                                                               |
| `CSRF_TRUSTED_ORIGINS` | ⚠️       | `http://localhost:3000,http://localhost:8080` | Comma-separated origins allowed for CSRF-protected POST requests (e.g., frontend domains)                                                                             |

---

## 🗄️ Database (PostgreSQL)

| Variable            | Required | Default                         | Description                                                             |
| ------------------- | -------- | ------------------------------- | ----------------------------------------------------------------------- |
| `POSTGRES_ENGINE`   | ✅       | `django.db.backends.postgresql` | Django database backend. Usually don't change                           |
| `POSTGRES_DB`       | ✅       | `pms`                           | PostgreSQL database name                                                |
| `POSTGRES_USER`     | ✅       | `postgresadmin`                 | PostgreSQL username                                                     |
| `POSTGRES_PASSWORD` | ✅       | _(none)_                        | PostgreSQL password. **Never commit real values**                       |
| `PG_HOST`           | ✅       | `postgres-db`                   | PostgreSQL host. Use `localhost` for local dev, service name for Docker |
| `PG_PORT`           | ✅       | `5432`                          | PostgreSQL port                                                         |

---

## ⚡ Redis / Celery

| Variable                | Required | Default                             | Description                               |
| ----------------------- | -------- | ----------------------------------- | ----------------------------------------- |
| `CELERY_BROKER_URL`     | ✅       | `redis://redis:6379/0`              | Redis URL for Celery task queue broker    |
| `CELERY_RESULT_BACKEND` | ✅       | `redis://redis:6379/0`              | Redis URL for storing Celery task results |
| `CACHE_BACKEND`         | ⚠️       | `django_redis.cache.RedisCache`     | Django cache backend class                |
| `CACHE_LOCATION`        | ⚠️       | `redis://redis:6379/0`              | Redis URL for Django caching              |
| `OPTIONS_CLIENT_CLASS`  | ⚠️       | `django_redis.client.DefaultClient` | Redis client class for django-redis       |

---

## 📧 Email Configuration

| Variable              | Required | Default                                       | Description                                                  |
| --------------------- | -------- | --------------------------------------------- | ------------------------------------------------------------ |
| `EMAIL_BACKEND`       | ⚠️       | `django.core.mail.backends.smtp.EmailBackend` | Django email backend. Use `console` for local testing        |
| `EMAIL_HOST`          | ⚠️       | `smtp.gmail.com`                              | SMTP server hostname                                         |
| `EMAIL_PORT`          | ⚠️       | `587`                                         | SMTP port (587 for TLS, 465 for SSL)                         |
| `EMAIL_HOST_USER`     | ⚠️       | _(none)_                                      | SMTP authentication username                                 |
| `EMAIL_HOST_PASSWORD` | ⚠️       | _(none)_                                      | SMTP authentication password or app-specific token           |
| `EMAIL_USE_TLS`       | ⚠️       | `True`                                        | Enable TLS encryption for SMTP                               |
| `EMAIL_USE_SSL`       | ⚠️       | `False`                                       | Enable SSL encryption for SMTP (mutually exclusive with TLS) |
| `DEFAULT_FROM_EMAIL`  | ⚠️       | `noreply@example.com`                         | Default "From" address for system emails                     |

---

## 📱 SMS Configuration

| Variable              | Required | Default   | Description                                                             |
| --------------------- | -------- | --------- | ----------------------------------------------------------------------- |
| `SMS_BACKEND`         | ⚠️       | `console` | SMS provider: `console` (logs to terminal), `twilio`, or custom backend |
| `TWILIO_ACCOUNT_SID`  | ⚠️       | _(none)_  | Twilio Account SID (required if `SMS_BACKEND=twilio`)                   |
| `TWILIO_AUTH_TOKEN`   | ⚠️       | _(none)_  | Twilio Auth Token (required if `SMS_BACKEND=twilio`)                    |
| `TWILIO_PHONE_NUMBER` | ⚠️       | _(none)_  | Twilio phone number in E.164 format (e.g., `+1234567890`)               |

---

## ☁️ Cloudflare R2 / S3 Storage

| Variable                        | Required | Default   | Description                                                          |
| ------------------------------- | -------- | --------- | -------------------------------------------------------------------- |
| `CLOUDFLARE_R2_BUCKET`          | ⚠️       | _(empty)_ | R2 bucket name for media file storage                                |
| `CLOUDFLARE_R2_BUCKET_ENDPOINT` | ⚠️       | _(empty)_ | R2 endpoint URL (e.g., `https://<account>.r2.cloudflarestorage.com`) |
| `CLOUDFLARE_R2_ACCESS_KEY`      | ⚠️       | _(empty)_ | R2 access key ID                                                     |
| `CLOUDFLARE_R2_SECRET_KEY`      | ⚠️       | _(empty)_ | R2 secret access key                                                 |
| `CLOUDFLARE_R2_TOKEN`           | ⚠️       | _(empty)_ | Optional R2 bearer token for token-based auth                        |

> 💡 **Note**: Leave empty to use local filesystem storage (`MEDIA_ROOT`). Populate to enable cloud storage via `django-storages`.

---

## 🔑 Third-Party API Keys

| Variable              | Required | Default  | Description                                                 |
| --------------------- | -------- | -------- | ----------------------------------------------------------- |
| `GOOGLE_MAPS_API_KEY` | ⚠️       | _(none)_ | Google Maps Platform key for geocoding, maps, or places API |

---

## 🐳 Docker / CI/CD

| Variable          | Required | Default  | Description                                                       |
| ----------------- | -------- | -------- | ----------------------------------------------------------------- |
| `DOCKERHUB_USER`  | ⚠️       | _(none)_ | Docker Hub username for CI/CD image pushes                        |
| `DOCKERHUB_TOKEN` | ⚠️       | _(none)_ | Docker Hub access token (use Personal Access Token, not password) |

---

## 🔐 Security Best Practices

1. **Never commit `.env`** – Add to `.gitignore`:

   ```gitignore
   # Local environment secrets
   app/.env
   app/.env.local
   app/.env.*.local
   ```

2. **Use secrets management in production**:
   - AWS Secrets Manager
   - HashiCorp Vault
   - Docker secrets (`/run/secrets/`)
   - Kubernetes Secrets

3. **Rotate keys regularly**:

   ```bash
   # Generate new Django SECRET_KEY
   python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"

   # Generate new JWT SIGNING_KEY
   python -c "import secrets; print(secrets.token_urlsafe(50))"
   ```

4. **Validate on startup** (optional):
   ```python
   # apps/core/management/commands/check_env.py
   REQUIRED = ["SECRET_KEY", "SIGNING_KEY", "POSTGRES_PASSWORD"]
   for var in REQUIRED:
       if not os.getenv(var):
           raise ImproperlyConfigured(f"Missing required env var: {var}")
   ```

---

## 🔄 How to Add a New Variable

1. Add to `app/.env.example` with a placeholder value
2. Add documentation row to this file under the appropriate section
3. Update `scripts/check_env_docs.py` regex if using non-standard formatting
4. Run `make docs-check` to verify sync

```markdown
| `NEW_VARIABLE` | ✅ | `default` | Clear description of purpose and usage |
```

---

> ✅ **Validation**: This file is automatically checked against `app/.env.example` by running `make docs-check` or via pre-commit hooks.

_Last Updated: {{ date }} • Maintained by: Miclem Abasie_
