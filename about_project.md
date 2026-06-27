# 🚀 Fresh Installation & Setup Checklist

Follow this checklist **exactly** to set up a clean instance of the PMS Backend from scratch.  
It covers every essential step – from environment variables to seeding baseline data – so that the system is fully operational for production.

---

## 1. Environment Configuration

### 1.1 Clone the repository
```bash
git clone <your-repo-url>
cd pms-backend
```

### 1.2 Copy the environment template and edit it
```bash
cp app/.env.example app/.env
```

Open `app/.env` and **set at least** these required variables (all others have safe defaults):

| Variable | Purpose | Example Value |
|----------|---------|---------------|
| `SECRET_KEY` | Django secret – generate a long random string | `django-insecure-abc...` |
| `SIGNING_KEY` | JWT signing key – different from SECRET_KEY | `abc123...` |
| `DEBUG` | Set to `False` in production | `False` |
| `ALLOWED_HOSTS` | Your domain or IPs | `example.com,api.example.com` |
| `POSTGRES_DB` | Database name | `pms_prod` |
| `POSTGRES_USER` | Database user | `pms_user` |
| `POSTGRES_PASSWORD` | Database password | `strong_password` |
| `PG_HOST` | Database host | `postgres-db` (Docker) or `localhost` |
| `SMOBIL_PAY_API_URL` | SmobilPay API URL (live or staging) | `https://api.smobilpay.com/v3` |
| `SMOBIL_PAY_API_KEY` | Public token | *(from SmobilPay dashboard)* |
| `SMOBIL_PAY_API_SECRET` | Secret key | *(from SmobilPay dashboard)* |
| `SMOBIL_PAY_WEBHOOK_SECRET` | Webhook secret (for HMAC) | *(from SmobilPay dashboard)* |
| `SMOBILPAY_MTN_CASHIN_ITEM_ID` | PayItemId for MTN cashin | *(from SmobilPay)* |
| `SMOBILPAY_MTN_CASHOUT_ITEM_ID` | PayItemId for MTN cashout | *(from SmobilPay)* |
| `SMOBILPAY_ORANGE_CASHIN_ITEM_ID` | PayItemId for Orange cashin | *(from SmobilPay)* |
| `SMOBILPAY_ORANGE_CASHOUT_ITEM_ID` | PayItemId for Orange cashout | *(from SmobilPay)* |
| `EMAIL_HOST` | SMTP server (if using email) | `smtp.gmail.com` |
| `EMAIL_HOST_USER` | SMTP username | `noreply@yourdomain.com` |
| `EMAIL_HOST_PASSWORD` | SMTP password | *(app-specific password)* |

---

## 2. Build & Start Services (Docker)

We assume you use Docker Compose for production. Run:

```bash
docker-compose up -d --build
```

This starts:
- PostgreSQL
- Redis
- Django API (Gunicorn)
- Celery worker
- Nginx (reverse proxy)

---

## 3. Database Setup

### 3.1 Run migrations
```bash
docker-compose exec api python manage.py migrate
```

### 3.2 Create superuser (admin)
```bash
docker-compose exec api python manage.py createsuperuser
```
Follow prompts – this user will have full access to the admin panel and API.

---

## 4. Seed Baseline Data (Mandatory)

The system requires certain **base records** to function correctly:

- **Subscription Feature Groups** (Free, Basic, Standard, Premium)
- **Subscription Plans** linked to those feature groups
- **Default Payment Plans** (monthly and yearly) for units
- **Platform Settings** (fee rates) – this is created automatically if missing, but you can verify.

### 4.1 Seed subscription feature groups and plans

Run the dedicated management command:

```bash
docker-compose exec api python manage.py setup_subscription_data
```

This creates the four feature groups and four subscription plans.  
Verify they exist in the admin panel at `/admin/subscriptions/`.

### 4.2 Create default Payment Plans (optional but recommended)

If you want to have reusable payment plans ready for units, create them manually via the API or admin panel.  
The system does not automatically seed PaymentPlans.  
Example monthly and yearly plans:

- **Monthly Flexible**: mode=`monthly`, allowed terms `[1,3,6]`, max_months=12, custom_amount=`true`, amount_step=10.
- **Yearly 60/40**: mode=`yearly`, installments with 60% and 40%, show_full_payment_option=`true`.

You can create them via the admin UI (`/admin/payments/paymentplan/`) or via API using `POST /api/v1/payments/payment-plans/` with a superuser token.

### 4.3 Ensure PlatformSettings singleton exists

Run this in Django shell to verify (or it auto-creates on first use):

```bash
docker-compose exec api python manage.py shell
```

```python
from apps.core.models import PlatformSettings
settings = PlatformSettings.get_settings()
print(settings.platform_fee_percent, settings.platform_fee_cap)
```

If it returns values (default 1.0% and 1000 XAF cap), it's fine.

---

## 5. Email & Notification Configuration

### 5.1 Set up email configuration (optional if you use SMTP)

If you want to use the database-backed email configuration (instead of settings), you can create an `EmailConfiguration` record via admin or command:

```bash
docker-compose exec api python manage.py setup_email_config
```

This command reads from environment variables (`EMAIL_HOST`, etc.) and creates an active `EmailConfiguration` row.  
If you rely on environment variables only (and keep `EMAIL_BACKEND='smtp'` in `.env`), you can skip this step.

### 5.2 Verify notification templates are present

The `setup_email_config` command also creates `welcome_email` and `password_reset` templates.  
If you skipped it, you can still create them manually in the admin panel.

---

## 6. Payment Gateway Configuration

### 6.1 Verify SmobilPay environment variables are set (already done in .env)

The system will use the values from `.env` to initialise the gateway.  
No additional setup is required, but you should test the connection:

```bash
docker-compose exec api python manage.py shell
```

```python
from apps.payments.gateway_SDKs.gateway_factory import gateway_factory
from django.conf import settings
gw = gateway_factory.create_gateway('smobilpay', settings.SMOBILPAY_CONFIG)
print(gw.get_health_status())
```

Expected output: `{'healthy': True, ...}` if credentials are correct.

---

## 7. Webhook Endpoint Configuration

The webhook URL must be registered with SmobilPay:

**Public URL:** `https://yourdomain.com/api/v1/payments/webhooks/smobilpay/`

Make sure your server is reachable from the internet and the endpoint is not behind authentication (the webhook view has `permission_classes=[]`).  
SmobilPay will send POST requests to this URL with the `X-SmobilPay-Signature` header.

---

## 8. Celery Beat (Periodic Tasks) – Ensure Running

Celery beat must be running to execute scheduled tasks:
- Subscription invoice generation (1st of each month)
- Subscription expiry (daily)
- Disbursement processing (every Monday)

In Docker Compose, the `celery_worker` service is configured with `command: /start-celeryworker` but **beat is not started**.  
We need to explicitly start beat (either as a separate container or inside the worker).  
Recommended: add a `celery_beat` service in `docker-compose.yml`:

```yaml
celery_beat:
  build:
    context: .
    dockerfile: ./docker/local/django/Dockerfile
  command: /start-celerybeat
  volumes:
    - .:/app
  env_file:
    - app/.env
  depends_on:
    - redis
    - postgres-db
  networks:
    - pms-network
```

And create `/start-celerybeat` script (copy from the worker).  
Or simply run beat manually for testing:

```bash
docker-compose exec api celery -A pms.celery beat -l info
```

Ensure `CELERY_BEAT_SCHEDULE` is defined in `settings/base.py` (it is, for invoice generation, expiry, and disbursement).

---

## 9. Final Verification Tests

### 9.1 Check admin panel
Visit `https://yourdomain.com/admin/` and log in with the superuser. Verify:
- Users, Owners, Tenants, Properties can be created.
- Subscription plans are visible.
- Payment plans exist.

### 9.2 Test authentication
```bash
curl -X POST https://yourdomain.com/api/v1/auth/jwt/create/ \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@example.com","password":"..."}'
```
You should receive access and refresh tokens.

### 9.3 Test property creation (with owner)
Create an owner profile for the admin user (if not already). Then create a property via API to ensure permissions work.

### 9.4 Test payment flow end‑to‑end
- Create a tenant (via API or admin).
- Create a unit with a payment plan.
- Create a rental agreement.
- Initiate a payment (use a test phone number) – the system will call SmobilPay sandbox if you use staging credentials.
- Verify the webhook endpoint receives the callback (use ngrok if local).

---

## 10. Production Readiness Checklist

- [ ] HTTPS is enforced (use Nginx with SSL certificate).
- [ ] `DEBUG=False` in `.env`.
- [ ] `SECRET_KEY` and `SIGNING_KEY` are strong and secret.
- [ ] Database backups scheduled (e.g., daily pg_dump).
- [ ] Logs are rotated and monitored.
- [ ] Celery worker and beat are running as daemons.
- [ ] Webhook URL is registered with SmobilPay.
- [ ] Email configuration is active (or SMTP set).
- [ ] Payment gateway credentials are correct and tested.

---

## 11. Management Commands Reference (Quick Lookup)

| Command | Purpose |
|---------|---------|
| `python manage.py migrate` | Apply database schema migrations |
| `python manage.py createsuperuser` | Create admin user |
| `python manage.py setup_subscription_data` | Seed feature groups & subscription plans |
| `python manage.py setup_email_config` | Create default email templates + active SMTP config |
| `python manage.py populate_test_data_full` | *(Development only)* – generate fake test data |

---

## 12. Troubleshooting Common Setup Issues

- **Migrations fail** – Ensure PostgreSQL is running and credentials in `.env` are correct.
- **Celery tasks not executing** – Verify Redis is running; check that beat is scheduled.
- **Webhook returns 400** – Check the signature verification fix (use raw body, not re-encoded JSON).
- **Payments fail** – Ensure SmobilPay payItemIds are correctly set for both cashin and cashout operations.

