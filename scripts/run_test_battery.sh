#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

echo "==> Unit tests (pytest, sqlite in-memory)"
docker compose exec -T -e DJANGO_SETTINGS_MODULE=config.settings.test backend pytest tests/

echo "==> Ensuring dev stack is up"
docker compose up -d --wait

echo "==> E2E smoke tests (Playwright)"
npm --prefix frontend run test:e2e:smoke

echo "==> Battery completed"
