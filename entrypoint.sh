#!/bin/sh
set -e

if [ "$DATABASE_URL" != "" ]; then
    echo "Waiting for postgres..."

    # Extract host and port from DATABASE_URL
    # postgres://postgres:postgres@db:5432/bali_rent_staging
    DB_HOST=$(echo $DATABASE_URL | cut -d'@' -f2 | cut -d':' -f1)
    DB_PORT=$(echo $DATABASE_URL | cut -d'@' -f2 | cut -d':' -f2 | cut -d'/' -f1)

    until nc -z $DB_HOST $DB_PORT; do
      echo "Postgres is unavailable - sleeping"
      sleep 1
    done

    echo "PostgreSQL started"
fi

if [ "$1" = "gunicorn" ]; then
    # Run migrations
    echo "Running migrations..."
    python manage.py migrate --noinput

    # Collect static files
    echo "Collecting static files..."
    python manage.py collectstatic --noinput
fi

exec "$@"
