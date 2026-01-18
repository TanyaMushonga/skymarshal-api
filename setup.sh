#!/bin/bash

echo "Setting up SkyMarshal..."

# Create models directory
mkdir -p models

# Run migrations
python manage.py makemigrations
python manage.py migrate

# Create superuser (interactive)
python manage.py createsuperuser

# Create TimescaleDB hypertable (if using TimescaleDB)
# python manage.py shell << EOF
# from django.db import connection
# with connection.cursor() as cursor:
#     cursor.execute("SELECT create_hypertable('traffic_metrics', 'timestamp');")
# EOF

# Collect static files
python manage.py collectstatic --noinput

echo "Setup complete!"