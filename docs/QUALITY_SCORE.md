# Quality Score

**Last scan:** 2026-04-23 (post DEV-116 typed blocks refactor)
**Scanned domains:** `backend/apps/campaigns`, `frontend/app/campaigns`, `backend/apps/reports`, `frontend/app/reports`
**Overall grade (scanned):** B+
**Previous grade:** B
**Trending:** ↑

## Domain Grades

| Domain | Tests | DRY | Boundaries | Docs | Principles | Patterns | Security | Git | Testability | Observability | Frontend | Hygiene | CI/CD | Overall |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| backend/apps/campaigns | A | A | A | A | A | A | A | A | A | B | — | A | B | **B+** |
| frontend/app/campaigns | B | C | A | A | A | A | A | A | A | B | C | A | B | **B** |
| backend/apps/reports | A | A | A | A | A | A | A | A | A | B | — | A | B | **A-** |
| frontend/app/reports | A | C | A | A | A | A | A | A | A | B | C | A | B | **B** |

All four scanned domains pass the entropy-driven quality gate (≥ B). No entropy-fix cycle required.

**DEV-116 impact:** `backend/apps/reports` rose from B to A- after the typed blocks refactor. Key drivers:
- Eliminated the `ReportBlock.config` JSONField + imperative validators; replaced with typed Django models (constraints enforced at DB).
- Eliminated `services/aggregations.py` (dead cross-report rollups); report is now a pure snapshot.
- Admin UX no longer requires JSON editing (`django-polymorphic` typed forms).
- Dependency audit process captured in `docs/DEPENDENCIES.md`.
- New tenant scoping regression test (`test_tenant_scoping.py`) guards the CLAUDE.md gotcha explicitly.

Overall rises from B to B+ because backend/reports moved up while frontend grades stayed (design-system debt still open).

## Detailed Findings

### backend/apps/campaigns

Clean domain. No principle violations, no DRY duplications, no anti-patterns, no
security gaps. The two B grades are the only gaps worth noting:

#### Observability (B)

| Category | File | Line | Issue | Fix |
|----------|------|------|-------|-----|
| Request tracing | backend/apps/campaigns/ | — | No correlation ID propagated to logs (repo-wide gap, not domain-specific) | Add request-id middleware at the project level |
| Metrics | backend/apps/campaigns/views.py | — | `campaign_detail_served` / `campaign_detail_access_denied` logged, but no counters for serve/deny rates | Consider Prometheus counters when observability stack lands |
| Structured logging on list action | backend/apps/campaigns/views.py | 22 | `get_queryset` for `list` has no access log, only `retrieve` does | Add `campaigns_list_served` log mirroring `retrieve` |

#### CI/CD (B, repo-level)

| Stage | File | Issue | Action |
|-------|------|-------|--------|
| 5 (Rollback) | README.md | Rollback section exists (added in DEV-52); Hetzner-specific one-command recipe could be tighter | Optional: extract rollback to `docs/RUNBOOK.md` with SHA-pinned example |

### frontend/app/campaigns

Good architecture — section decomposition, semantic HTML, keyboard a11y, server
components. Three dimensions short of A:

#### DRY (C)

| Files | Lines | What's duplicated |
|-------|-------|-------------------|
| `CampaignCardBig.tsx`, `CampaignRowArchived.tsx` | 18-26, 10-21 | Identical `formatPeriod(...)` + `lastReport = last_published_at ? formatReportDate(...) : null` pre-computation block |
| `app/campaigns/page.tsx`, `[id]/sections/CampaignHeader.tsx` | 40-49, 36-44 | Identical display h1 style (fontSize 96, lineHeight 0.9, letterSpacing -0.03em, textTransform lowercase, margin "8px 0 0") — signals missing `.display-xl` utility class |
| `CampaignCardBig.tsx` vs `CampaignHeader.tsx` | 48, 5-12 | Status rendering is inconsistent: card hardcodes `● ACTIVA`, detail uses `STATUS_PILL` lookup. Both should live in one place. |

**Fix:** Extract a `lib/campaign-view.ts` with `buildCampaignViewModel(c)` returning `{ period, lastReport, statusPill }`. Extract `.display-xl` class to `globals.css`. This is a follow-up refactor, not a blocker.

#### Observability (B)

| Category | File | Line | Issue | Fix |
|----------|------|------|-------|-----|
| Error logging | `app/campaigns/[id]/page.tsx` | 23 | `console.error` with unstructured `{ id, err }` — acceptable for server component but not captured by any log pipeline yet | Align with backend when Sentry/structured frontend logging lands |

#### Frontend Quality (C)

| Category | File | Line | Issue | Fix |
|----------|------|------|-------|-----|
| Design tokens (spacing) | All 7 files | — | Padding / margin / gap are hardcoded pixel values (`padding: 36`, `gap: 20`, `marginBottom: 40`) — no spacing scale | Introduce CSS custom props `--space-1..--space-12` or Tailwind-style scale; migrate incrementally |
| Design tokens (typography) | All 7 files | — | Font sizes hardcoded (`fontSize: 96`, `64`, `48`, `40`, `36`, `24`, `16`, `15`, `14`, `13`, `12`, `11`) — no scale | Extract type scale (`display-xl`, `display-lg`, `h1`, `h3`, `body`, `caption`) into `globals.css` |
| Responsive design | `app/campaigns/page.tsx`, `CampaignCardBig.tsx`, `CampaignRowArchived.tsx`, `[id]/page.tsx` | — | `gridTemplateColumns: "1fr 200px 140px 140px 80px"` and `maxWidth: 720` with no media queries; mobile will break | Add breakpoint scale; make archived row stack on narrow viewports |
| Inline styles | All 7 files | — | Large inline `style={{ ... }}` objects throughout (60%+ of LOC). Harder to theme and audit. | Migrate sections progressively to CSS modules or utility classes once scale exists |

**Sub-category breakdown:** design-system C, component-architecture B, a11y A, performance A, state-management A, responsive/i18n C → avg 3.17 → **C**.

The a11y work is solid: semantic `<nav aria-label>`, `<header>`, `<ol>/<li>`, `aria-hidden` on decorative stage numbers, `<button>` / `<Link>` for interactive elements, keyboard navigation test covers Tab+Enter. Keep this baseline when adding the design system.

#### CI/CD (B, repo-level — same grade as backend)

See backend entry.

### backend/apps/reports

Solid domain. DEV-105 refactor landed cleanly: `ReportBlock` model with per-type
registry validator, `save()` → `full_clean()` as the fail-fast seam, `original_pdf`
FileField with size + mime validators mirroring the image path. Test-to-source
ratio ≈ 739 / 770 (≈ 1:1) across 13 test files.

#### What's working

- **Registry pattern** (`blocks/registry.py` + `blocks/schemas.py`): pure functions, each block type owns its config contract, registry lookup fails fast on unknown type. Schemas reject string truthiness (`has_comparison: "yes"`) explicitly.
- **Fail-fast on invalid data** (`models.py` lines 195-201): `ReportBlock.save()` calls `full_clean()` so `ReportBlock.objects.create(...)` with a bad config raises at the Python layer before DB. The comment explicitly notes `bulk_create` bypasses this — and `seed_demo` relies on that, which is the right trade-off for trusted seeds. Regression test in `test_report_block_model.py::test_unique_order_per_report`.
- **Tenant scoping** (`views.py` lines 54-66): scoping via `getattr(request.user, "client_id", None)` in `get_queryset`, returning 404 not 403 for cross-tenant / DRAFT — avoids existence leak. CLAUDE.md gotcha explicitly referenced in docstring.
- **204 for latest-empty** (`views.py` lines 17-41): docstring calls out why `Response(None)` was the old bug (`"Unexpected end of JSON input"` on the frontend). Regression covered in `test_reports_api.py`.
- **N+1 budget test** (`test_report_nplus1.py`): creates 20 blocks + 20 top_content + 10 onelink and asserts the detail endpoint runs ≤ 13 queries. Hard-fails if a row-scoped query slips in.
- **Query plan** (`views.py` lines 58-66): `select_related` for stage/campaign/brand + `prefetch_related("metrics","top_content","onelink","blocks")` — matches the serializer's use sites.
- **PDF + image validators** (`validators.py`): size (5MB image / 20MB pdf) + mime allowlist (rejects SVG and `application/octet-stream`). Covered by `test_pdf_validators.py` and `test_report_viewer_models.py`.

#### Observability (B)

| Category | File | Line | Issue | Fix |
|----------|------|------|-------|-----|
| Missing log on latest endpoint | backend/apps/reports/views.py | 17-41 | `LatestPublishedReportView` has no `logger.info/warning` for success, 204, or access — only `ReportDetailView` emits structured events | Mirror `report_served` in the `latest` happy path and `report_latest_empty` on the 204 branch |
| Request tracing | backend/apps/reports/ | — | No correlation ID across `report_served` events (repo-wide gap, not domain-specific) | Add request-id middleware at the project level (same finding as campaigns) |
| No counters | backend/apps/reports/views.py | — | Events are logged but there's no counter for serve / deny rates | Consider Prometheus counters when observability stack lands |

#### CI/CD (B, repo-level)

Same repo-level finding as campaigns — see entry above. Stage-5 rollback is
informal (re-push + `git reset --hard` in the Hetzner workdir).

### frontend/app/reports

Clean dispatcher architecture — `BlockRenderer` looks up the component by `block.type`
from a typed `BLOCK_COMPONENTS` record, unknown types console.warn and return null.
Every block defensively validates its own config and returns null on bad input
(defense-in-depth since `seed_demo` uses `bulk_create` which skips `full_clean`).
SSR server components throughout — no client JS in the reports tree.

#### What's working

- **Dispatcher pattern** (`blocks/BlockRenderer.tsx`): typed `BLOCK_COMPONENTS as const`, null-safe dispatch, logs `unknown_block_type`. Matches the backend registry shape.
- **Defensive rendering**: each of the 6 block components validates its config shape in-component (`cfg.columns` ∈ {1,2,3}, `cfg.kind` ∈ {POST,CREATOR}, etc.) and returns null + `console.warn("invalid_X_config", block.id, cfg)` on bad input.
- **A11y**: semantic `<table>` / `<thead>` / `<th scope="col">` in MetricsTableBlock + AttributionTableBlock; `<dl>/<dt>/<dd>` in ContentCard; `role="img"` + `aria-label` on BarChartMini SVG; `aria-hidden` on decorative placeholder; `aria-label="Descargar PDF original"` on the header download link. Img alt falls back `caption → "Post de ${handle}" → "Contenido destacado"`.
- **Test coverage**: `report-blocks.spec.ts` asserts 10 expected pill titles appear in DOM order + verifies the YoY pill correctly does NOT appear (seed has no prior-year data) + PDF download absent when `original_pdf` empty. `reports.spec.ts` covers smoke / 404 / cross-tenant-404 (skipped awaiting seed).
- **Types match backend**: `ReportBlockType` union in `lib/api.ts` mirrors `ReportBlock.Type.choices` exactly.

#### DRY (C)

| Files | Lines | What's duplicated |
|-------|-------|-------------------|
| `MetricsTableBlock.tsx`, `AttributionTableBlock.tsx` | 28-52, 68-76, 83-106 & 24-56 | Identical `<table style={{width:"100%", borderCollapse:"collapse", marginTop:12}}>` scaffolding; `padding: "8px 12px"` literal appears 25× across 2 files; `borderTop: "1px solid rgba(0,0,0,0.05)"` row divider duplicated 4× |
| All 6 block files + ConclusionsSection | 22, 28, 36, 76, 129, 7 | `<section style={{ marginBottom: 48 }}>` repeated in every block; `<section style={{ marginBottom: 40, ... }}>` in HeaderSection + IntroText — signals missing `BlockSection` wrapper |
| All 6 block files | 13, 15, 26, 27, 68, 117 | Identical guard + log pattern (`if (!cfg ...) { console.warn("invalid_X_config", block.id, cfg); return null; }`) — could be a `validateConfigOrWarn(type, schema, cfg, blockId)` helper |

**Fix:** Extract `app/reports/[id]/blocks/_primitives/DataTable.tsx` (header + rows props) and `BlockSection.tsx` (pill title + section spacing). Extract a `validateConfig(schema, cfg, blockId)` helper. 40-60 line refactor; not a blocker.

#### Observability (B)

| Category | File | Line | Issue | Fix |
|----------|------|------|-------|-----|
| Error logging | `app/reports/[id]/page.tsx` | 21 | `console.error("reports_fetch_failed", { id, err })` — structured key, acceptable for server component but not captured by any log pipeline yet | Align with backend when Sentry/structured frontend logging lands (same finding as campaigns) |
| Warning logging | All 6 block components | 13, 15, 26, 27, 68, 117 | `console.warn("invalid_X_config", block.id, cfg)` — consistent key shape, good; but the `cfg` payload may contain PII or large blobs | When log pipeline lands, sanitise `cfg` before shipping |

#### Frontend Quality (C)

| Category | File | Line | Issue | Fix |
|----------|------|------|-------|-----|
| Design tokens (spacing) | All 15 files | — | Hardcoded `marginBottom: 48`, `padding: "8px 12px"`, `gap: 16/24/32`, `padding: 16/20`, `marginTop: 8/12/16` — 78 fontSize/padding/margin/gap occurrences across 13 files; no scale | Same fix as campaigns: introduce `--space-1..--space-12` CSS custom props |
| Design tokens (typography) | All 15 files | — | Font sizes hardcoded (`fontSize: 72, 56, 22, 18, 14, 13, 12, 11`) — no scale | Same fix: extract `display-lg`, `h1`, `h3`, `body`, `caption` classes into `globals.css` |
| Hardcoded colors | `MetricsTableBlock.tsx`, `AttributionTableBlock.tsx` | 38, 68, 94 & 34, 45 | `rgba(0,0,0,0.05)` and `rgba(0,0,0,0.15)` hex-alpha literals instead of CSS vars — everything else in the tree correctly uses `var(--chirri-*)` | Extract `--chirri-table-divider` / `--chirri-table-divider-strong` |
| Responsive design | `MetricsTableBlock.tsx`, `AttributionTableBlock.tsx`, `TextImageBlock.tsx` | — | Tables set `width: 100%` with no `overflow-x: auto` wrapper — narrow viewports overflow horizontally. TextImageBlock `flexDirection: "row"` has no breakpoint to stack on mobile | Wrap tables in `<div style={{overflowX:"auto"}}>`; stack TextImageBlock below 640px |
| Inline styles | All 15 files | — | Inline `style={{...}}` objects dominate LOC (same pattern as campaigns). Harder to theme and audit. | Migrate to CSS modules once design tokens land |

**Sub-category breakdown:** design-system C, component-architecture A (dispatcher + small focused blocks, biggest is MetricsTableBlock at 134 LOC), a11y A, performance A (pure SSR, no client JS, inline SVG chart), state-management A, responsive/i18n C → avg ≈ 3.0 → **C**.

The a11y work is as good as campaigns: scope attributes on all table headers, proper `<dl>` for key/value pairs, ARIA on the SVG chart, semantic landmark sections, `aria-label` on PDF download link. Keep this baseline when the design system lands.

#### CI/CD (B, repo-level — same grade as backend)

See backend/campaigns entry. `deploy.yml` runs post-deploy smoke vs `DEPLOY_URL`
and matches on `Report viewer|Home smoke|Campaign detail`, so reports coverage
participates in stage-4.

## Tech Debt

| Type | Count | Prev |
|---|---|---|
| TODO | 0 | 0 |
| FIXME | 0 | 0 |
| HACK | 0 | 0 |

Zero markers in the scanned domains and zero repo-wide. DEV-105 introduced no
new debt markers.

## Top 5 Refactoring Priorities

1. **Design system tokens (frontend-wide)** — impact: high. Extract spacing + typography scales to `globals.css`, migrate `/campaigns`, `/campaigns/[id]`, and `/reports/[id]` (15 files, 78 hardcoded spacing occurrences) in one pass. Unblocks responsive design. Likely own ticket (DEV-TBD).
2. **Reports block primitives** — impact: medium. Extract `<BlockSection>` (pill + spacing) and `<DataTable>` (shared table scaffolding) — eliminates all three frontend/reports DRY findings and the `rgba(0,0,0,0.05)` color literals. ~60 lines.
3. **Responsive wrappers for report tables** — impact: medium. `MetricsTableBlock` and `AttributionTableBlock` overflow horizontally on mobile; wrap in `overflow-x:auto` container. One-line fix per block.
4. **Structured logging on `LatestPublishedReportView`** — impact: low. Mirror `report_served` / add `report_latest_empty` for the 204 branch — ~8 lines in `views.py`. Same fix flavour as campaigns `list`-action log gap.
5. **Request-id correlation middleware (repo-level)** — impact: low today, high once we have multiple services. Tie logs across backend + frontend + worker.

## History

| Date | Overall (scanned) | Trend |
|---|---|---|
| 2026-04-20 | B | — (first scan, campaigns only) |
| 2026-04-20 | B | = (reports domain added, same grade) |
| 2026-04-23 | B+ | ↑ (DEV-116: backend/reports B→A-, typed blocks refactor eliminates JSON config + aggregations) |
