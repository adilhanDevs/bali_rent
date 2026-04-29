# Production Readiness Report & Deployment Guide

## Production Readiness Audit

| Category | Status | Details |
| :--- | :--- | :--- |
| **Security** | **PARTIAL** | JWT configured with blacklist. Security headers and secure cookies implemented in `settings.py`. Requires `DJANGO_DEBUG=False` and `DJANGO_SECRET_KEY` in production. |
| **Database** | **RISKY** | Currently uses SQLite by default. Configured for `DATABASE_URL` (PostgreSQL) but requires `dj-database-url` and `psycopg2` dependencies. |
| **Transactions/Indexes** | **READY** | Critical commerce paths (Bookings, Payments, Marketing) use `select_for_update` and `transaction.atomic`. Key DB indexes implemented. |
| **Redis/Cache** | **PARTIAL** | Configured in `settings.py` but requires Redis instance and `redis` Python package. |
| **Celery** | **PARTIAL** | Tasks implemented for notifications. Broker/Backend configured in `settings.py`. Requires Celery worker/beat process and Redis. |
| **Payments** | **READY** | Stripe and Crypto providers implemented with signature verification. Idempotency handled via `PaymentWebhookEvent`. |
| **Storage** | **PARTIAL** | Currently uses local storage. Recommended to use `django-storages` with AWS S3 for production. |
| **Monitoring** | **MISSING** | No Sentry integration. Basic logging configured to console (standard for Docker/Heroku). |
| **Docker** | **MISSING** | No `Dockerfile` or `docker-compose.yml` found in repository. |
| **CI/CD** | **MISSING** | No CI/CD pipelines configured. |

---

## Deployment Checklist

1. [ ] **Environment Variables**: Copy `.env.example` to `.env` and fill in secrets.
2. [ ] **Dependencies**: Install production dependencies:
   ```bash
   pip install gunicorn psycopg2-binary dj-database-url celery redis
   ```
3. [ ] **Static Files**: Run `python manage.py collectstatic`.
4. [ ] **Migrations**: Run `python manage.py migrate`.
5. [ ] **Process Management**:
   - Web: `gunicorn bali_rent.wsgi:application`
   - Worker: `celery -A bali_rent worker -l info`
   - Beat: `celery -A bali_rent beat -l info`
6. [ ] **SSL**: Ensure SSL certificate is installed and `SECURE_SSL_REDIRECT=True`.

---

## Required Environment Variables

| Variable | Description | Default (Dev) |
| :--- | :--- | :--- |
| `DJANGO_SECRET_KEY` | Secret key for encryption/signing | `django-insecure...` |
| `DJANGO_DEBUG` | Enable/Disable debug mode | `True` |
| `DJANGO_ALLOWED_HOSTS` | Comma-separated list of allowed domains | `*` |
| `DATABASE_URL` | PostgreSQL connection string | `sqlite:///...` |
| `REDIS_URL` | Redis URL for caching | `redis://localhost:6379/1` |
| `CELERY_BROKER_URL` | Redis URL for Celery broker | `redis://localhost:6379/0` |
| `STRIPE_SECRET_KEY` | Stripe API Secret | `None` |
| `STRIPE_WEBHOOK_SECRET` | Stripe Webhook Secret | `None` |

---

## Runbooks

### Webhook Failures
If webhooks are failing (seen in `WebhookProcessingLog`), verify the `WEBHOOK_SECRET` in environment variables. Use `audit` logs to identify the specific error message captured during processing.

### Background Jobs
If notifications are not being sent, check the Celery worker logs. Ensure the Redis broker is reachable.
Scheduled jobs (if implemented in Celery Beat) will be visible in the `django-celery-beat` admin if installed.
