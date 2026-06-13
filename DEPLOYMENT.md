# Bali Rent Deployment Guide

This guide prepares the current Django REST Framework project for deployment on an Ubuntu VPS with PostgreSQL, Gunicorn, and Nginx while keeping the existing SQLite database intact for rollback and data migration.

## 1. What changed

- Django settings now read configuration from `.env` via `django-environ`.
- PostgreSQL is configured through `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, and `DB_PORT`.
- SQLite remains available as a fallback when PostgreSQL variables are not provided.
- Static files are collected to `/var/www/bali_rent/static`.
- Media files are stored in `/var/www/bali_rent/media`.
- Ready-to-use `gunicorn.service` and `nginx.conf` files are included.

## 2. Environment variables

Create the production env file:

```bash
cp .env.example .env
```

Required variables:

```env
SECRET_KEY=replace-with-a-strong-secret-key
DEBUG=False
ALLOWED_HOSTS=*
DB_NAME=bali_rent
DB_USER=bali_rent_user
DB_PASSWORD=change-me
DB_HOST=127.0.0.1
DB_PORT=5432
```

Notes:

- `ALLOWED_HOSTS=*` is intentionally open for the first stage, as requested. Replace it with real domains as soon as DNS is ready.
- If an old environment still uses `DATABASE_URL`, the project will continue to support it as a fallback.

## 3. Clean Ubuntu VPS setup

These commands assume Ubuntu 24.04 or 22.04 and deploy the backend into `/var/www/bali_rent/app`.

```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-pip postgresql postgresql-contrib nginx redis-server git libpq-dev
```

Create directories:

```bash
sudo mkdir -p /var/www/bali_rent
sudo chown -R $USER:$USER /var/www/bali_rent
cd /var/www/bali_rent
git clone -b ibro_dev https://github.com/adilhanDevs/bali_rent.git app
cd app
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

## 4. PostgreSQL setup

Create database and user:

```bash
sudo -u postgres psql
```

Inside `psql`:

```sql
CREATE DATABASE bali_rent;
CREATE USER bali_rent_user WITH PASSWORD 'change-me';
ALTER ROLE bali_rent_user SET client_encoding TO 'utf8';
ALTER ROLE bali_rent_user SET default_transaction_isolation TO 'read committed';
ALTER ROLE bali_rent_user SET timezone TO 'UTC';
GRANT ALL PRIVILEGES ON DATABASE bali_rent TO bali_rent_user;
\q
```

## 5. Safe SQLite to PostgreSQL migration

Do not delete or overwrite `db.sqlite3`. Keep it as the rollback source.

### Step 1. Backup SQLite and media

From the project directory on the server or from the current host before upload:

```bash
mkdir -p backups
cp db.sqlite3 backups/db.sqlite3.$(date +%F-%H%M%S).bak
tar -czf backups/media.$(date +%F-%H%M%S).tar.gz media
```

### Step 2. Create a Django fixture from SQLite

Run this while the project is still pointed at SQLite:

```bash
python manage.py dumpdata \
  --natural-foreign \
  --natural-primary \
  --exclude contenttypes \
  --exclude auth.permission \
  --exclude admin.logentry \
  --indent 2 > backups/sqlite-data.json
```

This approach is safer than directly rewriting the SQLite file because:

- it keeps the original database untouched;
- it uses Django's ORM-level serialization;
- it avoids destructive in-place conversion.

### Step 3. Switch `.env` to PostgreSQL

Set the `DB_*` variables in `.env` and make sure `DEBUG=False`.

### Step 4. Create PostgreSQL schema

```bash
python manage.py migrate --noinput
```

### Step 5. Load SQLite data into PostgreSQL

```bash
python manage.py loaddata backups/sqlite-data.json
```

### Step 6. Restore uploaded files if needed

If media originally lived inside the repo, move it to the VPS media directory:

```bash
sudo mkdir -p /var/www/bali_rent/media /var/www/bali_rent/static
sudo chown -R www-data:www-data /var/www/bali_rent/media /var/www/bali_rent/static
rsync -av media/ /var/www/bali_rent/media/
```

### Step 7. Verify migration success

Run:

```bash
python manage.py showmigrations | tail
python manage.py check
python manage.py shell -c "from django.contrib.auth import get_user_model; print('users=', get_user_model().objects.count())"
python manage.py shell -c "from bookings.models import Booking; print('bookings=', Booking.objects.count())"
python manage.py shell -c "from catalog.models import Vehicle; print('vehicles=', Vehicle.objects.count())"
```

If counts match the SQLite environment and the API responds correctly, the migration is considered successful.

## 6. Static files

Collect static files into the Nginx-served directory:

```bash
sudo mkdir -p /var/www/bali_rent/static /var/www/bali_rent/media
sudo chown -R www-data:www-data /var/www/bali_rent/static /var/www/bali_rent/media
source venv/bin/activate
python manage.py collectstatic --noinput
```

## 7. Gunicorn

Correct WSGI module:

```bash
bali_rent.wsgi:application
```

Manual start command:

```bash
/var/www/bali_rent/app/venv/bin/gunicorn \
  --workers 3 \
  --timeout 120 \
  --bind unix:/run/bali_rent/gunicorn.sock \
  bali_rent.wsgi:application
```

Install the systemd unit:

```bash
sudo cp gunicorn.service /etc/systemd/system/gunicorn.service
sudo systemctl daemon-reload
sudo systemctl enable gunicorn
sudo systemctl start gunicorn
sudo systemctl status gunicorn
```

## 8. Nginx

Install the site config:

```bash
sudo cp nginx.conf /etc/nginx/sites-available/bali_rent
sudo ln -sf /etc/nginx/sites-available/bali_rent /etc/nginx/sites-enabled/bali_rent
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t
sudo systemctl restart nginx
```

The included config:

- proxies application traffic to Gunicorn;
- serves `/static/` from `/var/www/bali_rent/static/`;
- serves `/media/` from `/var/www/bali_rent/media/`;
- allows larger uploads with `client_max_body_size 25M`.

## 9. Deployment run order

Use this order on a clean VPS:

```bash
cd /var/www/bali_rent/app
source venv/bin/activate
cp .env.example .env
nano .env
python manage.py migrate --noinput
python manage.py collectstatic --noinput
sudo systemctl restart gunicorn
sudo systemctl restart nginx
```

If you are migrating from SQLite with real data, insert the fixture export/import steps before the final service restart.

## 10. Post-deploy checks

```bash
python manage.py check --deploy
curl http://127.0.0.1/
sudo systemctl status gunicorn
sudo systemctl status nginx
```

If HTTPS is added later with Certbot, keep `SECURE_SSL_REDIRECT=True` and update `ALLOWED_HOSTS` and `CSRF_TRUSTED_ORIGINS` to the real domains.
