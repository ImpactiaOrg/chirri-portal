# Quality Score

**Last scan:** 2026-04-20
**Scanned domains:** `backend/apps/campaigns`, `frontend/app/campaigns`
**Overall grade (scanned):** B
**Previous grade:** — (first scan)
**Trending:** —

## Domain Grades

| Domain | Tests | DRY | Boundaries | Docs | Principles | Patterns | Security | Git | Testability | Observability | Frontend | Hygiene | CI/CD | Overall |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| backend/apps/campaigns | A | A | A | A | A | A | A | A | A | B | — | A | B | **B** |
| frontend/app/campaigns | B | C | A | A | A | A | A | A | A | B | C | A | B | **B** |

Both scanned domains pass the entropy-driven quality gate (≥ B). No entropy-fix cycle required.

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

## Tech Debt

| Type | Count | Prev |
|---|---|---|
| TODO | 0 | — |
| FIXME | 0 | — |
| HACK | 0 | — |

Zero markers in the scanned domains and zero repo-wide. Notable: no debt was
introduced by DEV-52 or DEV-86.

## Top 5 Refactoring Priorities

1. **Design system tokens (frontend-wide)** — impact: high. Extract spacing + typography scales to `globals.css`, migrate `/campaigns`, `/campaigns/[id]`, and `/reports/[id]` in one pass. Unblocks responsive design. Likely own ticket (DEV-TBD).
2. **Campaign view model extraction** — impact: medium. `lib/campaign-view.ts` with `buildCampaignViewModel(c)` eliminates the three DRY findings above in a ~40 line module.
3. **Responsive breakpoints for `/campaigns` archived rows** — impact: medium. `gridTemplateColumns: "1fr 200px 140px 140px 80px"` breaks on narrow viewports; stack vertically below 768px.
4. **List-action structured logging** — impact: low. Mirror `campaign_detail_served` for `list` action — ~5 lines in `CampaignViewSet.list()`.
5. **Request-id correlation middleware (repo-level)** — impact: low for campaigns, high once we have multiple services. Tie logs across backend + frontend + worker.

## History

| Date | Overall (scanned) | Trend |
|---|---|---|
| 2026-04-20 | B | — (first scan) |
