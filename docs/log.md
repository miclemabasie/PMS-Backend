# 📝 `notes.md` - Project Changelog & Documentation Log

> **Purpose**: This file tracks all significant changes, decisions, and documentation updates for the Property Management System. Use it for release notes, migration guides, and team alignment.

---

## 🗓️ Changelog Format Guide

```markdown
## [Version] - YYYY-MM-DD

### 🚀 Added

- New features, endpoints, or capabilities

### 🔧 Changed

- Modifications to existing behavior (non-breaking)

### ⚠️ Deprecated

- Features marked for future removal

### 🗑️ Removed

- Features removed in this release

### 🐛 Fixed

- Bug fixes and corrections

### 🔒 Security

- Security patches or hardening measures

### 📚 Documentation

- README, API docs, or internal guide updates

### 🔁 Migration Notes

- Steps required when upgrading (if any)
```

---

## 📦 Release History

### [v1.2.0] - 2026-04-20 _(Current Development)_

#### 🚀 Added

- **Notifications Module** (`apps/notifications/`)
  - `Notification` model with status tracking (`pending`, `sent`, `failed`, `read`)
  - `NotificationTemplate` system for reusable email/SMS templates
  - `UserNotificationSetting` for per-user channel preferences (email/SMS/push)
  - Async task `send_notification_task` via Celery for non-blocking delivery
  - Backend abstraction: `DjangoSMTPBackend`, `TwilioSMSBackend`, `ConsoleSMSBackend`
- **Maintenance Workflow Enhancements**
  - `MaintenanceNote` model for audit trail on request updates
  - Vendor assignment with `approved_by` FK and approval timestamps
  - Cost tracking: `estimated_cost` vs `actual_cost` with currency field
  - Status transitions: `submitted` → `approved` → `in_progress` → `completed`/`cancelled`

- **Logging Infrastructure**
  - `CustomLogger` class in `apps/core/logging.py` for structured JSON logs
  - Context injection via `_extra()` method (request_id, user_id, module)
  - Rotating file handlers for `pms.log` and `django.log`
  - Coverage-aware logging: skipped lines marked in `htmlcov/` reports

- **Internationalization (i18n) Expansion**
  - Bilingual fields for `Property`, `Unit`, `MaintenanceRequest` (`*_en`/`*_fr`)
  - `django-modeltranslation` auto-registration for new models
  - Rosetta integration for web-based `.po` file editing

#### 🔧 Changed

- **Repository Pattern Refactor**
  - Moved generic `BaseRepository[T]` to `apps/core/base_repository.py`
  - All domain repos now inherit: `PropertyRepository(DjangoRepository[Property])`
  - Added `filter_for_user(user)` method to enforce RBAC at data layer

- **Service Layer Standardization**
  - `BaseService[T]` now requires explicit repository injection
  - Transaction boundaries enforced via `@transaction.atomic` on write operations
  - Added `get_or_create_cached()` helper for frequently accessed entities

- **API Response Consistency**
  - All ViewSets now use `MaintenanceRequestSerializer(context={'request': request})`
  - Standardized error format: `{"error": {"code": "...", "message": "...", "details": {...}}}`
  - Pagination defaults: `page_size=20`, `max_page_size=100`

#### 🐛 Fixed

- JWT refresh token rotation edge case when `REFRESH_TOKEN_LIFETIME` expires mid-request
- `FieldTracker` import error in `MaintenanceRequest` model (now using `model_utils`)
- Coverage report false negatives on `__str__` methods (added `# pragma: no cover` where appropriate)
- Celery task retry logic: exponential backoff now respects `max_retries`

#### 🔒 Security

- Added `MinValueValidator(1)` to all monetary fields to prevent negative values
- File upload validation: restricted extensions + 10MB limit in `SecureStorageMixin`
- Rate limiting ready: added `django-ratelimit` to `requirements.txt` (disabled by default)

#### 📚 Documentation

- ✅ Created comprehensive `README.md` with architecture diagrams, setup guides, and API examples
- ✅ Added this `notes.md` changelog template for future releases
- 🔄 _In Progress_: Swagger examples for maintenance workflow endpoints

#### 🔁 Migration Notes

```bash
# After pulling v1.2.0:
python manage.py migrate  # Applies 0012_notifications, 0013_maintenance_notes
python manage.py compilemessages  # Updates bilingual field translations

# Optional: Backfill notification settings for existing users
python manage.py shell << EOF
from apps.notifications.models import UserNotificationSetting
for user in User.objects.all():
    UserNotificationSetting.objects.get_or_create(user=user)
EOF
```

---

### [v1.1.0] - 2026-03-15

#### 🚀 Added

- **Payments Module** (`apps/payments/`)
  - `Payment` model with support for Rent/Deposit/Fee/Utility types
  - Payout methods: `MTN_MOMO`, `ORANGE_MONEY`, `CASH`, `BANK_TRANSFER`
  - Webhook reconciliation fields: `gateway_txn_id`, `webhook_signature`
- **Property Management Core**
  - `OwnershipRecord` for many-to-many owner<->property relationships
  - `PropertyManager` assignment with role-based access control
  - Image gallery support with `is_primary` flag and captions (EN/FR)

- **Testing Infrastructure**
  - Factory Boy factories for all major models (`PropertyFactory`, `LeaseFactory`, etc.)
  - `conftest.py` with shared fixtures: `api_client`, `auth_token`, `property_with_units`
  - Coverage threshold enforcement: `--cov-fail-under=85` in `pytest.ini`

#### 🔧 Changed

- **Authentication Flow**
  - Switched from session auth to Djoser + SimpleJWT (`/api/v1/auth/jwt/`)
  - Added `refresh` endpoint with token rotation
  - Profile-based role resolution: `OwnerProfile`, `TenantProfile`, `ManagerProfile`

- **Database Schema**
  - All models now inherit `TimeStampedUUIDModel` (UUID pk + created_at/updated_at)
  - Added `is_active` boolean flag to soft-delete capable entities
  - Indexed foreign keys on high-query fields: `property`, `unit`, `tenant`

#### 🐛 Fixed

- Lease termination date validation: prevented end_date < start_date
- Currency field precision: changed `DecimalField` to `max_digits=10, decimal_places=2`
- Celery worker startup race condition: added `depends_on` health checks in `docker-compose.yml`

#### 📚 Documentation

- Added Postman collection: `PMS API.postman_collection.json`
- Documented environment variables in `.env.example`
- Created `makefile` shortcuts: `make test`, `make coverage`, `make lint`

---

### [v1.0.0] - 2026-02-01 🎉 _Initial Production Release_

#### 🚀 Added

- **Core Architecture**
  - Django 5.2 project with modular app structure (`apps/`)
  - Repository/Service pattern implementation
  - PostgreSQL + Redis + Celery stack via Docker Compose
- **User Management** (`apps/users/`)
  - Custom `User` model with email as username
  - Role-based permissions: Superuser, Manager, Owner, Tenant, Vendor
  - Profile models with extended metadata (phone, address, ID documents)

- **Property & Rental Core**
  - `Property`, `Unit`, `Lease` models with status workflows
  - Lease lifecycle: `draft` → `active` → `expired`/`terminated`
  - Basic CRUD APIs with DRF ViewSets + Serializers

- **DevOps Foundation**
  - Multi-stage Docker build (slim Python 3.12)
  - Nginx reverse proxy with static file serving
  - Health check endpoint: `GET /health/`

#### 🔒 Security

- Django security middleware enabled (`SECURE_SSL_REDIRECT`, etc.)
- JWT authentication with short-lived access tokens (60 min)
- Environment variable isolation via `django-environ`

#### 📚 Documentation

- Initial `README.md` with setup instructions
- API schema generation via `drf-spectacular`
- Code coverage reporting with `coverage.py` + `htmlcov/`

---

## 🔄 How to Update This File (Best Practices)

### ✅ Before Merging a PR

1. **Identify the change type**: Feature, bugfix, refactor, security, docs
2. **Determine version impact**:
   - `MAJOR` (x.0.0): Breaking API changes, removed features
   - `MINOR` (1.x.0): New backwards-compatible features
   - `PATCH` (1.1.x): Bug fixes, non-breaking tweaks
3. **Add entry under current `[Unreleased]` section** (see below)

### 📝 Template for New Entries

```markdown
### [Unreleased] - Next Release

#### 🚀 Added

- #123: Added `export_to_csv()` method to `PropertyService` (@yourname)

#### 🐛 Fixed

- #145: Fixed timezone bug in lease expiry calculations (@contributor)

#### 📚 Documentation

- Updated API examples for maintenance request workflow
```

### 🔗 Linking to Code

- Use GitHub-style references: `#123` for issues, `@username` for authors
- For internal repos: `PMS-456` (Jira) or `MR!789` (GitLab)
- Always include **who** and **what** (not just "fixed bug")

### 🧹 Maintenance Tips

1. **Keep `[Unreleased]` at top** - move to versioned section on release day
2. **Group by type** - makes scanning easier for QA/Product teams
3. **Include migration notes** - critical for backend changes
4. **Tag breaking changes** with ⚠️ emoji and bold text
5. **Review quarterly** - archive old versions to `changelogs/v1.0.md`

---

## 📋 Documentation Checklist (Per Feature)

When adding new functionality, verify:

```markdown
- [ ] README.md updated with new setup/config steps
- [ ] API docs (Swagger) reflect new endpoints/params
- [ ] `.env.example` includes new environment variables
- [ ] Migration guide added if DB schema changed
- [ ] `notes.md` changelog entry created
- [ ] Inline code docs (docstrings) added for public methods
- [ ] Postman collection updated (if API changed)
- [ ] Docker config updated (if new service/dependency)
```

---

## 🗂️ Related Documentation Files

| File                                  | Purpose                               | Update Frequency            |
| ------------------------------------- | ------------------------------------- | --------------------------- |
| `README.md`                           | Project overview, setup, usage        | Per release                 |
| `notes.md` _(this file)_              | Changelog, decisions, migration notes | Per PR/merge                |
| `app/.env.example`                    | Environment variable reference        | When new config added       |
| `PMS API.postman_collection.json`     | API testing/exploration               | When endpoints change       |
| `docker-compose.yml`                  | Local development orchestration       | When services change        |
| `pyproject.toml` / `requirements.txt` | Dependency management                 | When packages added/updated |

_Last Updated: 2026-04-20 • Maintained by: Backend Team_  
_Next Review Date: 2026-05-20_
