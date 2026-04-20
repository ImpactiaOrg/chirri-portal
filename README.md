# Chirri Portal

Portal multi-tenant para clientes de Chirri Peppers (agencia de redes sociales AR). Reemplaza el ida y vuelta de reportes en PDF por un portal donde cada cliente entra con su login, ve sus reportes con la identidad visual de su marca, y revisa el contenido programado.

Cliente ancla: **Balanz** — campaña "De Ahorrista a Inversor".

## Stack

- **Backend:** Django 5 + DRF + PostgreSQL 15 + Redis + Celery
- **Frontend:** Next.js 14 (App Router) + TypeScript
- **Infra:** Docker Compose (dev + prod) + Nginx, deploy a Hetzner por GitHub Actions
- **Auth:** JWT (SimpleJWT) + cookies `httpOnly` en Next.js server actions

## Estructura

```
chirri-portal/
├─ backend/              # Django + DRF
│  ├─ apps/              # tenants, users, campaigns, influencers, reports, scheduling
│  └─ config/settings/   # base.py, development.py, production.py
├─ frontend/             # Next.js App Router
│  ├─ app/               # login, home, logout
│  └─ lib/               # api client, auth helpers
├─ nginx/                # nginx.prod.conf (SSL + proxy)
├─ docker-compose.yml           # dev stack
├─ docker-compose.prod.yml      # prod stack (Hetzner)
├─ .github/workflows/    # test.yml, deploy.yml
├─ docs/                 # specs de arquitectura
└─ design/               # handoff visual
```

## Dev

```bash
cp .env.example .env
docker compose up --build
```

- Portal: http://localhost:3000
- Django Admin: http://localhost:3000/admin (proxy vía Next.js al backend — superuser bootstrap con `DJANGO_SUPERUSER_EMAIL` / `_PASSWORD` en `.env`)
- API: http://localhost:3000/api (también http://localhost:8000/api si querés hitear directo para debug)
- Healthcheck: http://localhost:3000/api/health/

### Cargar datos

**Demo (data del mock de diseño · Balanz):**

```bash
docker compose exec backend python manage.py seed_demo
# o para limpiar y recargar:
docker compose exec backend python manage.py seed_demo --wipe
```

El seed carga el Client Balanz, 3 campañas (1 activa + 2 terminadas), 4 stages, 6 influencers, y ~8 reportes con métricas. Crea también el usuario **belen.rizzo@balanz.com / balanz2026** para loguear al portal.

**Para producción:** cargar Client, Brand, Campaign, Stage y ClientUser desde `/admin`.

### Rutas del portal
- `/login`, `/home`, `/campaigns`, `/campaigns/[id]`, `/reports/[id]`

### Env vars nuevas (R2)
Ver `docs/ENV.md`. En dev dejá `USE_R2` unset — se usa filesystem local.

### Endpoints de auth

- `POST /api/auth/login/` → `{ access, refresh, user }`
- `POST /api/auth/refresh/` → `{ access }`
- `GET  /api/auth/me/` → usuario + cliente + brands

## Deploy

Push a `development` dispara `.github/workflows/deploy.yml` que se conecta por SSH a Hetzner y corre `docker compose -f docker-compose.prod.yml up -d --build` + migraciones + collectstatic.

Secretos requeridos en el repo de GitHub:
- `HETZNER_HOST`, `HETZNER_USER`, `HETZNER_SSH_KEY`, `HETZNER_PORT` (opcional)

En el servidor, el directorio `/opt/chirri-portal` debe contener un clon del repo y un `.env` con los valores de producción (SECRET_KEY, credenciales de Postgres, dominio, etc.). SSL se maneja con certbot apuntando a `/etc/letsencrypt` (ver `nginx/nginx.prod.conf`).

## Tests

```bash
# backend
cd backend && pytest

# frontend
cd frontend && npm run typecheck && npm run build
```

CI corre ambos en cada push/PR a `main` y `development` (`.github/workflows/test.yml`).

## Rollback
1. `git revert <bad-sha>` o `git reset --hard <good-sha>` en `development`.
2. Push — `deploy.yml` redespliega la imagen previa (pineada por SHA, no `:latest`).
3. Si hay que rollback de migración: `docker compose exec backend python manage.py migrate reports <prev>`. Las migraciones DEV-52 son aditivas (campos/modelos nuevos); el rollback no pierde datos de columnas existentes.

## Documentación

- Arquitectura y modelo de datos: `docs/superpowers/specs/2026-04-18-chirri-portal-foundation-design.md`
- Addendum de diseño: `Documents/design-prompt-addendum-data-model.md`
- Linear: [Chirri Portal](https://linear.app/impactia/project/chirri-portal-dfd8e3e47945)
