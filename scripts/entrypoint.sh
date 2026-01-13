#!/bin/bash

# Wait for PostgreSQL with retry logic
echo "Waiting for PostgreSQL..."
max_retries=30
retry_count=0

while ! nc -z $DB_HOST $DB_PORT; do
  retry_count=$((retry_count + 1))
  if [ $retry_count -ge $max_retries ]; then
    echo "PostgreSQL is not available after $max_retries retries"
    exit 1
  fi
  echo "PostgreSQL not ready yet. Retry $retry_count/$max_retries..."
  sleep 2
done
echo "PostgreSQL started"

# Wait for Redis
echo "Waiting for Redis..."
while ! nc -z redis 6379; do
  sleep 0.5
done
echo "Redis started"

# Apply database migrations
echo "Applying migrations..."
python manage.py migrate --noinput

# Collect static files
echo "Collecting static files..."
python manage.py collectstatic --noinput

# Create superuser if it doesn't exist
echo "Creating superuser if needed..."
python manage.py createsuperuser --noinput || true

exec "$@"