#!/bin/sh

set -e

# Migrations and collectstatic belong to the web container; running them here
# would race it. Start this container after the web container has rolled out.
exec celery -A backend worker --loglevel=INFO \
    --concurrency="${CELERY_CONCURRENCY:-2}" \
    --max-tasks-per-child=100
