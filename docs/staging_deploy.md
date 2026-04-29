# Staging Deployment Guide

This document outlines the staging deployment architecture and instructions for the Bali Rent project.

## Architecture Summary
The staging environment utilizes Docker Compose to orchestrate the following services:
*   **db**: PostgreSQL 15 database.
*   **redis**: Redis 7 for caching and Celery message brokering.
*   **web**: Django application served by Gunicorn (runs migrations and collects static files on startup via `entrypoint.sh`).
*   **celery_worker**: Background task processor.
*   **celery_beat**: Background task scheduler.
*   **nginx**: Reverse proxy serving static/media files and forwarding requests to the web service.

Volumes are configured to persist database data (`postgres_data`), user uploads (`media_volume`), and static assets (`static_volume`).

## Deployment Commands

### 1. Environment Setup
Copy the staging environment template and modify any necessary secrets:
```bash
cp .env.staging .env.staging.local
# Make sure docker-compose.staging.yml points to the correct env_file if you renamed it.
```

### 2. Build and Start Services
Run the following command to build the Docker images and start the cluster in detached mode:
```bash
docker compose -f docker-compose.staging.yml up -d --build
```
*(Note: `entrypoint.sh` automatically waits for the DB, runs `migrate`, and `collectstatic`.)*

### 3. Create Superuser (First Time Only)
To access the Django admin panel, create a superuser on the running web container:
```bash
docker compose -f docker-compose.staging.yml exec web python manage.py createsuperuser
```

### 4. Viewing Logs
To debug or monitor the services:
```bash
docker compose -f docker-compose.staging.yml logs -f
# Or for a specific service:
docker compose -f docker-compose.staging.yml logs -f web
```

### 5. Stopping / Teardown
To stop the services without removing data:
```bash
docker compose -f docker-compose.staging.yml stop
```

To completely tear down the environment (including volumes/database data):
```bash
docker compose -f docker-compose.staging.yml down -v
```

## Rollback Notes
If a deployment fails:
1. Revert to the previous working Git commit.
2. Rebuild and restart the containers: `docker compose -f docker-compose.staging.yml up -d --build`.
3. If database migrations need to be rolled back, execute `docker compose -f docker-compose.staging.yml exec web python manage.py migrate <app_name> <migration_number>` before reverting the code, or restore from a database backup.
