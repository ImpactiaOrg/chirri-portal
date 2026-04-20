# Chirri Portal — Claude guidance

Portal multi-tenant Django + Next.js. Ver `README.md` para el panorama.

## Tests (no negociable)

Toda feature o bugfix requiere:

- **Unit test** para la lógica de backend nueva o modificada.
- **E2E update** cuando el cambio es user-visible (al menos el smoke).
- **Regresión con el bug nombrado en el docstring** cuando arreglás un bug.
- `npm run test:unit` y `npm run test:e2e:smoke` en verde antes de pedir review.

Cuando cambiás funcionalidad que ya tiene cobertura, **actualizá el test para que refleje el nuevo comportamiento esperado** — no lo skipees. Tests y código se mueven juntos.

Reglas completas, comandos y CI: `TESTING.md`.

## Stack

Django 5 + DRF · Next.js 14 (App Router, SSR) · PostgreSQL 15 · Redis · Celery · Playwright · pytest. Deploy a Hetzner vía GitHub Actions desde `development`.

## Comandos útiles

```bash
docker compose up -d                                    # dev stack
docker compose exec backend python manage.py seed_demo  # data demo (Balanz)
npm run test:unit                                       # pytest
npm run test:e2e:smoke                                  # smoke Playwright
npm run test:battery                                    # unit + smoke
```

Credenciales demo: `belen.rizzo@balanz.com` / `balanz2026`.

## Gotchas que ya nos mordieron

- **Tenant scoping va en la view, no en middleware.** El middleware de Django corre antes que la autenticación de DRF, así que `request.user` es `AnonymousUser` y el scoping silenciosamente devuelve `[]` o `None`. Scopear siempre con `getattr(self.request.user, "client_id", None)` dentro del viewset. Rompió una vez con "Unexpected end of JSON input" (abr 2026).
- **Server Components de Next no pueden escribir cookies.** Solo lo hacen middleware, route handlers y server actions. Por eso el refresh silencioso del JWT vive en `frontend/middleware.ts` — no intentar hacerlo desde `app/**/page.tsx`.
- **Hot-reload Windows → Docker es poco confiable para `middleware.ts`.** Si editás middleware y el test no ve el cambio, `docker compose restart frontend`.

## Branch model

- `development` = branch de deploy (push dispara `deploy.yml` → Hetzner).
- `main` = production-ready.
- CI (`test.yml`) corre backend + frontend + e2e-smoke en cada push/PR a `main` o `development`.
