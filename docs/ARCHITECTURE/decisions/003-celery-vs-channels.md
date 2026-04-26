# ADR-003: Celery for Background Task Execution

| Metadata | Value                                                        |
| -------- | ------------------------------------------------------------ |
| Status   | `accepted`                                                   |
| Date     | 2026-02-15                                                   |
| Deciders | Backend Team                                                 |
| Related  | `docker/local/django/celery/`, `apps/notifications/tasks.py` |

## Context

Django handles requests synchronously. Email delivery, broadcast campaigns, and report generation block the request/response cycle, causing timeouts under load.

## Decision

Adopt **Celery** with **Redis** as broker/backend. Use `django-celery-beat` for periodic tasks and `flower` for monitoring.

## Consequences

✅ Non-blocking API responses  
✅ Retry logic with exponential backoff built-in  
✅ Task visibility via Flower dashboard  
⚠️ Additional infrastructure (Redis, worker containers)  
⚠️ Requires task idempotency design  
⚠️ Debugging async flows is harder than sync

## Validation

- All email/notification sends use `@shared_task`
- Worker containers in `docker-compose.yml`
- Beat schedule defined in Django admin
- Task failures logged with structured JSON formatter

## Alternatives Considered

- `django-q` → simpler, but less mature ecosystem
- `Channels` → better for WebSockets, not batch jobs
- `threading/multiprocessing` → not durable, crashes lose tasks

## References

- `app/pms/celery.py` → Celery app config
- `docker-compose.yml` → `celery_worker` service
- `apps/notifications/tasks.py` → task definitions
- `apps/core/logging.py` → task execution logging
