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


def _run_with_env(
    env: dict[str, str],
    script: str = 'from config.settings import production; print("OK")',
) -> subprocess.CompletedProcess[str]:
    full = textwrap.dedent(
        f"""
        import django
        django.setup = lambda: None
        {script}
        """
    )
    return subprocess.run(
        [sys.executable, "-c", full],
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


def test_allowed_hosts_reads_django_allowed_hosts_env(tmp_path, monkeypatch):
    """Regresión DEV-77: base.py leía 'ALLOWED_HOSTS' (no 'DJANGO_ALLOWED_HOSTS'),
    así que el valor de .env.example nunca se aplicaba y en prod se caía al
    default 'localhost,127.0.0.1' — un deploy a chirri.impactia.ai daba
    DisallowedHost."""
    env = {
        **os.environ,
        "DJANGO_SECRET_KEY": "explicit-prod-key-from-env",
        "DJANGO_ALLOWED_HOSTS": "chirri.impactia.ai,staging.example.com",
    }
    env.pop("ALLOWED_HOSTS", None)
    result = _run_with_env(
        env,
        script=(
            "from config.settings import production; "
            "print(','.join(production.ALLOWED_HOSTS))"
        ),
    )
    assert result.returncode == 0, result.stderr
    hosts = result.stdout.strip()
    assert "chirri.impactia.ai" in hosts
    assert "staging.example.com" in hosts
    assert "localhost" not in hosts
