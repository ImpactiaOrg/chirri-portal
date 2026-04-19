#!/bin/bash
set -e

/app/bootstrap.sh

echo "[entrypoint] collecting static files"
python manage.py collectstatic --noinput

echo "[entrypoint] starting gunicorn"
exec gunicorn --bind 0.0.0.0:8000 --workers 3 --access-logfile - config.wsgi:application
