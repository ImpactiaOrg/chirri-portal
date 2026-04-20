# Environment variables

**Owner:** Daniel Zacharias.

Listed variables are read by `backend/config/settings/*.py` and
`frontend/lib/*`. Local dev defaults come from `docker-compose.yml`
and `.env.example`. Prod values live in GitHub Actions secrets for
`deploy.yml` and are injected into the Hetzner container env.

## Backend — core

| Name | Purpose | Required in prod |
|------|---------|------------------|
| `DJANGO_SECRET_KEY` | Django secret key | Yes |
| `DJANGO_ALLOWED_HOSTS` | CSV of hostnames | Yes |
| `POSTGRES_*` | DB connection | Yes |
| `REDIS_URL` | Celery broker/result | Yes |
| `CORS_ALLOWED_ORIGINS` | CSV of frontend origins | Yes |
| `CSRF_TRUSTED_ORIGINS` | CSV of frontend origins | Yes |

## Storage (R2)

Used when `USE_R2=1`. Unset locally to fall back to `backend/media/`.

| Name | Purpose | Required when USE_R2 |
|------|---------|----------------------|
| `USE_R2` | Toggle S3/R2 backend | Set to `1` in prod |
| `R2_ACCESS_KEY_ID` | Cloudflare R2 access key | Yes |
| `R2_SECRET_ACCESS_KEY` | Cloudflare R2 secret | Yes |
| `R2_ENDPOINT_URL` | e.g. `https://<acct>.r2.cloudflarestorage.com` | Yes |
| `R2_BUCKET_NAME` | Default `chirri-media` | No |
| `R2_PUBLIC_URL` | Public base URL for objects | Yes |

**Bucket setup:** `npx wrangler r2 bucket create chirri-media`.

## Frontend

| Name | Purpose |
|------|---------|
| `BACKEND_INTERNAL_URL` | URL used by Next server components to reach Django |
| `NEXT_PUBLIC_*` | Any public-side config (browser-exposed) |
