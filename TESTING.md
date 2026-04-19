# Testing Strategy

This project uses a practical test pyramid, matching the Siga pattern:

- **Unit tests (`pytest`)** for backend business logic and API contracts.
- **E2E smoke tests (`Playwright`)** for the critical user flow (login → home).
- **Full E2E suite (`Playwright`)** for deeper validation before releases.

## Commands

From the repo root:

- `npm run test:unit` — backend pytest suite in an in-memory SQLite DB.
- `npm run test:e2e:smoke` — Playwright smoke tests against the dev stack.
- `npm run test:e2e:all` — full Playwright suite.
- `npm run test:battery` (or `npm test`) — unit tests + ensure dev stack is up + smoke E2E.

The first time you run E2E locally:

```bash
cd frontend
npm install --legacy-peer-deps
npx playwright install chromium
```

The E2E tests assume `docker compose up -d` has been run and the seed user
(`belen.rizzo@balanz.com` / `balanz2026`) is present. If not, run
`docker compose exec backend python manage.py seed_demo` first.

## Definition of Done (mandatory)

Every new feature or bugfix must include:

- At least one **unit test** covering the new or changed backend logic.
- At least one **E2E update** when the change is user-visible.
- Green execution of `npm run test:unit` and `npm run test:e2e:smoke`.

CI (`.github/workflows/test.yml`) runs three jobs on every PR:

- `backend` — pytest against `config.settings.test` (sqlite in-memory, no Postgres/Redis needed).
- `frontend` — typecheck + lint + build.
- `e2e-smoke` — boots the dev stack in compose, seeds demo data, runs Playwright smoke tests.

A PR cannot merge with any of these red.

## Authoring rules

- Keep unit tests deterministic and fast. No network calls.
- Prefer testing DRF views and services directly over framework internals.
- E2E smoke tests must avoid flaky external dependencies.
- When you fix a bug, add a regression test that would have caught it —
  the docstring should name the bug so future readers know why the test
  exists.
