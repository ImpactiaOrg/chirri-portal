---
Ticket: DEV-86
Status: Design
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

## 10. CI/CD

- `test.yml` (backend + frontend + e2e-smoke) cubre los nuevos tests automáticamente (pytest corre todo `backend/apps/*/tests`, Playwright corre todos los `*.spec.ts` bajo `frontend/tests`).
- `deploy.yml` post_deploy_smoke ya corre `--grep "Report viewer|Home smoke"` — actualizar para incluir `|Campaign detail`.
- No hay cambios de infra ni secrets.

## 11. Repo hygiene

- Al finalizar la implementación: archivar spec en `docs/superpowers/specs/` con `Status: Done — 2026-04-20`, mover plan de `docs/superpowers/plans/` a `docs/superpowers/plans/completed/`.
- Actualizar `README.md` agregando `/campaigns/[id]` a la sección "Rutas del portal".
- No se crean archivos de estado temporarios. No hay deprecated paths.

## 12. Rollback

Feature aislada: ninguna migración, ningún cambio breaking en endpoints existentes (`CampaignListSerializer` intacto). Rollback = `git revert` del merge commit → deploy. Los clientes que ya hayan cacheado la URL `/campaigns/[id]` ven 404 hasta re-deploy, consistente con comportamiento previo.
