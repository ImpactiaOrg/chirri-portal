import importlib

import pytest


def test_default_storage_is_filesystem_when_use_r2_is_unset(settings):
    assert settings.STORAGES["default"]["BACKEND"] == "django.core.files.storage.FileSystemStorage"


def test_default_storage_switches_to_s3_when_use_r2_is_true(monkeypatch):
    monkeypatch.setenv("USE_R2", "1")
    monkeypatch.setenv("R2_ACCESS_KEY_ID", "x")
    monkeypatch.setenv("R2_SECRET_ACCESS_KEY", "y")
    monkeypatch.setenv("R2_ENDPOINT_URL", "https://r2.example")
    monkeypatch.setenv("R2_PUBLIC_URL", "https://pub.example")
    from config.settings import base as base_settings
    importlib.reload(base_settings)
    assert base_settings.STORAGES["default"]["BACKEND"] == "storages.backends.s3.S3Storage"
    assert base_settings.AWS_S3_ENDPOINT_URL == "https://r2.example"
