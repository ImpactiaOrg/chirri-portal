#!/bin/bash
# Bootstrap tasks shared by dev (runserver) and prod (gunicorn): migrations
# + seeding the Django superuser defined by DJANGO_SUPERUSER_EMAIL / _PASSWORD.
set -e

echo "[bootstrap] running migrations"
python manage.py migrate --noinput

echo "[bootstrap] seeding superuser (if missing)"
python manage.py shell <<'PY' || true
import os
from django.contrib.auth import get_user_model
User = get_user_model()
email = os.environ.get("DJANGO_SUPERUSER_EMAIL", "admin@chirri.local")
password = os.environ.get("DJANGO_SUPERUSER_PASSWORD", "admin123")
if not User.objects.filter(email=email).exists():
    User.objects.create_superuser(email=email, password=password)
    print(f"[bootstrap] created superuser {email}")
else:
    print(f"[bootstrap] superuser {email} already exists")
PY
