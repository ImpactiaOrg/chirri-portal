"""
Regresión DEV-69: las settings de producción deben fallar si
DJANGO_SECRET_KEY no está explícitamente seteada en el environment.

El default de base.py es un token random generado en runtime; en dev es
aceptable (rotás sesiones al reiniciar), pero en prod romper sesiones y
JWTs en cada deploy sería doloroso e invisible. La defensa es esta
aserción al importar production.py.
"""
from __future__ import annotations

import os
import subprocess
import sys
import textwrap


def _run_with_env(env: dict[str, str]) -> subprocess.CompletedProcess[str]:
    script = textwrap.dedent(
        """
        import django
        django.setup = lambda: None
        from config.settings import production  # noqa: F401
        print("OK")
        """
    )
    return subprocess.run(
        [sys.executable, "-c", script],
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )


def test_production_fails_fast_without_secret_key():
    env = {
        k: v
        for k, v in os.environ.items()
        if k not in {"DJANGO_SECRET_KEY", "SECRET_KEY"}
    }
    result = _run_with_env(env)
    assert result.returncode != 0, result.stdout
    assert "DJANGO_SECRET_KEY" in result.stderr


def test_production_boots_with_explicit_secret_key():
    env = {**os.environ, "DJANGO_SECRET_KEY": "explicit-prod-key-from-env"}
    result = _run_with_env(env)
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "OK"
