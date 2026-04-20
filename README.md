# 🏢 Property Management System (PMS) Backend

> ⚠️ **PROPRIETARY SOFTWARE**  
> This codebase is confidential and proprietary. Unauthorized copying, distribution, modification, or use is strictly prohibited. © 2026 All Rights Reserved.

[![Python](https://img.shields.io/badge/Python-3.12-blue?logo=python)](https://www.python.org/)
[![Django](https://img.shields.io/badge/Django-5.2-092E20?logo=django)](https://www.djangoproject.com/)
[![DRF](https://img.shields.io/badge/DRF-3.14-red?logo=django)](https://www.django-rest-framework.org/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-336791?logo=postgresql)](https://www.postgresql.org/)
[![Redis](https://img.shields.io/badge/Redis-6.0-DC382D?logo=redis)](https://redis.io/)
[![Celery](https://img.shields.io/badge/Celery-5.4-37814A?logo=celery)](https://docs.celeryq.dev/)
[![Docker](https://img.shields.io/badge/Docker-✓-2496ED?logo=docker)](https://www.docker.com/)
[![License](https://img.shields.io/badge/License-Proprietary-red)](#license)

---

## 📋 Table of Contents

1. [Overview](#-overview)
2. [Core Features](#-core-features)
3. [Technology Stack](#-technology-stack)
4. [Architecture & Design Patterns](#-architecture--design-patterns)
5. [Project Structure](#-project-structure)
6. [Prerequisites](#-prerequisites)
7. [Installation & Setup](#-installation--setup)
8. [Environment Configuration](#-environment-configuration)
9. [Running the Application](#-running-the-application)
10. [API Documentation](#-api-documentation)
11. [Testing & Quality Assurance](#-testing--quality-assurance)
12. [Docker & Deployment](#-docker--deployment)
13. [Background Tasks (Celery)](#-background-tasks-celery)
14. [Logging & Monitoring](#-logging--monitoring)
15. [Security Considerations](#-security-considerations)
16. [Internationalization (i18n)](#-internationalization-i18n)
17. [File Storage](#-file-storage)
18. [Troubleshooting](#-troubleshooting)
19. [Contributing (Internal)](#-contributing-internal)
20. [License](#-license)

---

## 🌐 Overview

A production-grade, modular Django backend for comprehensive property management operations. The system enables end-to-end management of properties, units, leases, tenants, owners, maintenance workflows, financial tracking, vendor coordination, and automated communications.

Built with clean architecture principles, repository/service patterns, comprehensive test coverage, and containerized deployment support.

### Key Business Capabilities
- 🏠 **Property & Unit Management**: CRUD operations, multilingual descriptions (EN/FR), amenities, images, status tracking
- 👥 **User & Role Management**: Superuser, Manager, Owner, Tenant, Vendor roles with granular permissions
- 📜 **Lease Lifecycle**: Draft → Active → Expired states, term management, tenant linking, renewal/termination workflows
- 🔧 **Maintenance Workflow**: Request submission, priority levels, status transitions (`submitted`→`in_progress`→`completed`/`failed`), vendor assignment, cost tracking
- 💰 **Financial Operations**: Payment processing (Rent/Deposit/Fee/Utility), expense categorization, payout methods (MoMo/Orange/Cash)
- 📎 **Document Management**: Secure file uploads with validation, FK-based relations, Cloudflare R2/S3 support
- 📢 **Broadcast System**: Template-driven email/SMS broadcasting to targeted user groups with delivery tracking
- 🔔 **Notifications**: Real-time alerts via Django Channels + Redis, database-backed notification queue
- 🌍 **Multi-language Support**: `django-modeltranslation` + `gettext_lazy` for bilingual field content

---

## ✨ Core Features

### Authentication & Authorization
- JWT-based authentication via **Djoser** + **djangorestframework-simplejwt**
- Role-based access control (RBAC) with custom permission classes:
  - `IsOwnerOrManagerOrSuperAdmin`
  - `CanManageProperty`
  - `IsTenantOrReadOnly`
  - `IsAdminOrReadOnly`
- Profile-based role assignment (`OwnerProfile`, `ManagerProfile`, `TenantProfile`)
- Query-level filtering: users only access data they're authorized to see

### Domain Modules
| Module | Responsibility |
|--------|---------------|
| `apps.users` | User accounts, profiles, roles, authentication flows |
| `apps.properties` | Properties, units, ownership records, managers, images |
| `apps.rentals` | Leases, payments, payment terms, lease-tenant relationships |
| `apps.tenants` | Tenant profiles, occupancy tracking, lease associations |
| `apps.maintenance` | Maintenance requests, vendor assignments, status workflows |
| `apps.payments` | Payment processing, transaction records, payout methods |
| `apps.accounting` | Expense tracking, categorization, financial reporting |
| `apps.notifications` | Email/SMS backends, template rendering, broadcast tasks |
| `apps.reports` | Aggregated analytics, export utilities (placeholder) |

### Technical Capabilities
- ✅ **Repository Pattern**: `BaseRepository[T]` → `DjangoRepository[T]` for testable data access
- ✅ **Service Layer**: `BaseService[T]` encapsulates business logic, transaction management
- ✅ **Async Task Queue**: Celery + Redis for broadcasts, notifications, background jobs
- ✅ **Structured Logging**: Custom `CustomLogger` with contextual metadata injection
- ✅ **API Documentation**: Auto-generated OpenAPI 3.0 specs via `drf-spectacular`
- ✅ **Testing Suite**: `pytest` + `factory_boy` + `coverage.py` with domain-specific fixtures
- ✅ **i18n Ready**: Bilingual models (`name_en`/`name_fr`), `gettext_lazy` integration
- ✅ **File Storage Abstraction**: `django-storages` backend for S3/Cloudflare R2

---

## 🛠️ Technology Stack

### Core Framework
| Component | Version | Purpose |
|-----------|---------|---------|
| Python | 3.12 | Runtime language |
| Django | 5.2 | Web framework, ORM, admin |
| Django REST Framework | 3.14 | API serialization, viewsets, authentication |
| Djoser | 2.2.3 | User registration, login, password management |
| djangorestframework-simplejwt | 5.3.1 | JWT token authentication |

### Data & Caching
| Component | Version | Purpose |
|-----------|---------|---------|
| PostgreSQL | 16 (Alpine) | Primary relational database |
| Redis | 6.0 (Alpine) | Cache backend, Celery broker, Channels layer |
| django-redis | 5.4.0 | Redis cache integration |
| elasticsearch-dsl | 8.15.1 | Optional full-text search (commented in docker-compose) |

### Async & Background Processing
| Component | Version | Purpose |
|-----------|---------|---------|
| Celery | 5.4.0 | Distributed task queue |
| django-celery-beat | 2.8.1 | Periodic task scheduling |
| django-celery-email | 3.0.0 | Async email sending via Celery |
| flower | 2.0.1 | Celery monitoring dashboard (optional) |

### API & Documentation
| Component | Version | Purpose |
|-----------|---------|---------|
| drf-spectacular | 0.28.0 | OpenAPI 3.0 schema generation |
| drf-spectacular-sidecar | 2025.9.1 | Self-hosted Swagger/ReDoc UI assets |
| django-cors-headers | 4.4.0 | CORS middleware for frontend integration |

### Testing & Quality
| Component | Version | Purpose |
|-----------|---------|---------|
| pytest | 8.3.2 | Test runner |
| pytest-django | 4.9.0 | Django integration for pytest |
| pytest-cov | 5.0.0 | Coverage reporting |
| factory_boy | 3.3.1 | Test data factories |
| Faker | 21.0.0 | Fake data generation |
| coverage | 7.5.4 | Code coverage measurement |
| flake8 | 3.9.2 | PEP8 linting |
| black | 23.12.0 | Code formatting |

### Storage & Files
| Component | Version | Purpose |
|-----------|---------|---------|
| django-storages | 1.14.4 | Abstract file storage backend |
| boto3 | 1.35.15 | AWS S3 client (for R2 compatibility) |
| django-drf-filepond | 0.5.0 | Chunked file upload support |

### Internationalization & Translation
| Component | Version | Purpose |
|-----------|---------|---------|
| django-modeltranslation | 0.19.17 | Field-level translation for models |
| django-parler | 2.3 | Alternative translation framework (optional) |
| django-rosetta | 0.10.2 | Web-based translation file editor |
| deep-translator | 1.11.4 | Programmatic translation utilities |

### Deployment & DevOps
| Component | Version | Purpose |
|-----------|---------|---------|
| Docker | ✓ | Containerization |
| docker-compose | ✓ | Multi-container orchestration |
| Gunicorn | 22.0.0 | WSGI HTTP server for production |
| Nginx | ✓ | Reverse proxy, static file serving |
| django-environ | 0.11.2 | Environment variable management |
| psycopg2-binary | 2.9.9 | PostgreSQL adapter |

---

## 🏗️ Architecture & Design Patterns

### Layered Architecture
```
┌─────────────────────────────────────┐
│            API Layer                │
│  • ViewSets / APIViews              │
│  • Serializers (validation, I/O)    │
│  • Permissions (RBAC enforcement)   │
└────────────┬────────────────────────┘
             │
┌────────────▼────────────────────────┐
│         Service Layer               │
│  • BaseService[T] (generic CRUD)    │
│  • Domain-specific services         │
│  • Transaction management (@transaction.atomic) │
│  • Business rule enforcement        │
└────────────┬────────────────────────┘
             │
┌────────────▼────────────────────────┐
│       Repository Layer              │
│  • BaseRepository[T] (ABC interface)│
│  • DjangoRepository[T] (ORM impl.)  │
│  • Query abstraction & filtering    │
└────────────┬────────────────────────┘
             │
┌────────────▼────────────────────────┐
│        Data Layer                   │
│  • Django Models (with translations)│
│  • PostgreSQL schema                │
│  • Signals for side-effects         │
└─────────────────────────────────────┘
```

### Key Patterns Implemented
1. **Generic Repository Pattern**
   ```python
   # apps/core/base_repository.py
   class BaseRepository(ABC, Generic[T]):
       @abstractmethod
       def get(self, id: Any) -> Optional[T]: ...
       @abstractmethod
       def filter(self, **filters) -> List[T]: ...
       @abstractmethod
       def create(self, **data) -> T: ...
       @abstractmethod
       def update(self, instance: T, **data) -> T: ...
       @abstractmethod
       def delete(self, instance: T) -> None: ...
   ```

2. **Service Layer with Dependency Injection**
   ```python
   # apps/core/base_service.py
   class BaseService(Generic[T]):
       def __init__(self, repository: BaseRepository[T]):
           self.repository = repository
       
       def get_by_id(self, id) -> Optional[T]:
           return self.repository.get(id)
   ```

3. **Role-Aware Query Filtering**
   ```python
   # Example: PropertyRepository.filter_for_user()
   if user.is_superuser:
       return qs  # Full access
   elif hasattr(user, 'owner_profile'):
       return qs.filter(ownership_records__owner=user.owner_profile)
   elif hasattr(user, 'manager_profile'):
       return qs.filter(managers=user.manager_profile)
   else:
       return qs.none()  # Default deny
   ```

4. **Async Task Decoupling**
   ```python
   # apps/notifications/tasks.py
   @shared_task(bind=True, max_retries=3)
   def send_broadcast_email(self, broadcast_id: str, recipient_emails: List[str]):
       # Template rendering + email dispatch via Celery
       ...
   ```

---

## 📁 Project Structure

```
.
├── app/                          # Django project root (managed via WORKDIR)
│   ├── apps/                     # Domain-driven Django apps
│   │   ├── accounting/           # Financial expense tracking
│   │   ├── core/                 # Shared utilities, base classes, logging
│   │   ├── maintenance/          # Maintenance request workflows
│   │   ├── notifications/        # Email/SMS broadcast system
│   │   ├── payments/             # Payment processing logic
│   │   ├── properties/           # Property/unit management
│   │   ├── rentals/              # Leases, payments, tenant links
│   │   ├── reports/              # Analytics & export utilities
│   │   ├── tenants/              # Tenant profiles & occupancy
│   │   └── users/                # Authentication, profiles, roles
│   │       └── api/              # DRF views, serializers, permissions
│   ├── helpers/                  # Cross-cutting utilities
│   │   ├── cloudflare/           # R2 storage configuration
│   │   └── storages/             # Custom storage mixins
│   ├── htmlcov/                  # Coverage.py HTML reports
│   ├── logs/                     # Application log files
│   ├── manage.py                 # Django management entrypoint
│   ├── pms/                      # Project configuration package
│   │   ├── settings/             # base.py, dev.py, prod.py
│   │   ├── urls.py               # Root URL router
│   │   ├── celery.py             # Celery app configuration
│   │   ├── asgi.py / wsgi.py     # ASGI/WSGI entrypoints
│   │   └── __init__.py
│   ├── pytest.ini                # Pytest configuration
│   └── conftest.py               # Pytest fixtures & plugins
│
├── docker/                       # Containerization assets
│   └── local/
│       ├── django/
│       │   ├── Dockerfile        # Python 3.12-slim base
│       │   ├── entrypoint        # Container init script
│       │   ├── start             # Django server launcher
│       │   └── celery/
│       │       ├── worker/start  # Celery worker entrypoint
│       │       └── flower/start  # Flower monitor entrypoint
│       └── nginx/
│           ├── Dockerfile
│           └── default.conf      # Reverse proxy config
│
├── docker-compose.yml            # Multi-service orchestration
├── requirements.txt              # Python dependencies (pinned)
├── pyproject.toml                # Modern Python project metadata
├── makefile                      # Common dev commands
├── PMS API.postman_collection.json  # API testing collection
├── LICENSE                       # Proprietary license terms
└── README.md                     # This file
```

---

## 📦 Prerequisites

### Local Development
- Python 3.12+
- PostgreSQL 16+ (or Docker)
- Redis 6.0+ (or Docker)
- `pip` + `virtualenv` or `poetry`
- Docker & Docker Compose (for containerized workflow)

### Production Deployment
- Linux server (Ubuntu 22.04 LTS recommended)
- Docker Engine 24+ & Docker Compose v2+
- Reverse proxy (Nginx) with SSL termination
- Persistent volume storage for PostgreSQL, media, static files
- Environment variable management (`.env` or secret manager)

---

## 🚀 Installation & Setup

### Option 1: Docker Compose (Recommended)

```bash
# 1. Clone repository
git clone <repository-url>
cd pms-backend

# 2. Configure environment
cp app/.env.example app/.env
# Edit app/.env with your secrets (see Configuration section)

# 3. Build and start services
docker-compose up -d --build

# 4. Run migrations
docker-compose exec api python manage.py migrate

# 5. Create superuser
docker-compose exec api python manage.py createsuperuser

# 6. Verify services
curl http://localhost/api/v1/auth/jwt/create/  # Should return 405 (POST required)
```

### Option 2: Local Development (Without Docker)

```bash
# 1. Clone and setup virtual environment
git clone <repository-url>
cd pms-backend
python3.12 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 2. Install dependencies
pip install --upgrade pip
pip install -r requirements.txt

# 3. Configure environment
cp app/.env.example app/.env
# Edit app/.env (see Configuration section)

# 4. Setup database (ensure PostgreSQL is running)
python app/manage.py migrate

# 5. Create superuser
python app/manage.py createsuperuser

# 6. Start development server
cd app
python manage.py runserver 8000

# 7. Start Celery worker (separate terminal)
celery -A pms.celery worker -l info --pool=solo

# 8. (Optional) Start Celery beat for periodic tasks
celery -A pms.celery beat -l info
```

---

## ⚙️ Environment Configuration

Create `app/.env` based on `app/.env.example`:

```ini
# === Django Core ===
SECRET_KEY=your-32-char-min-secret-key-here
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1,[::1]

# === Database (PostgreSQL) ===
DATABASE_URL=postgres://user:password@postgres-db:5432/pms_db
# Local dev alternative:
# DATABASE_URL=postgres://localhost:5432/pms_db

# === Cache & Broker (Redis) ===
REDIS_URL=redis://redis:6379/0
CELERY_BROKER_URL=redis://redis:6379/0
CELERY_RESULT_BACKEND=redis://redis:6379/0

# === Email Configuration ===
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.example.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=your-email@example.com
EMAIL_HOST_PASSWORD=your-email-password
DEFAULT_FROM_EMAIL=noreply@example.com

# === File Storage ===
# Local (dev):
DEFAULT_FILE_STORAGE=django.core.files.storage.FileSystemStorage
MEDIA_ROOT=/app/mediafiles
MEDIA_URL=/media/

# Cloudflare R2 / S3 (prod):
# DEFAULT_FILE_STORAGE=helpers.cloudflare.storages.CloudflareR2Storage
# AWS_ACCESS_KEY_ID=your-r2-access-key
# AWS_SECRET_ACCESS_KEY=your-r2-secret-key
# AWS_STORAGE_BUCKET_NAME=your-bucket-name
# AWS_S3_ENDPOINT_URL=https://<account-id>.r2.cloudflarestorage.com
# AWS_S3_CUSTOM_DOMAIN=<your-domain>.r2.dev

# === Authentication ===
DJOSER={
  "USER_ID_FIELD": "pkid",
  "LOGIN_FIELD": "email",
  "SEND_ACTIVATION_EMAIL": False,
  "PASSWORD_RESET_CONFIRM_URL": "reset-password/{uid}/{token}",
  "USERNAME_RESET_CONFIRM_URL": "username/reset/confirm/{uid}/{token}",
  "ACTIVATION_URL": "activate/{uid}/{token}",
  "SERIALIZERS": {
    "user_create": "apps.users.api.serializers.UserCreateSerializer",
    "current_user": "apps.users.api.serializers.UserSerializer"
  }
}
SIMPLE_JWT={
  "ACCESS_TOKEN_LIFETIME": "timedelta(minutes=60)",
  "REFRESH_TOKEN_LIFETIME": "timedelta(days=7)",
  "AUTH_HEADER_TYPES": ("Bearer",)
}

# === API Documentation ===
SPECTACULAR_SETTINGS={
  "TITLE": "PMS API",
  "DESCRIPTION": "Property Management System Backend",
  "VERSION": "1.0.0",
  "SERVE_INCLUDE_SCHEMA": false
}

# === Logging ===
LOG_LEVEL=INFO
LOG_FILE=/app/logs/pms.log
DJANGO_LOG_FILE=/app/logs/django.log

# === Internationalization ===
LANGUAGE_CODE=en-us
USE_I18N=True
USE_L10N=True
LANGUAGES=(("en", "English"), ("fr", "French"))
MODELTRANSLATION_DEFAULT_LANGUAGE="en"
MODELTRANSLATION_FALLBACK_LANGUAGES=("en", "fr")
```

> 🔐 **Security Note**: Never commit `.env` files. Use secret management in production (AWS Secrets Manager, HashiCorp Vault, etc.).

---

## ▶️ Running the Application

### Development Commands

*See `makefile` for all possible commands*

```bash
# Navigate to Django project directory
cd app

# Database migrations
python manage.py makemigrations
python manage.py migrate

# Create admin user
python manage.py createsuperuser

# Run development server
python manage.py runserver 8000

# Collect static files (for production)
python manage.py collectstatic --noinput

# Run tests
pytest  # All tests
pytest apps/properties/tests/  # Module-specific
pytest --cov=apps --cov-report=html  # With coverage

# Code quality
black .  # Format code
flake8 apps/  # Lint
isort .  # Sort imports

# Management commands
python manage.py shell  # Interactive Django shell
python manage.py shell_plus  # With auto-imports (django-extensions)
python manage.py show_urls  # List all URL patterns
```

### Celery Task Management

```bash
# Start worker (development)
celery -A pms.celery worker -l info --pool=solo

# Start worker (production)
celery -A pms.celery worker -l info -c 4

# Start beat scheduler (for periodic tasks)
celery -A pms.celery beat -l info

# Monitor with Flower (if enabled)
# Access at http://localhost:5557
celery -A pms.celery flower --port=5557
```

### Docker Commands

```bash
# Build and start all services
docker-compose up -d --build

# View logs
docker-compose logs -f api
docker-compose logs -f celery_worker

# Execute commands in container
docker-compose exec api python manage.py shell
docker-compose exec api pytest

# Restart specific service
docker-compose restart redis

# Stop all services
docker-compose down

# Stop and remove volumes (⚠️ deletes data)
docker-compose down -v
```

---

## 📚 API Documentation

### Interactive Documentation
- **Swagger UI**: `http://localhost:8000/api/docs/`
- **ReDoc**: `http://localhost:8000/api/redoc/`
- **OpenAPI Schema**: `http://localhost:8000/api/schema/`

### Authentication Flow (JWT)

```bash
# 1. Register new user
POST /api/v1/auth/users/
{
  "email": "user@example.com",
  "password": "SecurePass123!",
  "first_name": "John",
  "last_name": "Doe"
}

# 2. Obtain JWT tokens
POST /api/v1/auth/jwt/create/
{
  "email": "user@example.com",
  "password": "SecurePass123!"
}
# Response:
{
  "access": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "refresh": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
}

# 3. Use access token in requests
GET /api/v1/properties/
Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...

# 4. Refresh expired token
POST /api/v1/auth/jwt/refresh/
{
  "refresh": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
}
```

### Key API Endpoints

| Resource | Method | Endpoint | Description |
|----------|--------|----------|-------------|
| Auth | POST | `/api/v1/auth/users/` | Register new user |
| Auth | POST | `/api/v1/auth/jwt/create/` | Obtain JWT tokens |
| Auth | POST | `/api/v1/auth/jwt/refresh/` | Refresh access token |
| Properties | GET | `/api/v1/properties/` | List properties (role-filtered) |
| Properties | POST | `/api/v1/properties/` | Create property (Manager/Superuser) |
| Properties | GET | `/api/v1/properties/{pk}/` | Retrieve property details |
| Units | GET | `/api/v1/properties/units/` | List units (role-filtered) |
| Leases | GET | `/api/v1/rentals/leases/` | List leases (role-filtered) |
| Leases | POST | `/api/v1/rentals/leases/{pk}/terminate/` | Terminate active lease |
| Maintenance | POST | `/api/v1/rentals/maintenance-requests/` | Submit maintenance request |
| Maintenance | PATCH | `/api/v1/rentals/maintenance-requests/{pk}/assign/` | Assign to vendor |
| Payments | POST | `/api/v1/rentals/payments/` | Record payment |
| Broadcast | POST | `/api/v1/notifications/broadcasts/` | Send templated message |

> 📋 Full endpoint documentation available via Swagger UI at `/api/docs/`.

---

## 🧪 Testing & Quality Assurance

### Running Tests

```bash
# Run all tests with coverage
pytest --cov=apps --cov-report=term-missing --cov-report=html

# View HTML coverage report
open htmlcov/index.html  # macOS
xdg-open htmlcov/index.html  # Linux

# Run specific test module
pytest apps/properties/tests/test_services.py -v

# Run with factory debugging
pytest --factory-debug

# Run failed tests only (requires pytest-xdist)
pytest --last-failed
```

### Test Structure

```
apps/properties/tests/
├── conftest.py           # Shared fixtures (property_factory, user_factory)
├── factories.py          # Factory Boy model factories
├── test_models.py        # Model validation, methods, signals
├── test_serializers.py   # Input/output validation
├── test_repositories.py  # Data access layer tests
├── test_services.py      # Business logic tests
├── test_permissions.py   # RBAC enforcement tests
└── test_views.py         # API endpoint integration tests
```

### Quality Gates

```bash
# Pre-commit checks (configure via .pre-commit-config.yaml)
black --check .
flake8 apps/
isort --check-only .
pytest --cov=apps --cov-fail-under=85  # Fail if coverage < 85%

# Type checking (optional, add mypy to requirements-dev.txt)
mypy apps/
```

### Sample Test (pytest + factory_boy)

```python
# apps/properties/tests/test_services.py
import pytest
from apps.properties.services import PropertyService
from apps.properties.factories import PropertyFactory, OwnerFactory

@pytest.mark.django_db
class TestPropertyService:
    def test_create_property_success(self):
        owner = OwnerFactory()
        service = PropertyService()
        
        data = {
            "name_en": "Sunset Apartments",
            "name_fr": "Appartements Coucher de Soleil",
            "address": "123 Main St",
            "starting_amount": "1500.00"
        }
        
        property = service.create(owner=owner, **data)
        
        assert property.pk is not None
        assert property.name_en == "Sunset Apartments"
        assert property.owners.filter(pkid=owner.pkid).exists()
```

---

## 🐳 Docker & Deployment

### Production Deployment Checklist

1. **Environment Hardening**
   ```ini
   # app/.env (production)
   DEBUG=False
   SECRET_KEY=change-me-in-production-$(openssl rand -base64 32)
   ALLOWED_HOSTS=your-domain.com,www.your-domain.com
   SECURE_SSL_REDIRECT=True
   SESSION_COOKIE_SECURE=True
   CSRF_COOKIE_SECURE=True
   ```

2. **Database Backup Strategy**
   ```bash
   # Daily PostgreSQL backup (cron job)
   0 2 * * * docker exec pms-postgres-db pg_dump -U $DB_USER pms_db | gzip > /backups/pms_$(date +\%Y\%m\%d).sql.gz
   ```

3. **Static/Media File Handling**
   - Use Cloudflare R2 or S3 for media files (`DEFAULT_FILE_STORAGE`)
   - Serve static files via Nginx or CDN
   - Configure `collectstatic` in deployment pipeline

4. **Health Checks**
   ```python
   # apps/core/views.py
   from django.http import JsonResponse
   from django.db import connection
   
   def health_check(request):
       try:
           connection.ensure_connection()
           db_status = "ok"
       except Exception:
           db_status = "fail"
       
       return JsonResponse({
           "status": "ok" if db_status == "ok" else "degraded",
           "database": db_status,
           "version": "1.0.0"
       }, status=200 if db_status == "ok" else 503)
   ```

### Deployment Commands

```bash
# Build production images
docker-compose -f docker-compose.yml build --no-cache

# Deploy with zero-downtime (basic strategy)
docker-compose pull
docker-compose up -d --no-deps --build api nginx
docker-compose exec api python manage.py migrate --noinput
docker-compose exec api python manage.py collectstatic --noinput

# Rollback (if needed)
docker-compose up -d --no-deps api:previous-tag
```

### Monitoring & Observability

- **Application Logs**: `/app/logs/pms.log` (structured JSON via `logger_formatter.py`)
- **Celery Monitoring**: Flower dashboard at `http://localhost:5557` (if enabled)
- **Database Metrics**: PostgreSQL `pg_stat_statements`, slow query log
- **API Metrics**: Integrate with Prometheus via `django-prometheus` (optional)

---

## ⚡ Background Tasks (Celery)

### Task Registration

```python
# apps/notifications/tasks.py
from celery import shared_task
from .utils import render_template, get_email_backend

@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def send_broadcast_email(self, broadcast_id: str, recipient_emails: list[str]):
    try:
        # Fetch broadcast config
        # Render template with context
        # Send via configured backend (SMTP/Twilio/etc.)
        # Log delivery status
        ...
    except Exception as exc:
        raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))
```

### Periodic Tasks (django-celery-beat)

Configure via Django Admin → `Periodic Tasks`:

| Task | Schedule | Purpose |
|------|----------|---------|
| `cleanup_expired_tokens` | Daily 03:00 | Remove stale JWT refresh tokens |
| `send_lease_reminders` | Daily 09:00 | Notify tenants of upcoming rent |
| `generate_monthly_reports` | Monthly 1st 02:00 | Aggregate financial summaries |
| `sync_translation_files` | Weekly Sunday 04:00 | Pull `.po` updates from Rosetta |

### Task Monitoring

```bash
# View active tasks
docker-compose exec api celery -A pms.celery inspect active

# View registered tasks
docker-compose exec api celery -A pms.celery inspect registered

# Purge all queued tasks (⚠️ destructive)
docker-compose exec api celery -A pms.celery purge
```

---

## 🪵 Logging & Monitoring

### Logging Configuration (`apps/core/logging.py`)

```python
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "json": {
            "()": "apps.core.logger_formatter.CustomJsonFormatter",
            "format": "%(asctime)s %(name)s %(levelname)s %(message)s"
        }
    },
    "handlers": {
        "file": {
            "class": "logging.handlers.RotatingFileHandler",
            "filename": "/app/logs/pms.log",
            "maxBytes": 10485760,  # 10MB
            "backupCount": 5,
            "formatter": "json"
        },
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "json"
        }
    },
    "root": {
        "handlers": ["file", "console"],
        "level": "INFO"
    }
}
```

### Structured Log Example

```json
{
  "asctime": "2026-04-20 14:23:45,123",
  "name": "apps.rentals.services",
  "levelname": "INFO",
  "message": "Lease created",
  "lease_id": "a1b2c3d4-e5f6-7890",
  "user_id": "usr_98765",
  "property_id": "prop_12345",
  "request_id": "req_abc123"
}
```

### Log Analysis

```bash
# Tail production logs
docker-compose logs -f api | grep "ERROR\|CRITICAL"

# Search for specific lease operations
docker-compose exec api grep "lease_id=a1b2c3d4" /app/logs/pms.log

# Export logs for external analysis (ELK, Datadog, etc.)
docker-compose exec api tail -n 10000 /app/logs/pms.log | jq '.' > logs_export.json
```

---

## 🔒 Security Considerations

### Implemented Protections
- ✅ JWT authentication with short-lived access tokens + refresh rotation
- ✅ Role-based query filtering at repository layer (defense in depth)
- ✅ Input validation via DRF serializers + model constraints
- ✅ SQL injection protection via Django ORM parameterization
- ✅ XSS protection via Django template auto-escaping
- ✅ CSRF protection for session-based endpoints
- ✅ Password hashing via Django's PBKDF2 (configurable to Argon2)
- ✅ Rate limiting ready (integrate `django-ratelimit` if needed)

### Recommended Hardening (Production)
1. **HTTPS Enforcement**
   ```python
   # settings/prod.py
   SECURE_SSL_REDIRECT = True
   SECURE_HSTS_SECONDS = 3600
   SECURE_HSTS_INCLUDE_SUBDOMAINS = True
   SECURE_HSTS_PRELOAD = True
   ```

2. **Security Headers (Nginx)**
   ```nginx
   # docker/local/nginx/default.conf
   add_header X-Frame-Options "DENY" always;
   add_header X-Content-Type-Options "nosniff" always;
   add_header X-XSS-Protection "1; mode=block" always;
   add_header Referrer-Policy "strict-origin-when-cross-origin" always;
   ```

3. **Secrets Management**
   - Never store secrets in code or `.env` committed to VCS
   - Use AWS Secrets Manager / HashiCorp Vault in production
   - Rotate `SECRET_KEY` and database credentials quarterly

4. **Dependency Scanning**
   ```bash
   # Install safety for vulnerability checks
   pip install safety
   
   # Run audit
   safety check -r requirements.txt
   ```

5. **Audit Logging**
   - Log all authentication attempts (success/failure)
   - Log sensitive operations (lease termination, payment processing)
   - Retain logs per compliance requirements (GDPR, etc.)

---

## 🌍 Internationalization (i18n)

### Model Translation Setup

```python
# apps/properties/models.py
from django.utils.translation import gettext_lazy as _
from modeltranslation.translator import register, TranslationOptions

class Property(models.Model):
    name = models.CharField(_("Name"), max_length=255)  # Base field
    description = models.TextField(_("Description"), blank=True)
    # modeltranslation auto-creates: name_en, name_fr, description_en, description_fr

@register(Property)
class PropertyTranslationOptions(TranslationOptions):
    fields = ('name', 'description', 'address')
```

### Usage in Code

```python
# Automatic language resolution from request
from django.utils.translation import activate, get_language

# In view/service
def get_property_name(property: Property, lang: str = None):
    if lang:
        activate(lang)  # Temporarily switch language
    return property.name  # Returns name_en or name_fr based on active language
```

### Translation Management

```bash
# Extract translatable strings
python app/manage.py makemessages -l fr  # Create/update French .po files

# Compile translations
python app/manage.py compilemessages

# Edit translations via web UI (if django-rosetta enabled)
# Access at /admin/rosetta/ (superuser only)
```

### Frontend Integration

```javascript
// Example: Request with language preference
fetch('/api/v1/properties/', {
  headers: {
    'Accept-Language': 'fr-FR',  // Django middleware activates fr
    'Authorization': `Bearer ${token}`
  }
})
```

---

## 📎 File Storage

### Supported Backends

| Environment | Storage Backend | Configuration |
|-------------|----------------|---------------|
| Development | Local filesystem | `MEDIA_ROOT=/app/mediafiles` |
| Staging | Cloudflare R2 | `helpers.cloudflare.storages.CloudflareR2Storage` |
| Production | Cloudflare R2 + CDN | R2 + Cloudflare Pages/Workers |

### Cloudflare R2 Setup

```ini
# app/.env (production)
DEFAULT_FILE_STORAGE=helpers.cloudflare.storages.CloudflareR2Storage
AWS_ACCESS_KEY_ID=your-r2-access-key
AWS_SECRET_ACCESS_KEY=your-r2-secret-key
AWS_STORAGE_BUCKET_NAME=pms-media-prod
AWS_S3_ENDPOINT_URL=https://<account-id>.r2.cloudflarestorage.com
AWS_S3_CUSTOM_DOMAIN=media.your-domain.com
AWS_QUERYSTRING_AUTH=False  # Public read access via CDN
```

### File Upload Endpoint Example

```bash
# Upload property image (authenticated)
POST /api/v1/properties/{property_id}/images/
Authorization: Bearer <token>
Content-Type: multipart/form-data

{
  "image": <file>,
  "caption_en": "Front exterior",
  "caption_fr": "Façade avant",
  "is_primary": true
}
```

### Storage Utilities

```python
# apps/helpers/storages/mixins.py
class SecureStorageMixin:
    """Validate file type/size before upload"""
    allowed_extensions = {'.jpg', '.jpeg', '.png', '.pdf'}
    max_size_mb = 10
    
    def validate_file(self, file):
        ext = Path(file.name).suffix.lower()
        if ext not in self.allowed_extensions:
            raise ValidationError(f"Unsupported file type: {ext}")
        if file.size > self.max_size_mb * 1024 * 1024:
            raise ValidationError(f"File exceeds {self.max_size_mb}MB limit")
```

---

## 🛠️ Troubleshooting

### Common Issues

#### 1. Database Connection Failed
```bash
# Check PostgreSQL container status
docker-compose ps postgres-db

# Verify connection string in .env
docker-compose exec api python -c "import os, dj_database_url; print(dj_database_url.parse(os.getenv('DATABASE_URL')))"

# Test direct connection
docker-compose exec postgres-db psql -U $DB_USER -d $DB_NAME -c "\dt"
```

#### 2. Celery Worker Not Processing Tasks
```bash
# Check worker logs
docker-compose logs celery_worker

# Verify Redis connectivity
docker-compose exec redis redis-cli ping  # Should return PONG

# Inspect queue
docker-compose exec api celery -A pms.celery inspect stats
```

#### 3. JWT Authentication Errors
```bash
# Verify token structure
echo <token> | cut -d'.' -f2 | base64 -d  # Decode payload

# Check token expiration
python -c "import jwt, datetime; print(jwt.decode('<token>', options={'verify_signature': False}))"

# Ensure SIMPLE_JWT settings match frontend expectations
```

#### 4. Static Files Not Loading (Production)
```bash
# Verify collectstatic ran
docker-compose exec api ls -la /app/staticfiles/

# Check Nginx config mounts static volume
docker-compose exec nginx nginx -t

# Ensure MEDIA_URL/STATIC_URL match frontend requests
```

#### 5. Translation Fields Not Appearing
```bash
# Verify modeltranslation is in INSTALLED_APPS
docker-compose exec api python -c "from django.conf import settings; print('modeltranslation' in settings.INSTALLED_APPS)"

# Re-run migrations after adding TranslationOptions
docker-compose exec api python manage.py makemigrations
docker-compose exec api python manage.py migrate

# Check compiled .mo files exist
docker-compose exec api ls app/locale/fr/LC_MESSAGES/django.mo
```

### Debug Mode Utilities

```python
# Enable Django Debug Toolbar (dev only)
# settings/dev.py
if DEBUG:
    INSTALLED_APPS += ['debug_toolbar']
    MIDDLEWARE = ['debug_toolbar.middleware.DebugToolbarMiddleware'] + MIDDLEWARE
    INTERNAL_IPS = ['127.0.0.1', '0.0.0.0']
    DEBUG_TOOLBAR_CONFIG = {'SHOW_TOOLBAR_CALLBACK': lambda request: True}
```

```bash
# Access toolbar at http://localhost:8000/ (look for ▶️ icon)
# Provides SQL queries, cache stats, template context, etc.
```

---

## 👥 Contributing (Internal Team)

### Development Workflow

1. **Branch Strategy**
   ```
   main          → Production releases (protected)
   develop       → Integration branch for features
   feature/*     → New functionality (e.g., feature/lease-renewal)
   bugfix/*      → Critical fixes (e.g., bugfix/payment-calculation)
   release/*     → Release preparation (e.g., release/v1.2.0)
   ```

2. **Pull Request Checklist**
   - [ ] Code formatted with `black` and imports sorted with `isort`
   - [ ] Linting passes: `flake8 apps/`
   - [ ] Tests added/updated with ≥85% coverage for new logic
   - [ ] Migrations created and tested (`makemigrations` + `migrate`)
   - [ ] API docs updated (Swagger auto-generated, but verify examples)
   - [ ] `.env.example` updated if new env vars added
   - [ ] Changelog entry in `notes.md`

3. **Code Review Guidelines**
   - Prefer repository/service layer changes over view logic
   - Use `@transaction.atomic` for multi-model writes
   - Add type hints to new functions (`-> UserType`)
   - Log business-critical operations at `INFO` level
   - Avoid N+1 queries: use `select_related`/`prefetch_related`

### Local Development Setup (Team Members)

```bash
# 1. Fork and clone internal repo
git clone git@internal-git-server:pms/backend.git
cd backend

# 2. Setup pre-commit hooks (enforces quality gates)
pip install pre-commit
pre-commit install

# 3. Copy team-shared .env template
cp app/.env.team-example app/.env
# Add personal secrets (DB password, etc.)

# 4. Start dev environment
docker-compose up -d postgres-db redis
docker-compose run --rm api python manage.py migrate
docker-compose run --rm api python manage.py loaddata fixtures/dev_data.json  # Optional seed data

# 5. Run tests before committing
pytest --cov=apps --cov-fail-under=85
```****

### Internal Resources
- 📁 Design Docs: `docs/architecture/`
- 🗄️ Database Schema: `docs/db/schema.pdf`
- 🔐 Secrets Management: Internal wiki → "PMS Credential Vault"
- 🚨 Incident Response: `docs/runbooks/incident-response.md`

---

## 📜 License

> **PROPRIETARY AND CONFIDENTIAL**  
>   
> This software and associated documentation files (the "Software") are the exclusive property of [Your Company Name].  
>   
> **You may not**:  
> - Copy, modify, merge, publish, distribute, sublicense, or sell copies of the Software  
> - Reverse engineer, decompile, or disassemble the Software  
> - Use the Software for any purpose other than authorized internal business operations  
>   
> **Authorized Use**:  
> Licensed personnel may use the Software solely for developing, maintaining, and operating the Property Management System under the terms of their employment agreement and company policies.  
>   
> **No Warranty**:  
> The Software is provided "AS IS", without warranty of any kind, express or implied.  
>   
> © 2026 [Your Company Name]. All Rights Reserved.  
> Last Updated: April 2026  

*For license exceptions or enterprise licensing inquiries, contact: legal@yourcompany.com*

---

## 📞 Support & Contact

| Role | Contact | Purpose |
|------|---------|---------|
| Backend Team Lead | backend-lead@yourcompany.com | Architecture decisions, code reviews |
| DevOps Engineer | devops@yourcompany.com | Deployment, infrastructure, monitoring |
| Security Officer | security@yourcompany.com | Vulnerability reports, compliance |
| Product Owner | product@yourcompany.com | Feature requirements, prioritization |

### Emergency Contacts
- **Production Outage**: #pms-incidents (Slack) or +237-670-181-442
- **Security Incident**: miclemabasie@bliztondynamics.com (PGP encrypted)


*Document Version: 1.2.0 • Last Reviewed: April 2026*