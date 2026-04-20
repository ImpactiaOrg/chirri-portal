# Spec — `/campaigns` list screen

**Ticket:** DEV-79 (to be created in Linear on approval)
**Date:** 2026-04-20
**Author:** Daniel + Claude

## Context

El portal tiene hoy `/home` con un link "Tus campañas" que apunta a `/campaigns`, pero la ruta no existe — 404. Esta spec cubre la lista de campañas de un cliente: activas arriba (cards grandes), archivadas abajo (rows compactas). Pattern ya prototipado por Design en `Design/handoff/chirri-portal/project/v2/screens/campaigns.jsx`.

Source of truth del diseño son los mockups JSX + el `design-prompt.md` original. Campos inventados por claude design (`totalReach`, `pieces`, `influencers`) quedan **fuera de scope** — se ticketan aparte con prioridad baja (ver "Follow-ups").

## Goal

Usuario logueado de un cliente entra a `/campaigns` y ve todas las campañas de su cliente, separadas en activas vs archivadas, con información mínima útil para decidir cuál abrir.

## Non-goals

- Detalle de campaña (`/campaigns/[id]`) — ticket aparte.
- Filtros, búsqueda, paginación — no hay volumen que lo justifique (hoy el seed tiene 3 campañas, se espera ~10-20 por cliente en horizonte realista).
- Métricas agregadas a nivel campaña (total reach, piezas, influencers) — ver "Follow-ups".
- Admin UI para crear/editar campañas — ya existe vía Django admin.

## Architecture

Una página Server Component que hace SSR del fetch al backend y renderiza dos secciones.

```
frontend/app/campaigns/page.tsx                 ← server component, fetch + split
frontend/app/campaigns/CampaignCardBig.tsx      ← server, card activas
frontend/app/campaigns/CampaignRowArchived.tsx  ← server, row archivadas
frontend/lib/format.ts                          ← pure funcs formatPeriod / formatReportDate / MONTHS_ES
```

Separación:
- `page.tsx` — orquesta fetch y split. Usa `getAccessToken()` y `apiFetch()` (helpers existentes en `lib/auth.ts` y `lib/api.ts`), llama `GET /api/campaigns/`, divide por `status`.
- Sub-componentes — solo render (server components sin estado). Reciben `campaign: CampaignDto` y (para el card grande) `colorIndex`. Envuelven con `<Link href={...}>` para navegación accesible.
- `lib/format.ts` — funciones puras, cero dependencias. `MONTHS_ES` se extrae desde `home/page.tsx` (que hoy lo define local) — DRY.

**Tipos:** el tipo `CampaignDto` ya existe en `frontend/lib/api.ts` (línea 63) y refleja el shape del `CampaignListSerializer`. Se consume tal cual — no se crea un tipo nuevo. Si el serializer cambia, TS rompe el build.

No hay cambios de backend. `CampaignListSerializer` ya expone todos los campos que el UI necesita.

## Data flow

```
/api/campaigns/ → { results: Campaign[] }  (tenant-scoped por viewset)
  ↓
CampaignsPage (server)
  ├── activas  = results.filter(c => c.status === 'ACTIVE')
  └── archivo  = results.filter(c => c.status !== 'ACTIVE')   // incluye FINISHED y PAUSED
  ↓
  Render
  ├── <Pill mint>ACTIVAS · N</Pill>
  │     activas.map((c, i) => <CampaignCardBig c={c} colorIndex={i % 3} />)
  └── <Pill white>ARCHIVO · N</Pill>
        archivo.map(c => <CampaignRowArchived c={c} />)
```

## Components

### `CampaignsPage` (Server Component)

- Lee `access` JWT del cookie.
- Fetch a `BACKEND_INTERNAL_URL/api/campaigns/` con `Authorization: Bearer <jwt>`.
- En error de auth → redirect a `/login` (mismo patrón que `home/page.tsx`).
- Layout: `main.page.page-wide` con `background: var(--chirri-pink)`.
- Secciones:
  1. Header: breadcrumb (`"Chirri Portal · {clientName}"`) + `<h1>campañas.</h1>` + sub-copy.
  2. Activas: pill mint con count + stack vertical de `CampaignCardBig`.
  3. Archivo: separador `border-top: 3px solid black` + pill white con count + stack de `CampaignRowArchived`.

Si `activas.length === 0`: la pill muestra "ACTIVAS · 0" y no se renderizan cards (sin empty state extra — la pill ya comunica el estado).
Si `archivo.length === 0`: mismo patrón (pill 0, sin rows).

### `CampaignCardBig`

Props: `{ campaign: Campaign, colorIndex: 0 | 1 | 2 }`.

Paleta: `['var(--chirri-mint)', 'var(--chirri-peach)', 'var(--chirri-lilac)']`. `colorIndex` se calcula en el padre como `index % 3` sobre el orden que devuelve el backend (`-start_date`). Determinístico por orden, no por id — si se agrega una campaña nueva al top, las existentes mantienen color relativo (la primera sigue siendo mint).

Render según mockup (`campaigns.jsx:40-75`):
- Background = color según `colorIndex`.
- Borde 2.5px negro, border-radius 22px, shadow 4px 4px 0 black.
- Grid 2 columnas: izquierda texto, derecha CTA.
- Izquierda: status pill verde + período, nombre en `font-display` lowercase 64px, `brief`, línea inferior con `{reportCount} reportes · último {lastReportDate}`.
- Derecha: label "Abrir →" como botón primario. (El mockup tiene "Alcance total" con `totalReach` — se omite, es scope de follow-up.)

Click → navega a `/campaigns/{id}` (aunque la ruta aún no existe, el link queda listo para cuando se implemente).

### `CampaignRowArchived`

Props: `{ campaign: Campaign }`.

Render según mockup (`campaigns.jsx:77-101`), adaptado:
- Grid: `1fr 200px 120px 120px 80px`.
- Columnas: nombre (display 24px lowercase) + brief truncado a 80 chars | período | `{reportCount} reportes` | `último {lastReportDate}` | "Abrir →".
- Sin `totalReach` (follow-up).

### `formatPeriod(start_date, end_date, is_ongoing_operation) → string`

Pure function. Reglas:

| `is_ongoing` | `start` | `end` | Output |
|---|---|---|---|
| `true` | cualquiera | cualquiera | `"operación continua"` |
| `false` | set | `null` | `"feb 2026 – en curso"` |
| `false` | set | set, mismo año que start | `"feb – dic 2025"` |
| `false` | set | set, año distinto | `"feb 2024 – dic 2025"` |
| `false` | `null` | * | `"—"` (defensivo; no debería pasar) |

Meses en español abreviado lowercase (`"feb"`, `"mar"`, etc.).

### `formatReportDate(iso_string) → string`

`"2026-04-15T10:23:00Z"` → `"15 abr 2026"`. Si `null` → `"sin reportes"`.

## Auth & tenant scoping

Heredado del backend. El ViewSet filtra por `request.user.client_id` (gotcha documentado en CLAUDE.md — scoping en view, no en middleware). Frontend solo pasa el JWT, no valida client-side.

## Error handling

- **JWT expirado**: el middleware de Next ya hace refresh silencioso (ver `frontend/middleware.ts`, DEV-68). Si el refresh falla, redirect a `/login`.
- **Fetch error (500, red caída)**: renderiza un mensaje simple en la página (`"No pudimos cargar las campañas. Refrescá la página."`). Sin retry automático.
- **Lista vacía** (cliente sin campañas): ambas pills muestran "· 0" y no se renderizan cards. No es un error.

## Testing

### Unit (frontend) — NO EN ESTE TICKET

**Deuda técnica asumida.** Frontend no tiene infra de unit tests (no Vitest, no Jest — solo Playwright E2E). Instalar Vitest agregaría scope y va en un ticket separado (DEV-81). Las funciones puras de `lib/format.ts` quedan sin unit tests automatizados; su cobertura se ejerce vía E2E y TypeScript.

Riesgo controlado: `formatPeriod` y `formatReportDate` son determinísticas, chicas (~20 líneas cada una), y los inputs están acotados. Cuando se instale Vitest (DEV-81), estos dos formatters son el target natural de los primeros tests.

### E2E smoke (Playwright)

Extensión de `frontend/tests/home.spec.ts`, o archivo nuevo `frontend/tests/campaigns.spec.ts` si crece mucho. La decisión se toma en el plan — si son solo 3 assertions, van inline en `home.spec.ts`; si es un flujo con setup propio, archivo nuevo.

Aserciones mínimas:
- Después del login demo (`belen.rizzo@balanz.com` / `balanz2026`), navegar a `/campaigns`.
- Verificar `h1` contiene "campañas" (lowercase por el `text-transform`).
- Verificar que "De Ahorrista a Inversor" (la campaña activa del seed) aparece en la página.
- Verificar que aparece la pill "ARCHIVO" (con las 2 campañas del seed: Campaña B y C finished).
- Verificar que la card activa contiene el string del período formateado y el conteo de reportes.

El smoke corre vía `npm run test:e2e:smoke`. Si se crea un archivo nuevo, agregarlo al script en `frontend/package.json`.

### Regresión

No aplica — no estamos arreglando un bug.

## Quality dimensions

Complementa las secciones anteriores con requisitos que `entropy-scan` evalúa y que no tenían home natural arriba.

**Complexity budget (dim 4).** Ningún archivo debería pasar ~200 líneas:
- `page.tsx` estimado ~80-100 (fetch + split + JSX de secciones).
- `CampaignCardBig.tsx` ~80-120 (el JSX es denso pero todo inline, sin lógica).
- `CampaignRowArchived.tsx` ~50-70.
- `lib/format.ts` ~50-70 (dos funciones + helpers de meses).

Si algún archivo se acerca al límite durante la implementación, parar y pedir guidance antes de split prematuro.

**Principles alignment (dim 5).**
- **P2 (SRP):** cada componente tiene una sola razón de cambio. `page.tsx` cambia si cambia el layout de la página; `CampaignCardBig` si cambia la card activa; `format.ts` si cambian las reglas de fecha.
- **P3 (DRY):** `formatPeriod` y `formatReportDate` son la única fuente de verdad para esos strings. Nadie más formatea fechas de campaña en frontend.
- **P5 (DIP):** `colorIndex` se pasa como prop al card, no se calcula adentro. La card no depende de "la lista de campañas" ni del orden — solo de su color.
- **P10 (Simplicity):** nada de framework de colores, context providers, ni lib externa de fechas. Funciones puras + objetos literales.

**Boundaries & typing (dim 3).** Frontend define un tipo `Campaign` en `frontend/lib/types.ts` (o extiende el existente) que refleja exactamente los campos que devuelve `CampaignListSerializer`. Las dos subcomponentes y `formatPeriod` consumen ese tipo — si el backend cambia el shape del payload, TypeScript rompe el build. Es el contrato de borde client↔server.

**Accessibility (dim 11).** Las cards son clickables pero hoy el mockup usa `<div onClick>`. En la implementación real:
- Wrap cada card/row en `<Link href={`/campaigns/${c.id}`}>` (Next.js `<Link>`, no un div con onClick). Hereda keyboard nav, focus ring y semántica nativa de anchor.
- El h1 "campañas." es el único h1 de la página. Las cards usan h2 para el nombre (como el mockup ya indica).
- Pills y status badges son decorativos — no necesitan role; el texto ya comunica.
- Focus states: heredados del `card-link` class existente en `globals.css`.

**Responsive (dim 11).** El mockup usa pixels fijos (64px h2, 22px border-radius, etc.). Mobile es **out of scope** para este ticket — la audiencia objetivo (Belén, equipo de Chirri) usa desktop para revisar reportes. Documentar en el PR: "desktop-only screen; mobile layout pending". Agregar `@media (max-width: 768px)` con un fallback simple ("Abrí el portal desde una compu para ver las campañas") a cargo de un follow-up si se pide.

**i18n (dim 11).** El portal es **es-AR único** — sin infra de i18n. Strings hardcodeados en español. Meses abreviados (`"ene"`, `"feb"`, …) como constante local en `format.ts`.

**Observability (dim 10).** Fetch errors loggean con `console.error` + contexto estructurado:
```ts
console.error("campaigns_fetch_failed", { url, status, hasJwt: !!jwt });
```
No hay stack de logging estructurado en frontend (no Sentry/Datadog todavía — es un follow-up de infra). El mínimo es que el error sea grep-eable en DevTools. Backend ya loggea request failures vía Django default.

**Git Health (dim 8).** Commits atómicos, cada uno compilable independientemente:
1. `feat(campaigns): add formatPeriod/formatReportDate helpers (DEV-79)` — solo `lib/format.ts` + su test.
2. `feat(campaigns): add CampaignCardBig and CampaignRowArchived components (DEV-79)`.
3. `feat(campaigns): add /campaigns list page and E2E smoke (DEV-79)`.

Squash en PR queda opcional; preferimos mantener los 3 para que `git log --follow` de cada archivo sea limpio.

**Repo Hygiene (dim 12).** Al mergear el PR:
- Actualizar `README.md` si menciona páginas disponibles (chequear primero).
- Archivar spec/plan: dejar los archivos en `docs/superpowers/specs/` y `docs/superpowers/plans/` — el repo ya mantiene histórico, no se borran.
- No se crean archivos en ubicaciones deprecadas (todo bajo `frontend/app/campaigns/` y `frontend/lib/`).

**CI/CD (dim 13).** Sin cambios de pipeline:
1. PR gate: `.github/workflows/test.yml` ya corre backend unit, frontend unit, E2E smoke en `pull_request` a `main`/`development`. Los tests nuevos (`format.test.ts` + assertions en `smoke.spec.ts`) los toma automáticamente.
2. Build: Docker build reusa layer cache; el cambio es frontend-only, rebuildeará solo frontend image.
3. Deploy: `.github/workflows/deploy.yml` dispara en push a `development` → Hetzner. Sin cambios.
4. Post-deploy smoke: pendiente como parte de DEV-77 (staging) — fuera de scope acá.
5. Rollback: `git revert` + push a `development` (pipeline existente).

No hay nuevos secrets ni env vars. `BACKEND_INTERNAL_URL` ya existe (`.env.example`).

## Follow-ups (tickets aparte)

1. **DEV-80 (a crear, priority Low, state "Someday" — validar con Chirri)**: Métricas agregadas a nivel campaña. `total_reach`, `piece_count`, `influencer_count`, `engagement_rate` computados como sum/count sobre los reportes de la campaña. Endpoint: extender `CampaignListSerializer` con annotations, o endpoint nuevo `/api/campaigns/<id>/summary/`. UI: volver a mostrar `Alcance total` en el card grande + columna en la row de archivo. **Requiere validación con Chirri si es info que quieren ver o no.**

2. **DEV-81 (a crear, priority Medium)**: Instalar Vitest en frontend y migrar las utils de formateo (`formatPeriod`, `formatReportDate`, `formatCompact`, `firstName`, `sumReach`) a archivos con unit tests. Config mínima, script `test:unit:frontend`, wirear al `test:battery`. Primer test target: los formatters que dejamos sin cobertura en DEV-79.

3. **`/campaigns/[id]` detalle** — ticket aparte (DEV-82 probable). Fuera de scope acá.

## Definition of Done

- [ ] Linear ticket DEV-79 creado y en In Progress.
- [ ] Archivos nuevos: `frontend/app/campaigns/page.tsx`, `CampaignCardBig.tsx`, `CampaignRowArchived.tsx`, `frontend/lib/format.ts`.
- [ ] `home/page.tsx` migrado a importar `MONTHS_ES` y `formatMonthYear` desde `lib/format.ts` (DRY).
- [ ] `CampaignDto` existente reutilizado (no se crea `types.ts`).
- [ ] Cards envueltas en `<Link>` de Next (no `<div onClick>`).
- [ ] E2E smoke extendido con las aserciones del spec.
- [ ] `npm run test:e2e:smoke` verde.
- [ ] `npm --prefix frontend run typecheck` verde.
- [ ] Verificación manual en browser: login → home → click "Tus campañas" → ver `/campaigns` con la campaña activa en color mint y las 2 archivadas como rows.
- [ ] Ningún archivo supera ~200 líneas.
- [ ] Commits atómicos (mínimo 3, ver sección Git Health).
- [ ] Follow-up tickets DEV-80 (metrics aggregate) y DEV-81 (Vitest setup) creados.
- [ ] PR a `development`, mergeado, ticket DEV-79 → In Review + Euge.
