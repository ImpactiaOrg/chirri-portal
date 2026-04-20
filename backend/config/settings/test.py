"""Test settings: SQLite, fast hasher, quiet logs."""
from .base import *  # noqa: F401,F403

DEBUG = False
# Key de ≥32 bytes para que SimpleJWT (HMAC-SHA256, RFC 7518) no tire warnings.
SECRET_KEY = "test-secret-key-must-be-at-least-32-bytes-to-satisfy-rfc-7518"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}

PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.MD5PasswordHasher",
]

EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"

CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True

STATICFILES_STORAGE = "django.contrib.staticfiles.storage.StaticFilesStorage"

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {"null": {"class": "logging.NullHandler"}},
    "root": {"handlers": ["null"], "level": "WARNING"},
}

MIDDLEWARE = [m for m in MIDDLEWARE if m != "whitenoise.middleware.WhiteNoiseMiddleware"]
