# `/campaigns` list Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implementar la pantalla `/campaigns` con la lista de activas (cards grandes rotando 3 colores) y archivadas (rows compactas), sin cambios de backend.

**Architecture:** Server Component en `frontend/app/campaigns/page.tsx` que hace SSR del fetch a `/api/campaigns/`, splitea por status, y renderiza dos secciones con sub-componentes presentacionales (también server). Funciones puras de formateo de fecha en `frontend/lib/format.ts`, compartidas con `home/page.tsx`.

**Tech Stack:** Next.js 14 App Router (server components), TypeScript, Playwright E2E.

**Spec:** `docs/superpowers/specs/2026-04-20-campaigns-list-design.md`.

**Ticket:** DEV-79 (crear al inicio).

**Testing note:** Frontend no tiene infra de unit tests (deuda asumida, DEV-81 follow-up). Cobertura: `tsc --noEmit` para types + Playwright E2E para comportamiento + verificación manual en browser.

---

### Task 1: Crear ticket DEV-79 en Linear y moverlo a In Progress

**Files:**
- (none — Linear only)

- [ ] **Step 1: Buscar el project de Chirri Portal y el usuario Daniel en Linear**

Usar `mcp__linear__list_projects` con query "Chirri" y `mcp__linear__list_users` con query "Daniel".

- [ ] **Step 2: Crear el issue DEV-79**

Título: `/campaigns — lista de campañas activas y archivadas`

Body (markdown, newlines reales, sin `\n`):

```
Implementar la pantalla /campaigns con activas (cards grandes) y archivadas (rows).

Spec: docs/superpowers/specs/2026-04-20-campaigns-list-design.md

## Alcance
- Server component en app/campaigns/page.tsx
- CampaignCardBig (activas, paleta mint/peach/lilac rotativa)
- CampaignRowArchived (terminadas)
- lib/format.ts con formatPeriod + formatReportDate
- DRY: migrar MONTHS_ES y formatMonthYear de home/page.tsx
- E2E smoke extendido

## Fuera de scope
- Detalle /campaigns/[id] (ticket aparte)
- Métricas agregadas por campaña (DEV-80)
- Infra de unit tests frontend (DEV-81)

## DoD
Ver spec sección Definition of Done.
```

Asignar a Daniel. Estado: In Progress.

- [ ] **Step 3: Confirmar que el ticket aparece en Linear con estado In Progress**

Anotar el ID exacto del issue (e.g., `IMP-79` o `DEV-79` según el prefijo del team).

---

### Task 2: Crear `frontend/lib/format.ts`

**Files:**
- Create: `frontend/lib/format.ts`
- Modify (en Task 3): `frontend/app/home/page.tsx` — solo para importar desde `lib/format.ts` y quitar definiciones locales duplicadas.

- [ ] **Step 1: Escribir `frontend/lib/format.ts`**

```ts
export const MONTHS_ES = [
  "enero", "febrero", "marzo", "abril", "mayo", "junio",
  "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre",
];

export const MONTHS_ES_SHORT = [
  "ene", "feb", "mar", "abr", "may", "jun",
  "jul", "ago", "sep", "oct", "nov", "dic",
];

export function formatMonthYear(iso: string): { month: string; year: string } {
  const d = new Date(iso);
  return { month: MONTHS_ES[d.getUTCMonth()], year: String(d.getUTCFullYear()) };
}

/**
 * Formatea un período de campaña en español.
 *
 * Reglas:
 *  - is_ongoing_operation=true → "operación continua"
 *  - sin end_date            → "feb 2026 – en curso"
 *  - mismo año               → "feb – dic 2025"
 *  - cruza año               → "feb 2024 – dic 2025"
 *  - sin start_date          → "—" (defensivo)
 */
export function formatPeriod(
  startDate: string | null,
  endDate: string | null,
  isOngoing: boolean,
): string {
  if (isOngoing) return "operación continua";
  if (!startDate) return "—";

  const start = new Date(startDate);
  const startMonth = MONTHS_ES_SHORT[start.getUTCMonth()];
  const startYear = start.getUTCFullYear();

  if (!endDate) {
    return `${startMonth} ${startYear} – en curso`;
  }

  const end = new Date(endDate);
  const endMonth = MONTHS_ES_SHORT[end.getUTCMonth()];
  const endYear = end.getUTCFullYear();

  if (startYear === endYear) {
    return `${startMonth} – ${endMonth} ${endYear}`;
  }
  return `${startMonth} ${startYear} – ${endMonth} ${endYear}`;
}

/**
 * Formatea una fecha ISO de reporte publicado.
 *  - "2026-04-15T10:23:00Z" → "15 abr 2026"
 *  - null                    → "sin reportes"
 */
export function formatReportDate(iso: string | null): string {
  if (!iso) return "sin reportes";
  const d = new Date(iso);
  const day = d.getUTCDate();
  const month = MONTHS_ES_SHORT[d.getUTCMonth()];
  const year = d.getUTCFullYear();
  return `${day} ${month} ${year}`;
}
```

- [ ] **Step 2: Typecheck**

Run: `docker compose exec -T frontend npm run typecheck`
Expected: PASS sin errores.

Si el container no está corriendo: `docker compose up -d frontend` primero.

- [ ] **Step 3: Commit**

```bash
git add frontend/lib/format.ts
git commit -m "feat(campaigns): add formatPeriod/formatReportDate helpers (DEV-79)"
```

---

### Task 3: Migrar `home/page.tsx` a usar `lib/format.ts` (DRY)

**Files:**
- Modify: `frontend/app/home/page.tsx` (líneas 7-20 aprox: `MONTHS_ES`, `formatMonthYear`).

- [ ] **Step 1: Leer el archivo actual**

Read `frontend/app/home/page.tsx` y confirmar que `MONTHS_ES` y `formatMonthYear` viven en las líneas 7-20.

- [ ] **Step 2: Reemplazar definiciones locales por import**

Viejo (al tope del archivo, después del `import` de `TopBar`):

```ts
const MONTHS_ES = [
  "enero", "febrero", "marzo", "abril", "mayo", "junio",
  "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre",
];

function firstName(full: string, fallback: string): string {
  const first = full.trim().split(/\s+/)[0];
  return (first || fallback).toLowerCase();
}

function formatMonthYear(iso: string): { month: string; year: string } {
  const d = new Date(iso);
  return { month: MONTHS_ES[d.getUTCMonth()], year: String(d.getUTCFullYear()) };
}
```

Nuevo:

```ts
import { MONTHS_ES, formatMonthYear } from "@/lib/format";

function firstName(full: string, fallback: string): string {
  const first = full.trim().split(/\s+/)[0];
  return (first || fallback).toLowerCase();
}
```

(Se mantiene `firstName` local por ahora — es chico, específico de home, y moverlo no es parte de este ticket. Si DEV-81 quiere extraerlo, que lo haga ahí.)

- [ ] **Step 3: Typecheck + smoke test de home**

Run:
```bash
docker compose exec -T frontend npm run typecheck
```
Expected: PASS.

Run:
```bash
npm run test:e2e:smoke
```
Expected: PASS (el smoke de home sigue en verde — no cambia nada de comportamiento).

- [ ] **Step 4: Commit**

```bash
git add frontend/app/home/page.tsx
git commit -m "refactor(home): import MONTHS_ES/formatMonthYear from lib/format (DEV-79)"
```

---

### Task 4: Crear `CampaignCardBig.tsx`

**Files:**
- Create: `frontend/app/campaigns/CampaignCardBig.tsx`

- [ ] **Step 1: Escribir el componente**

```tsx
import Link from "next/link";
import type { CampaignDto } from "@/lib/api";
import { formatPeriod, formatReportDate } from "@/lib/format";

const PALETTE = [
  "var(--chirri-mint)",
  "var(--chirri-peach)",
  "var(--chirri-lilac)",
];

type Props = {
  campaign: CampaignDto;
  colorIndex: number;
};

export default function CampaignCardBig({ campaign, colorIndex }: Props) {
  const color = PALETTE[colorIndex % PALETTE.length];
  const period = formatPeriod(
    campaign.start_date,
    campaign.end_date,
    campaign.is_ongoing_operation,
  );
  const lastReport = formatReportDate(campaign.last_published_at);
  const reportCount = campaign.published_report_count;

  return (
    <Link
      href={`/campaigns/${campaign.id}`}
      className="card-link"
      style={{
        background: color,
        border: "2.5px solid var(--chirri-black)",
        borderRadius: 22,
        padding: 36,
        boxShadow: "4px 4px 0 var(--chirri-black)",
        display: "grid",
        gridTemplateColumns: "1fr auto",
        gap: 40,
        alignItems: "end",
        textDecoration: "none",
        color: "inherit",
      }}
    >
      <div style={{ position: "relative" }}>
        <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 12 }}>
          <span className="status status-approved">● ACTIVA</span>
          <span style={{ fontSize: 12, fontWeight: 700 }}>{period}</span>
        </div>
        <h2
          className="font-display"
          style={{
            fontSize: 64,
            lineHeight: 0.88,
            letterSpacing: "-0.03em",
            margin: "0 0 10px",
            textTransform: "lowercase",
          }}
        >
          {campaign.name.toLowerCase()}
        </h2>
        <p style={{ fontSize: 15, maxWidth: 520, lineHeight: 1.5, fontWeight: 500 }}>
          {campaign.brief}
        </p>
        <div style={{ display: "flex", gap: 28, marginTop: 18, fontSize: 12, fontWeight: 700 }}>
          <span>{reportCount} reportes</span>
          <span>· último {lastReport}</span>
        </div>
      </div>
      <div style={{ textAlign: "right" }}>
        <span className="btn btn-primary">Abrir →</span>
      </div>
    </Link>
  );
}
```

- [ ] **Step 2: Typecheck**

Run: `docker compose exec -T frontend npm run typecheck`
Expected: PASS.

- [ ] **Step 3: (sin commit todavía — commit junto con la row en Task 6)**

---

### Task 5: Crear `CampaignRowArchived.tsx`

**Files:**
- Create: `frontend/app/campaigns/CampaignRowArchived.tsx`

- [ ] **Step 1: Escribir el componente**

```tsx
import Link from "next/link";
import type { CampaignDto } from "@/lib/api";
import { formatPeriod, formatReportDate } from "@/lib/format";

type Props = {
  campaign: CampaignDto;
};

export default function CampaignRowArchived({ campaign }: Props) {
  const period = formatPeriod(
    campaign.start_date,
    campaign.end_date,
    campaign.is_ongoing_operation,
  );
  const lastReport = formatReportDate(campaign.last_published_at);
  const reportCount = campaign.published_report_count;
  const briefShort = campaign.brief.length > 80
    ? `${campaign.brief.slice(0, 80)}…`
    : campaign.brief;

  return (
    <Link
      href={`/campaigns/${campaign.id}`}
      className="card-link"
      style={{
        background: "white",
        border: "2px solid var(--chirri-black)",
        borderRadius: 14,
        padding: "16px 22px",
        boxShadow: "2px 2px 0 var(--chirri-black)",
        display: "grid",
        gridTemplateColumns: "1fr 200px 140px 140px 80px",
        alignItems: "center",
        gap: 20,
        textDecoration: "none",
        color: "inherit",
        opacity: 0.88,
      }}
    >
      <div>
        <div
          className="font-display"
          style={{ fontSize: 24, lineHeight: 1, textTransform: "lowercase" }}
        >
          {campaign.name.toLowerCase()}
        </div>
        <div
          style={{
            fontSize: 12,
            color: "var(--chirri-muted)",
            marginTop: 4,
            fontWeight: 500,
          }}
        >
          {briefShort}
        </div>
      </div>
      <div style={{ fontSize: 12, fontWeight: 700 }}>{period}</div>
      <div style={{ fontSize: 12, fontWeight: 700 }}>{reportCount} reportes</div>
      <div style={{ fontSize: 11, fontWeight: 600, color: "var(--chirri-muted)" }}>
        último {lastReport}
      </div>
      <div style={{ textAlign: "right", fontWeight: 800, fontSize: 12, textDecoration: "underline" }}>
        Abrir →
      </div>
    </Link>
  );
}
```

- [ ] **Step 2: Typecheck**

Run: `docker compose exec -T frontend npm run typecheck`
Expected: PASS.

- [ ] **Step 3: Commit los 2 componentes juntos**

```bash
git add frontend/app/campaigns/CampaignCardBig.tsx frontend/app/campaigns/CampaignRowArchived.tsx
git commit -m "feat(campaigns): add CampaignCardBig and CampaignRowArchived (DEV-79)"
```

---

### Task 6: Crear `frontend/app/campaigns/page.tsx`

**Files:**
- Create: `frontend/app/campaigns/page.tsx`

- [ ] **Step 1: Escribir la página**

```tsx
import { redirect } from "next/navigation";
import { apiFetch, type CampaignDto, type PagedResponse } from "@/lib/api";
import { getAccessToken, getCurrentUser } from "@/lib/auth";
import TopBar from "@/components/top-bar";
import CampaignCardBig from "./CampaignCardBig";
import CampaignRowArchived from "./CampaignRowArchived";

export default async function CampaignsPage() {
  const user = await getCurrentUser();
  if (!user) redirect("/login");

  const token = getAccessToken();

  let campaigns: CampaignDto[] = [];
  try {
    const res = await apiFetch<PagedResponse<CampaignDto> | CampaignDto[]>(
      "/api/campaigns/",
      { token },
    );
    campaigns = Array.isArray(res) ? res : res.results;
  } catch (err) {
    console.error("campaigns_fetch_failed", {
      url: "/api/campaigns/",
      error: err instanceof Error ? err.message : String(err),
      hasJwt: !!token,
    });
  }

  const active = campaigns.filter((c) => c.status === "ACTIVE");
  const archived = campaigns.filter((c) => c.status !== "ACTIVE");

  return (
    <>
      <TopBar user={user} active="campaigns" />
      <main className="page page-wide" style={{ background: "var(--chirri-pink)" }}>
        <section style={{ marginBottom: 40 }}>
          <div className="eyebrow">
            Chirri Portal · {user.client?.name ?? "—"}
          </div>
          <h1
            className="font-display"
            style={{
              fontSize: 96,
              lineHeight: 0.9,
              letterSpacing: "-0.03em",
              margin: "8px 0 0",
              textTransform: "lowercase",
            }}
          >
            campañas.
          </h1>
          <p
            style={{
              fontSize: 16,
              maxWidth: 620,
              marginTop: 14,
              lineHeight: 1.5,
              fontWeight: 500,
            }}
          >
            Las activas arriba. Abajo quedan archivadas las terminadas — podés abrir cualquiera para ver el cierre y los reportes de esa etapa.
          </p>
        </section>

        <section style={{ marginBottom: 48 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 14, marginBottom: 20 }}>
            <span className="pill pill-mint">ACTIVAS · {active.length}</span>
          </div>
          <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
            {active.map((c, i) => (
              <CampaignCardBig key={c.id} campaign={c} colorIndex={i} />
            ))}
          </div>
        </section>

        <section
          style={{
            borderTop: "3px solid var(--chirri-black)",
            paddingTop: 36,
            marginTop: 48,
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: 14, marginBottom: 20 }}>
            <span className="pill pill-white">ARCHIVO · {archived.length}</span>
            <span style={{ fontSize: 12, fontWeight: 600, color: "var(--chirri-muted)" }}>
              Campañas terminadas
            </span>
          </div>
          <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
            {archived.map((c) => (
              <CampaignRowArchived key={c.id} campaign={c} />
            ))}
          </div>
        </section>
      </main>
    </>
  );
}
```

- [ ] **Step 2: Verificar que las clases `pill`, `pill-mint`, `pill-white` existen en `globals.css`**

Run:
```bash
grep -n "pill" frontend/app/globals.css | head -20
```

Si NO existen, agregarlas al globals.css (ver Task 6.5). Si existen, saltear.

- [ ] **Step 2.5 (condicional): Agregar clases `pill` a `globals.css`**

Solo si el grep de step 2 no las muestra. Agregar al final de `frontend/app/globals.css`:

```css
.pill {
  display: inline-flex;
  align-items: center;
  padding: 6px 14px;
  border: 2px solid var(--chirri-black);
  border-radius: 999px;
  font-size: 11px;
  font-weight: 800;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}
.pill-mint { background: var(--chirri-mint); }
.pill-white { background: white; }
```

- [ ] **Step 3: Typecheck**

Run: `docker compose exec -T frontend npm run typecheck`
Expected: PASS.

- [ ] **Step 4: Verificación manual en browser**

Arrancar stack si no está: `docker compose up -d`

Abrir `http://localhost:3000/login`, login con `belen.rizzo@balanz.com` / `balanz2026`. Ir a `/campaigns`.

Verificar visualmente:
- Header "campañas." lowercase gigante.
- Pill "ACTIVAS · 1" mint arriba, con la card grande mint "de ahorrista a inversor.".
- Pill "ARCHIVO · 2" blanca abajo, con 2 rows compactas.
- Click en la card grande → navega a `/campaigns/<id>` (dará 404 porque el detalle no existe todavía — esperado).
- Click en "Tus campañas" desde `/home` → te lleva a `/campaigns`.

- [ ] **Step 5: Commit**

Si se modificó `globals.css`:
```bash
git add frontend/app/campaigns/page.tsx frontend/app/globals.css
```
Si no:
```bash
git add frontend/app/campaigns/page.tsx
```

```bash
git commit -m "feat(campaigns): add /campaigns list page (DEV-79)"
```

---

### Task 7: Extender E2E smoke con aserciones de `/campaigns`

**Files:**
- Modify: `frontend/tests/home.spec.ts` (agregar un nuevo test en el mismo archivo — los 3 assertions son pocos).

- [ ] **Step 1: Leer `frontend/tests/home.spec.ts`**

Read el archivo completo para entender el patrón de login + navegación que ya usa.

- [ ] **Step 2: Agregar bloque de test para `/campaigns`**

Dentro del mismo `describe` o al final del archivo (seguir el estilo existente). El patrón típico:

```ts
test("/campaigns muestra activas y archivo", async ({ page }) => {
  // Login (reutilizar helper si existe, o copiar el flujo de home.spec.ts)
  await page.goto("/login");
  await page.fill('input[name="email"]', "belen.rizzo@balanz.com");
  await page.fill('input[name="password"]', "balanz2026");
  await page.click('button[type="submit"]');
  await page.waitForURL("**/home");

  // Navegar a /campaigns
  await page.goto("/campaigns");

  // Aserciones
  await expect(page.locator("h1")).toContainText("campañas");
  await expect(page.getByText("ACTIVAS ·")).toBeVisible();
  await expect(page.getByText("ARCHIVO ·")).toBeVisible();
  await expect(page.getByText("de ahorrista a inversor")).toBeVisible();
});
```

**Ajustar el helper de login** al estilo concreto que usa `home.spec.ts` (selectors, waitForURL, etc.). Si hay un helper `login(page)` ya definido, usarlo.

- [ ] **Step 3: Correr el smoke**

Run: `npm run test:e2e:smoke`
Expected: PASS. Incluye el smoke existente de home + el nuevo de campaigns.

Si falla por hot-reload Windows (ver CLAUDE.md gotcha), correr primero `docker compose restart frontend` y reintentar.

- [ ] **Step 4: Commit**

```bash
git add frontend/tests/home.spec.ts
git commit -m "test(campaigns): add E2E smoke for /campaigns list (DEV-79)"
```

---

### Task 8: Crear follow-up tickets DEV-80 y DEV-81

**Files:**
- (none — Linear only)

- [ ] **Step 1: Crear DEV-80 (priority Low, state "Someday" / "Backlog")**

Título: `Métricas agregadas a nivel campaña (totalReach, piezas, influencers)`

Body:

```
Diseñamos /campaigns sin mostrar agregados de reportes por campaña (totalReach, piezas, influencers). Claude design había inventado esos campos en el mockup; ninguno está pedido en design-prompt.md del material original.

Este ticket queda para VALIDAR con Chirri si quieren info agregada por campaña, y si sí, implementarla.

## Si se valida con Chirri

Backend:
- Extender CampaignListSerializer con annotations: total_reach (sum de ReportMetric.metric_name='reach' en reportes publicados), piece_count, influencer_count (count de CampaignInfluencer).
- O endpoint separado /api/campaigns/<id>/summary/.

Frontend:
- Mostrar "Alcance total" en CampaignCardBig (mockup v2 ya lo tenía).
- Columna totalReach en CampaignRowArchived.

Priority: Low. State: Someday/Backlog hasta validación.
```

Asignar a Daniel. Estado: Backlog o Someday.

- [ ] **Step 2: Crear DEV-81 (priority Medium)**

Título: `Instalar Vitest en frontend para unit tests de lib/`

Body:

```
Hoy no hay infra de unit tests en frontend (solo Playwright E2E). Las funciones puras de lib/ (formatPeriod, formatReportDate, formatCompact, firstName, sumReach) son ideales para unit tests.

## Alcance

1. npm install -D vitest @vitest/ui @testing-library/react jsdom en frontend/.
2. vitest.config.ts con environment jsdom, alias @/* -> ./.
3. Script frontend/package.json: test:unit.
4. Script root package.json: test:unit:frontend que corre el de arriba.
5. Wirear a scripts/run_test_battery.sh para que test:battery incluya frontend unit.
6. Primer test target: frontend/lib/format.test.ts con los 5 casos de formatPeriod + 2 de formatReportDate (los que quedaron sin cobertura en DEV-79).
7. CI: actualizar .github/workflows/test.yml para correr el job.

Priority: Medium. Deuda técnica explícita de DEV-79.
```

Asignar a Daniel. Estado: Backlog.

- [ ] **Step 3: Confirmar que los 2 issues aparecen en Linear**

---

### Task 9: PR a `development` y handoff a Euge

**Files:**
- (none — git + Linear)

- [ ] **Step 1: Chequear el estado del branch**

```bash
git status
git log --oneline origin/development..HEAD
```

Expected: 4-5 commits (format helpers, home refactor, componentes, page, E2E).

- [ ] **Step 2: Push al remote**

```bash
git push origin <branch-actual>
```

(Si estamos directo en `development`, usuario debe confirmar que quiere push directo. Si hay un feature branch, abrir PR.)

- [ ] **Step 3: Si hay PR, abrirlo**

```bash
gh pr create --title "feat(campaigns): /campaigns list page (DEV-79)" --body "$(cat <<'EOF'
## Summary
- `/campaigns` lista activas (cards grandes rotativas mint/peach/lilac) y archivadas (rows compactas)
- `lib/format.ts` con `formatPeriod` y `formatReportDate`; `home/page.tsx` migrado a importar desde ahí (DRY)
- E2E smoke extendido

## Spec & Plan
- `docs/superpowers/specs/2026-04-20-campaigns-list-design.md`
- `docs/superpowers/plans/2026-04-20-campaigns-list.md`

## Follow-ups
- DEV-80 — métricas agregadas por campaña (validar con Chirri)
- DEV-81 — infra de Vitest en frontend (unit tests de lib/)

## Test plan
- [x] `docker compose exec -T frontend npm run typecheck` verde
- [x] `npm run test:e2e:smoke` verde
- [x] Verificación manual en browser: login → home → /campaigns OK
EOF
)"
```

- [ ] **Step 4: Chequear README**

Run:
```bash
grep -ni "campaigns\|campañas\|/home\|páginas" README.md
```

Si `README.md` menciona páginas disponibles y no lista `/campaigns`, agregarlo en la sección correspondiente. Si no las menciona, saltear.

Si se modificó: commit aparte `docs: add /campaigns to README pages (DEV-79)`.

- [ ] **Step 5: Mover DEV-79 a In Review y asignar a Euge**

Usar `mcp__linear__save_issue` con el ID del issue, state "In Review", assignee Euge (buscar con `list_users` query "Euge").

---

## Self-review checklist

Después de implementar todo:

- Todos los archivos creados/modificados compilan (`npm run typecheck`).
- Smoke verde (`npm run test:e2e:smoke`).
- Ningún archivo supera ~200 líneas (chequear con `wc -l` sobre los 4 archivos nuevos).
- DEV-79 en In Review + Euge. DEV-80 y DEV-81 creados. PR abierto o mergeado.
- Home sigue funcionando (no regresión por el refactor de Task 3).
