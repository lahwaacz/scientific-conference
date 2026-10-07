#!/bin/sh

set -e

# collect static files and perform database migrations before starting the webserver
python manage.py collectstatic --no-input
python manage.py migrate

# exec makes gunicorn PID 1 so it receives SIGTERM directly (graceful worker shutdown)
exec gunicorn backend.wsgi:application --bind 0.0.0.0:8000 --access-logfile -
