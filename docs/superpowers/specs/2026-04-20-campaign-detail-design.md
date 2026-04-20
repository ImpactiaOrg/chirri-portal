---
Ticket: DEV-86
Status: Design (entropy-aware enriched 2026-04-20)
Date: 2026-04-20
Owner: Daniel Zacharias
Related: DEV-52 (report viewer), DEV-79 (campaigns list), DEV-104 (draft preview follow-up)
---

# DEV-86 — Campaign detail page `/campaigns/[id]`

## 1. Contexto

`/campaigns` (DEV-79) ya lista las campañas y cada card linkea a `/campaigns/[id]` — pero esa ruta hoy no existe (404). Este spec define el detalle: puente entre la lista de campañas y los reportes de cada etapa.

Se diseña siguiendo el patrón establecido por DEV-52 `/reports/[id]` (server component + sections modulares + apiFetch SSR + tenant scoping en la view).

## 2. Objetivo

Usuario viewer (Balanz) autenticado puede entrar desde `/campaigns`, abrir una campaña, ver su header (nombre, estado, período, brief), ver sus etapas (stages) como timeline con la lista de reportes publicados de cada una, y clickear cualquier reporte para ir a `/reports/[id]`. Cross-tenant devuelve 404.

Out of scope (tickets separados):
- Edición de campaña → admin Django.
- Métricas agregadas por campaña → DEV-81 (Someday).
- Preview de reportes en DRAFT para admin → DEV-104.
- Branding por cliente (colores/logo) → ticket aparte.

## 3. Arquitectura

### Backend
- Nuevo `CampaignDetailSerializer` en `backend/apps/campaigns/serializers.py` — extiende `CampaignListSerializer` agregando `stages_with_reports` (reemplaza el `stages` simple cuando es detail).
- Nuevo `StageWithReportsSerializer` — emite `{id, order, kind, name, description, start_date, end_date, reports}` donde `reports` es lista de `CampaignReportRowSerializer`.
- Nuevo `CampaignReportRowSerializer` — emite `{id, title, display_title, kind, period_start, period_end, published_at}`. Mínimo necesario para renderizar una row clickeable; no duplica el payload de `/api/reports/<id>/`.
- `CampaignViewSet` pasa a usar `get_serializer_class()`: `list`/default → `CampaignListSerializer`, `retrieve` → `CampaignDetailSerializer`.
- Queryset de retrieve: `Campaign.objects.select_related("brand").prefetch_related(Prefetch("stages", queryset=Stage.objects.order_by("order").prefetch_related(Prefetch("reports", queryset=Report.objects.filter(status=Report.Status.PUBLISHED).order_by("-published_at")))))` + filtro `brand__client_id=request.user.client_id`. Unknown/cross-tenant → DRF `get_object_or_404` → 404. No 403 — no queremos leak de existencia.
- Log `campaign_detail_served` con `campaign_id`, `client_id`, `user_id`. Log `campaign_detail_access_denied` con `campaign_id`, `user_id`, `reason` (espejo de `ReportDetailView`).

### Frontend
- Nueva ruta `frontend/app/campaigns/[id]/page.tsx` — server component.
- Sections modulares en `frontend/app/campaigns/[id]/sections/`:
  - `CampaignHeader.tsx` — eyebrow, h1, pill estado, período, brief.
  - `StagesTimeline.tsx` — container, maps stages → `StageBlock`. Empty global si 0 stages.
  - `StageBlock.tsx` — 1 stage: nombre, período, descripción, lista de reportes (o empty state).
- Tipos nuevos en `frontend/lib/api.ts`: `CampaignReportRowDto`, `StageWithReportsDto`, `CampaignDetailDto`.
- No se introducen nuevos componentes cross-feature — breadcrumb y top bar se reutilizan del patrón actual.

### Complejidad y documentación (dim 4)

Presupuesto de tamaño por archivo:
- `page.tsx` ≤ 60 líneas.
- Cada section (`CampaignHeader`, `StagesTimeline`, `StageBlock`) ≤ 120 líneas. Si alguna supera 200, dividir (ej. mover a sub-componente `ReportRow`).
- `CampaignDetailSerializer` + helpers ≤ 80 líneas en `serializers.py`. Si `serializers.py` total supera 300, dividir por archivo (`serializers/campaign_list.py` + `serializers/campaign_detail.py`).
- `views.py` de campaigns ≤ 150 líneas. Si crece, mover viewsets a archivos separados.

Documentación de interfaces públicas:
- JSDoc en tipos exportados de `frontend/lib/api.ts` (qué representa cada campo, si es opcional).
- Docstring Python en `CampaignDetailSerializer` describiendo la shape nested y la razón del prefetch explícito (evitar N+1).
- `README.md` sección "Rutas del portal" incluye `/campaigns/[id]` + una línea descriptiva.

### Patterns aplicados (dim 6)

- **Serializer polimórfico por acción** (`get_serializer_class`): patrón estándar DRF. Justificado: list y detail tienen shape distinta y queremos evitar pagar el prefetch de reports en listados.
- **Presentational components**: sections son server components puros — reciben props, retornan JSX, no tienen estado ni efectos. Evita el antipattern "god component".
- **No circular deps**: sections importan tipos de `@/lib/api` y utilidades de `@/lib/format`. No importan de `page.tsx`. No hay inheritance; composición vía children-through-props.

## 4. Contratos de datos

### DTOs (frontend/lib/api.ts)
```ts
export type CampaignReportRowDto = {
  id: number;
  title: string;
  display_title: string;
  kind: "INFLUENCER" | "GENERAL" | "QUINCENAL" | "MENSUAL" | "CIERRE_ETAPA";
  period_start: string;      // ISO date
  period_end: string;        // ISO date
  published_at: string;      // ISO datetime (never null — PUBLISHED only)
};

export type StageWithReportsDto = {
  id: number;
  order: number;
  kind: "AWARENESS" | "EDUCATION" | "VALIDATION" | "CONVERSION" | "ONGOING" | "OTHER";
  name: string;
  description: string;       // may be empty string
  start_date: string | null; // ISO date
  end_date: string | null;   // ISO date
  reports: CampaignReportRowDto[]; // may be empty array
};

export type CampaignDetailDto = Omit<CampaignDto, "stages"> & {
  stages_with_reports: StageWithReportsDto[]; // may be empty array
};
```

Diseño explícito: `reports` y `stages_with_reports` son siempre arrays (nunca null) — front no debe defender `?? []`.

### JSON de ejemplo
```json
{
  "id": 1,
  "brand_name": "Balanz",
  "name": "Semillero 2026",
  "brief": "Primer trimestre de awareness educacional.",
  "status": "ACTIVE",
  "start_date": "2026-02-01",
  "end_date": null,
  "is_ongoing_operation": false,
  "stages_with_reports": [
    {
      "id": 10,
      "order": 1,
      "kind": "AWARENESS",
      "name": "Etapa 1 — Awareness",
      "description": "Arrancamos con contenido de validación social.",
      "start_date": "2026-02-01",
      "end_date": "2026-03-31",
      "reports": [
        {
          "id": 3,
          "title": "Reporte mensual · marzo",
          "display_title": "marzo 2026",
          "kind": "MENSUAL",
          "period_start": "2026-03-01",
          "period_end": "2026-03-31",
          "published_at": "2026-04-05T10:00:00Z"
        }
      ]
    }
  ],
  "stage_count": 1,
  "published_report_count": 1,
  "last_published_at": "2026-04-05T10:00:00Z"
}
```

## 5. Comportamiento de UI

### Header
- Eyebrow: `Chirri Portal · {client.name} · campañas` (la palabra `campañas` es `<Link>` a `/campaigns`).
- h1 nombre campaña (font-display, lowercase, mismo treatment que DEV-52/DEV-79).
- Pill estado: verde mint "● ACTIVA" si `status=ACTIVE`, gris "● TERMINADA" si `FINISHED`, amarilla "● PAUSADA" si `PAUSED`.
- Subline: `formatPeriod(start_date, end_date, is_ongoing_operation)` al lado del pill.
- Brief completo como párrafo debajo. Si vacío → no se renderiza el `<p>`.

### StagesTimeline
- Si `stages_with_reports.length === 0`: card gris con texto "Esta campaña todavía no tiene etapas publicadas".
- Si ≥1 stage: `<ol>` renderizado verticalmente con numeración visible (1/2/3/…) a la izquierda, `<StageBlock>` a la derecha.

### StageBlock
- h3 nombre stage (font-display, lowercase).
- Período: `formatPeriod(start_date, end_date, false)` — `is_ongoing_operation` siempre false a nivel stage.
- `description` como párrafo si no está vacía.
- Lista de reports:
  - Si `reports.length === 0`: texto gris "Esta etapa todavía no tiene reportes publicados".
  - Si ≥1: `<ul>` donde cada `<li>` es un `<Link href="/reports/{id}">` con:
    - Título: `display_title`
    - Pill kind pequeña (QUINCENAL/MENSUAL/CIERRE DE ETAPA/GENERAL/INFLUENCER)
    - Fecha: `formatReportDate(published_at)` a la derecha
    - Hover: highlight del row

### Estados de error
- Backend 404 → Next `notFound()` → página 404 de Next.
- Backend 401/otros → `throw err` (propaga a error boundary de Next — mismo patrón que DEV-52).
- Usuario sin `client_id` → backend retorna queryset vacío → `get_object_or_404` → 404.

## 6. Tests

### Backend (pytest)
Archivo nuevo: `backend/apps/campaigns/tests/test_detail.py`.
1. `test_returns_campaign_with_nested_stages_and_reports` — seed con 1 campaña · 2 stages · reportes PUBLISHED → response tiene ambas stages con sus reports.
2. `test_filters_draft_reports_from_stage_reports` — seed con 1 DRAFT en una stage → la stage aparece pero sin ese report.
3. `test_cross_tenant_returns_404` — cliente B pide campaña que pertenece a cliente A → 404.
4. `test_unauthenticated_returns_401`.
5. `test_user_without_client_returns_404`.
6. `test_empty_stages_returns_empty_array` — campaña sin stages → `stages_with_reports: []` (no 500).
7. `test_stage_with_no_published_reports_has_empty_reports_array` — stage sin reports published → `reports: []`.
8. `test_prefetch_avoids_n_plus_1` — `django_assert_num_queries` ≤ 6 (auth + scope + campaign + brand + stages + reports).

### E2E Playwright
Archivo nuevo: `frontend/tests/campaigns.spec.ts` (o append al existente de campaigns si ya hay).
1. `campaign detail happy path` — login → `/campaigns` → click primera ACTIVA → URL matches `/campaigns/\d+$` → h1 visible, brand name visible, ≥1 stage visible, ≥1 report link visible, 0 console errors.
2. `report row navigates to report page` — click primer report → URL `/reports/\d+$` → h1 del reporte visible.
3. `unknown campaign id returns 404` — GET `/campaigns/999999` → Next 404 page.

### Testability (dim 9)

- Backend serializer recibe instance via DRF (inyección estándar), no instancia modelos dentro del método. Los tests usan `APIClient` + factories/seed — sin mocks de DB (política de proyecto: integration tests contra Postgres real).
- Frontend sections son puras (props → JSX). Testables por inspección de markup en Playwright sin necesidad de mocks. No hay hooks que requieran `render()` de testing-library para este ticket.
- `apiFetch` es el único side-effect I/O del server component; se mockea via Playwright network interception si hiciera falta para tests aislados (no se necesita en este ticket — E2E full stack alcanza).

### Frontend quality (dim 11)

- **Design tokens**: colores vía `var(--chirri-*)` (pink, black, muted, mint, mint-deep, yellow-soft). Tipografía vía clase `font-display`. Pills vía `.pill`, `.pill-mint`, `.pill-white`, `.status-approved`. Sin hex hardcodeado.
- **Semantic HTML**: `<main>`, `<nav>` para breadcrumb, `<ol>` para timeline de stages (hay orden), `<ul>` para reports dentro de cada stage, `<h1>` para nombre campaña, `<h3>` para nombres de stage.
- **Accesibilidad**:
  - Links de reports usan `<Link>` (anchor real, keyboard navigable).
  - Pill de estado incluye `aria-label="Estado: activa"` porque el `●` es decorativo.
  - `notFound()` devuelve la page 404 estándar de Next (ya accesible).
  - Contraste: texto negro sobre pink ≥ 7:1 (ya validado en DEV-79).
- **Performance**: sin imágenes nuevas, sin bundles client nuevos. Todo server-rendered. No se necesita virtualization — máximo esperado: ~5 stages × ~10 reports = 50 rows.
- **State management**: no hay estado — 100% server component. No Context, no Zustand, no hooks.
- **Responsive**: `.page` class ya tiene max-width y paddings responsivos. Grid del StageBlock: flex-column en mobile (default), posibles columnas en desktop vía media query si la copy lo justifica — pero por YAGNI, mantener flex-column siempre en v1.
- **i18n**: todos los strings en español hardcoded (consistente con el resto del portal; i18n es un ticket futuro no-Chirri).

## 7. Principios aplicados

- **P2 SRP**: cada section tiene una responsabilidad (header ≠ timeline ≠ stage ≠ report row).
- **P3 DRY**: reutiliza `formatPeriod`, `formatReportDate`, `apiFetch`, `getCurrentUser`, `TopBar`. No duplica el tipo `Network`/`ReportDto`.
- **P5 DIP**: page recibe data via `apiFetch`, no importa del backend directo.
- **P6 Minimal Surface Area**: ningún hook nuevo, ningún client component, ningún context global. Solo 3 archivos de sections + tipos.
- **P9 Fail Fast**: tenant scoping duro; cross-tenant → 404 inmediato.
- **P10 Simplicity**: un solo endpoint retrieve, un solo serializer detail, un solo fetch SSR.

## 8. Observabilidad

- Log `campaign_detail_served` en view exitosa con `campaign_id`, `client_id`, `user_id`.
- Log `campaign_detail_access_denied` en 404 con `campaign_id`, `user_id`, `reason`.
- Log frontend `campaigns_detail_fetch_failed` en try/catch (igual a DEV-52).
- No métricas nuevas — queries DB se cubren por test de N+1.

## 9. Seguridad

- Auth: DRF `IsAuthenticated` + JWT via cookie → backend (mismo flujo que DEV-52).
- Scoping: hard filter por `brand__client_id=request.user.client_id` en `get_queryset`. Usuario sin `client_id` ve `Campaign.objects.none()`.
- 404 vs 403: cross-tenant y unknown ambos → 404, para no leak existencia.
- Input validation: el id llega como path param; DRF lo convierte a int o devuelve 404. Sin body input.
- No secrets nuevos, no variables de entorno nuevas.

## 9.5 Git health (dim 8)

- **Ownership**: `@dzacharias` como owner del ticket. Review: opt-in (repo de 1-2 personas). Si entra un segundo dev, agregar `CODEOWNERS` entry para `backend/apps/campaigns/` + `frontend/app/campaigns/`.
- **Commit strategy**: atomic commits, uno por task del plan. Mensaje en conventional commits (`feat:`, `test:`, `docs:`, `refactor:`). Cada commit pasa pytest + lint.
- **Branch**: commits directo a `development` (política del proyecto según CLAUDE.md — `development` es branch de deploy; `main` es production). Sin PR forzado.
- **No bottleneck de conocimiento**: spec + plan quedan en el repo como documentación permanente del feature. Cualquier dev nuevo puede retomar leyendo `docs/superpowers/specs/2026-04-20-campaign-detail-design.md` + código.

## 10. CI/CD (pipeline 5 etapas)

1. **PR gate** (`.github/workflows/test.yml`): lint (ruff + eslint) + typecheck (mypy + tsc) + unit tests (pytest backend + jest/tsc frontend) + E2E smoke Playwright. Required check para merge a `main` y `development`.
2. **Build**: SHA-pinned Docker images para backend + frontend vía deploy.yml. Tag: `${{ github.sha }}`, nunca `:latest`.
3. **Branch → env mapping**:
   - `development` → staging/prod Hetzner (según política del proyecto; actualmente deploy.yml escucha push a `development`).
   - `main` → reservado para production-ready cuts (no deploy automático hoy; manual merge desde `development`).
4. **Post-deploy smoke** (`deploy.yml` job `post_deploy_smoke`): corre Playwright con `PLAYWRIGHT_BASE_URL=${{ secrets.DEPLOY_URL }}` contra la URL deployada. Filtro: `--grep "Report viewer|Home smoke|Campaign detail"` (actualizar el grep actual para incluir el nuevo spec). Curl `/api/health/` primero como precheck.
5. **Rollback**: `git revert <merge-commit>` en `development` → push → deploy automático revierte a la imagen anterior (las imágenes SHA-pinned en Hetzner registry quedan disponibles). Ver sección 12.

Secrets usados: `DEPLOY_URL`, credenciales SSH Hetzner (ya existentes). No se introducen secrets nuevos — `docs/ENV.md` no cambia.

No hay cambios de infra.

## 11. Repo hygiene

- Al finalizar la implementación: archivar spec en `docs/superpowers/specs/` con `Status: Done — 2026-04-20`, mover plan de `docs/superpowers/plans/` a `docs/superpowers/plans/completed/`.
- Actualizar `README.md` agregando `/campaigns/[id]` a la sección "Rutas del portal".
- No se crean archivos de estado temporarios. No hay deprecated paths.

## 12. Rollback

Feature aislada: ninguna migración, ningún cambio breaking en endpoints existentes (`CampaignListSerializer` intacto). Rollback = `git revert` del merge commit → deploy. Los clientes que ya hayan cacheado la URL `/campaigns/[id]` ven 404 hasta re-deploy, consistente con comportamiento previo.
