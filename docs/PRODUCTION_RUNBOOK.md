# Production Runbook - Bali Scooter Rental

This guide provides instructions for deploying, managing, and troubleshooting the Bali Scooter Rental backend.

## 1. Local Development Setup

### Prerequisites
- Python 3.12+
- Redis (running locally or via Docker)
- SQLite (default) or PostgreSQL

### Steps
1. **Clone and Install**:
   ```bash
   git clone <repo_url>
   cd bali_rent
   python -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```
2. **Environment**:
   ```bash
   cp .env.example .env
   # Edit .env with your local settings
   ```
3. **Database**:
   ```bash
   python manage.py migrate
   python manage.py createsuperuser
   ```
4. **Run**:
   - Web: `python manage.py runserver`
   - Worker: `celery -A bali_rent worker -l info`

---

## 2. Docker Staging Deployment
The project includes a Dockerized setup for staging environments.

### Services
- **web**: Django application (Gunicorn).
- **db**: PostgreSQL 15.
- **redis**: Redis 7.
- **celery_worker**: Task processor.
- **celery_beat**: Task scheduler.
- **nginx**: Reverse proxy.

### Commands
```bash
# Build and start
docker compose -f docker-compose.staging.yml up -d --build

# Create superuser
docker compose -f docker-compose.staging.yml exec web python manage.py createsuperuser

# View logs
docker compose -f docker-compose.staging.yml logs -f web
```

---

## 3. Production Deployment
*Note: Ensure `DJANGO_DEBUG=False` and a strong `DJANGO_SECRET_KEY` are set.*

### Infrastructure Requirements
- **PostgreSQL**: Managed database (AWS RDS, Heroku Postgres, etc.) is recommended.
- **Redis**: For Celery broker and Caching.
- **S3 Storage**: Recommended for user uploads (avatars, documents) and static files.

### Deployment Steps
1. Set up environment variables (see below).
2. Install production dependencies.
3. Run `python manage.py collectstatic --noinput`.
4. Run `python manage.py migrate --noinput`.
5. Start processes (Web, Worker, Beat).

---

## 4. Environment Variables Reference

| Variable | Description | Example |
| :--- | :--- | :--- |
| `DJANGO_DEBUG` | Enable/Disable debug mode | `False` |
| `DJANGO_SECRET_KEY` | Django security key | `long-random-string` |
| `DATABASE_URL` | DB Connection string | `postgres://user:pass@host:5432/db` |
| `REDIS_URL` | Redis URL | `redis://localhost:6379/1` |
| `CELERY_BROKER_URL` | Celery Broker | `redis://localhost:6379/0` |
| `STRIPE_SECRET_KEY` | Stripe API Secret | `sk_live_...` |
| `CRYPTO_PAYMENT_API_KEY` | NowPayments API Key | `...` |
| `THROTTLE_LOGIN` | Login rate limit | `10/min` |
| `THROTTLE_REGISTER` | Registration rate limit | `5/min` |
| `THROTTLE_PRICING_CALCULATE` | Price calculation rate limit | `60/min` |
| `THROTTLE_PROMO_VALIDATE` | Promo validation rate limit | `30/min` |
| `THROTTLE_ANALYTICS_EVENTS` | Analytics ingest rate limit | `120/min` |
| `THROTTLE_PAYMENT_CREATE` | Payment create rate limit | `20/min` |

---

## 5. Maintenance & Troubleshooting

### Database Migrations
Always backup the database before running migrations in production.
```bash
python manage.py migrate
```

### Resetting Passwords
If an admin loses access:
```bash
python manage.py changepassword <username>
```

### Checking System Health
- **Logs**: Monitor `web` and `celery_worker` logs for `ERROR` level entries.
- **Audit Logs**: Check the `AuditLog` table in the Django admin for suspicious activity.
- **Webhook Logs**: Check `WebhookProcessingLog` in the `audit` app to see if Stripe or Crypto webhooks are failing. This is the canonical webhook monitoring table.
- **Sensitive Data**: Audit and webhook payloads are recursively redacted for passwords, tokens, secrets, signatures, hashes, and API keys.
- **Document Uploads**: Verification documents are limited to JPG, PNG, and PDF, max 5 MB, and server-side UUID filenames.
- **Celery Jobs**: `expire_unpaid_bookings` and `sync_currency_rates` have retry/backoff/time limits. Alert if retries are exhausted or if unpaid bookings remain pending beyond the configured expiry window.

### Monitoring & Error Tracking (Recommended)
`sentry-sdk` is not currently installed in `requirements.txt`. To enable Sentry:
1. Install `sentry-sdk`: `pip install sentry-sdk`
2. Configure in `settings.py`:
   ```python
   import sentry_sdk
   from sentry_sdk.integrations.django import DjangoIntegration

   sentry_sdk.init(
       dsn=os.environ.get('SENTRY_DSN'),
       integrations=[DjangoIntegration()],
       traces_sample_rate=1.0,
       send_default_pii=True
   )
   ```
3. Set `SENTRY_DSN` in environment variables.

### Common Issues
- **401 Unauthorized**: JWT token expired. Refresh or re-login.
- **403 Forbidden**: User role does not have permission for the action.
- **500 Internal Error**: Check logs. Common causes: DB connection timeout, Redis down, or missing environment variable.
