# DEV-86 Campaign Detail Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship `/campaigns/[id]` — server-rendered detail page with campaign header, stages timeline, and published reports per stage, tenant-scoped via viewset.

**Architecture:** Extends `CampaignViewSet.retrieve` with a new `CampaignDetailSerializer` that nests `stages_with_reports`. Frontend mirrors DEV-52 pattern: server component page + modular sections (`CampaignHeader`, `StagesTimeline`, `StageBlock`).

**Tech Stack:** Django 5 + DRF, Next.js 14 App Router (SSR), PostgreSQL, pytest, Playwright.

**Spec:** `docs/superpowers/specs/2026-04-20-campaign-detail-design.md`

---

**Status:** Done — 2026-04-20

## File Structure

**Backend:**
- Modify: `backend/apps/campaigns/serializers.py` — add `CampaignReportRowSerializer`, `StageWithReportsSerializer`, `CampaignDetailSerializer`.
- Modify: `backend/apps/campaigns/views.py` — override `get_serializer_class`, add detail queryset with Prefetch.
- Create: `backend/tests/unit/test_campaigns_detail_view.py` — 8 tests (auth/scoping/shape/N+1).

**Frontend:**
- Modify: `frontend/lib/api.ts` — add `CampaignReportRowDto`, `StageWithReportsDto`, `CampaignDetailDto`.
- Create: `frontend/app/campaigns/[id]/page.tsx` — server component orchestrator.
- Create: `frontend/app/campaigns/[id]/sections/CampaignHeader.tsx`.
- Create: `frontend/app/campaigns/[id]/sections/StagesTimeline.tsx`.
- Create: `frontend/app/campaigns/[id]/sections/StageBlock.tsx`.
- Modify: `frontend/tests/campaigns.spec.ts` — create new file with 3 E2E tests.

**Ops/Docs:**
- Modify: `README.md` — add `/campaigns/[id]` to "Rutas del portal".
- Modify: `.github/workflows/deploy.yml` — extend `--grep` in post_deploy_smoke to include `Campaign detail`.
- Modify: spec + plan status lines at the end (Status: Done, move plan to `completed/`).

---

## Task 1: Backend serializer + unit tests (DTO shape)

**Files:**
- Modify: `backend/apps/campaigns/serializers.py`
- Create: `backend/tests/unit/test_campaigns_detail_view.py`

- [ ] **Step 1: Write failing test for serializer shape**

Create `backend/tests/unit/test_campaigns_detail_view.py`:

```python
"""Campaign detail endpoint: nested stages_with_reports.

The retrieve action returns the campaign plus its stages, each stage
carrying its list of PUBLISHED reports only. Drafts never leak.

Scoping mirrors DEV-52: cross-tenant → 404, not 403.
"""
from datetime import date, timedelta

import pytest
from django.utils import timezone

from apps.campaigns.models import Campaign, Stage
from apps.reports.models import Report


pytestmark = pytest.mark.django_db


class TestCampaignDetail:
    def _url(self, pk: int) -> str:
        return f"/api/campaigns/{pk}/"

    def test_returns_401_without_auth(self, api_client, balanz_campaign):
        res = api_client.get(self._url(balanz_campaign.pk))
        assert res.status_code == 401

    def test_returns_campaign_with_nested_stages_and_reports(
        self, authed_balanz, balanz_campaign
    ):
        stage = Stage.objects.create(
            campaign=balanz_campaign, order=1, name="Etapa 1", kind=Stage.Kind.AWARENESS
        )
        Report.objects.create(
            stage=stage,
            kind=Report.Kind.MENSUAL,
            period_start=date(2026, 3, 1),
            period_end=date(2026, 3, 31),
            title="Mensual marzo",
            status=Report.Status.PUBLISHED,
            published_at=timezone.now(),
        )
        res = authed_balanz.get(self._url(balanz_campaign.pk))
        assert res.status_code == 200
        assert res.data["id"] == balanz_campaign.pk
        assert res.data["brand_name"] == "Balanz"
        stages = res.data["stages_with_reports"]
        assert len(stages) == 1
        assert stages[0]["name"] == "Etapa 1"
        assert stages[0]["kind"] == "AWARENESS"
        assert len(stages[0]["reports"]) == 1
        assert stages[0]["reports"][0]["kind"] == "MENSUAL"

    def test_filters_draft_reports_from_stage(self, authed_balanz, balanz_campaign):
        stage = Stage.objects.create(
            campaign=balanz_campaign, order=1, name="Etapa 1", kind=Stage.Kind.AWARENESS
        )
        Report.objects.create(
            stage=stage,
            kind=Report.Kind.MENSUAL,
            period_start=date(2026, 3, 1),
            period_end=date(2026, 3, 31),
            status=Report.Status.DRAFT,
        )
        res = authed_balanz.get(self._url(balanz_campaign.pk))
        assert res.status_code == 200
        assert res.data["stages_with_reports"][0]["reports"] == []

    def test_cross_tenant_returns_404(self, authed_rival, balanz_campaign):
        res = authed_rival.get(self._url(balanz_campaign.pk))
        assert res.status_code == 404

    def test_unknown_id_returns_404(self, authed_balanz):
        res = authed_balanz.get(self._url(99999))
        assert res.status_code == 404

    def test_user_without_client_returns_404(
        self, api_client, balanz_campaign
    ):
        from apps.users.models import ClientUser
        from rest_framework_simplejwt.tokens import RefreshToken
        orphan = ClientUser.objects.create_user(
            email="orphan@nowhere.com", password="x", client=None
        )
        token = RefreshToken.for_user(orphan).access_token
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
        res = api_client.get(self._url(balanz_campaign.pk))
        assert res.status_code == 404

    def test_empty_stages_returns_empty_array(self, authed_balanz, balanz_campaign):
        res = authed_balanz.get(self._url(balanz_campaign.pk))
        assert res.status_code == 200
        assert res.data["stages_with_reports"] == []

    def test_stage_with_no_published_reports_has_empty_reports_array(
        self, authed_balanz, balanz_campaign
    ):
        Stage.objects.create(
            campaign=balanz_campaign, order=1, name="Etapa vacía", kind=Stage.Kind.OTHER
        )
        res = authed_balanz.get(self._url(balanz_campaign.pk))
        assert res.status_code == 200
        stages = res.data["stages_with_reports"]
        assert len(stages) == 1
        assert stages[0]["reports"] == []

    def test_detail_uses_constant_query_count(
        self, authed_balanz, balanz_campaign, django_assert_max_num_queries
    ):
        stage = Stage.objects.create(
            campaign=balanz_campaign, order=1, name="Etapa 1", kind=Stage.Kind.AWARENESS
        )
        for i in range(3):
            Report.objects.create(
                stage=stage,
                kind=Report.Kind.MENSUAL,
                period_start=date(2026, 1, 1) + timedelta(days=30 * i),
                period_end=date(2026, 1, 31) + timedelta(days=30 * i),
                status=Report.Status.PUBLISHED,
                published_at=timezone.now(),
            )
        with django_assert_max_num_queries(8):
            res = authed_balanz.get(self._url(balanz_campaign.pk))
        assert res.status_code == 200
        assert len(res.data["stages_with_reports"][0]["reports"]) == 3
```

- [ ] **Step 2: Run tests — all should FAIL**

```bash
docker compose exec backend pytest backend/tests/unit/test_campaigns_detail_view.py -v
```

Expected: all 9 FAIL (serializer/view not yet configured for detail). Most likely 500 or wrong shape.

- [ ] **Step 3: Add detail serializers**

Append to `backend/apps/campaigns/serializers.py`:

```python
from apps.reports.models import Report


class CampaignReportRowSerializer(serializers.ModelSerializer):
    """Minimal report payload for the per-stage list on the campaign detail page.

    Intentionally smaller than ReportDetailSerializer — we only need what the
    row renders (title, kind, period, published_at) to avoid dragging metrics
    and top_content into a list view.
    """

    class Meta:
        model = Report
        fields = (
            "id",
            "title",
            "display_title",
            "kind",
            "period_start",
            "period_end",
            "published_at",
        )


class StageWithReportsSerializer(serializers.ModelSerializer):
    reports = serializers.SerializerMethodField()

    class Meta:
        model = Stage
        fields = (
            "id",
            "order",
            "kind",
            "name",
            "description",
            "start_date",
            "end_date",
            "reports",
        )

    def get_reports(self, stage):
        # Stage.reports is prefetched in the view with status=PUBLISHED filter.
        # Ordering (-published_at) also comes from the prefetch queryset.
        return CampaignReportRowSerializer(stage.reports.all(), many=True).data


class CampaignDetailSerializer(CampaignListSerializer):
    stages_with_reports = StageWithReportsSerializer(
        source="stages", many=True, read_only=True
    )

    class Meta(CampaignListSerializer.Meta):
        fields = CampaignListSerializer.Meta.fields + ("stages_with_reports",)
```

- [ ] **Step 4: Run tests — serializers will still mostly fail (view not updated)**

```bash
docker compose exec backend pytest backend/tests/unit/test_campaigns_detail_view.py -v
```

Expected: most still FAIL — the viewset still uses list serializer on retrieve. Next task fixes that.

- [ ] **Step 5: Commit**

```bash
git add backend/apps/campaigns/serializers.py backend/tests/unit/test_campaigns_detail_view.py
git commit -m "feat(campaigns): add detail serializers + failing tests for /campaigns/<id>/"
```

---

## Task 2: Wire CampaignDetailSerializer into the viewset

**Files:**
- Modify: `backend/apps/campaigns/views.py`

- [ ] **Step 1: Replace view with detail-aware version**

Replace the entire contents of `backend/apps/campaigns/views.py` with:

```python
import logging

from django.db.models import Count, Max, Prefetch, Q
from rest_framework import permissions, viewsets

from apps.reports.models import Report

from .models import Campaign, Stage
from .serializers import CampaignDetailSerializer, CampaignListSerializer

logger = logging.getLogger(__name__)


class CampaignViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [permissions.IsAuthenticated]

    def get_serializer_class(self):
        if self.action == "retrieve":
            return CampaignDetailSerializer
        return CampaignListSerializer

    def get_queryset(self):
        client_id = getattr(self.request.user, "client_id", None)
        if client_id is None:
            return Campaign.objects.none()

        if self.action == "retrieve":
            published_reports = (
                Report.objects
                .filter(status=Report.Status.PUBLISHED)
                .order_by("-published_at")
            )
            stages_qs = (
                Stage.objects
                .order_by("order")
                .prefetch_related(Prefetch("reports", queryset=published_reports))
            )
            return (
                Campaign.objects
                .filter(brand__client_id=client_id)
                .select_related("brand")
                .prefetch_related(Prefetch("stages", queryset=stages_qs))
            )

        # list action keeps the existing annotated queryset
        published = Q(stages__reports__status=Report.Status.PUBLISHED)
        return (
            Campaign.objects
            .filter(brand__client_id=client_id)
            .select_related("brand")
            .prefetch_related("stages")
            .annotate(
                _stage_count=Count("stages", distinct=True),
                _published_count=Count("stages__reports", filter=published, distinct=True),
                _last_published_at=Max("stages__reports__published_at", filter=published),
            )
        )

    def retrieve(self, request, *args, **kwargs):
        try:
            response = super().retrieve(request, *args, **kwargs)
        except Exception:
            logger.warning(
                "campaign_detail_access_denied",
                extra={
                    "campaign_id": kwargs.get("pk"),
                    "user_id": getattr(request.user, "id", None),
                    "client_id": getattr(request.user, "client_id", None),
                    "reason": "not_found_or_scoped_out",
                },
            )
            raise
        logger.info(
            "campaign_detail_served",
            extra={
                "campaign_id": kwargs.get("pk"),
                "client_id": getattr(request.user, "client_id", None),
                "user_id": request.user.id,
            },
        )
        return response
```

Note: the list serializer uses `_stage_count`/`_published_count`/`_last_published_at` annotations. Those only apply to list. Retrieve doesn't need them — `CampaignDetailSerializer` inherits these fields from `CampaignListSerializer` but DRF will fall back to the model's Count(…) if the annotation is absent? No — it won't, because the serializer uses `source="_stage_count"`. The detail serializer inherits this and would crash.

Fix: either (a) make list-only fields optional on detail, or (b) drop them on detail. Cleanest: override the Meta on `CampaignDetailSerializer` to exclude the annotation-backed fields. Update `serializers.py` accordingly in the next step (still inside Task 2).

- [ ] **Step 2: Drop annotation-backed fields from CampaignDetailSerializer**

Open `backend/apps/campaigns/serializers.py` and replace `CampaignDetailSerializer` with:

```python
class CampaignDetailSerializer(serializers.ModelSerializer):
    """Detail payload: campaign + stages nested with their published reports.

    Does NOT inherit from CampaignListSerializer because the list serializer
    reads annotations (_stage_count, _published_count, _last_published_at)
    that are only added to the list queryset — inheriting them here would
    crash on retrieve.
    """

    brand_name = serializers.CharField(source="brand.name", read_only=True)
    stages_with_reports = StageWithReportsSerializer(
        source="stages", many=True, read_only=True
    )

    class Meta:
        model = Campaign
        fields = (
            "id",
            "brand_name",
            "name",
            "brief",
            "status",
            "start_date",
            "end_date",
            "is_ongoing_operation",
            "stages_with_reports",
        )
```

- [ ] **Step 3: Run tests — all should PASS**

```bash
docker compose exec backend pytest backend/tests/unit/test_campaigns_detail_view.py -v
```

Expected: 9 PASS.

- [ ] **Step 4: Run full backend suite to check for regressions**

```bash
docker compose exec backend pytest -q
```

Expected: all previously-passing tests still PASS (including `test_campaigns_api.py` for the list).

- [ ] **Step 5: Commit**

```bash
git add backend/apps/campaigns/views.py backend/apps/campaigns/serializers.py
git commit -m "feat(campaigns): retrieve returns nested stages_with_reports"
```

---

## Task 3: Frontend DTO types

**Files:**
- Modify: `frontend/lib/api.ts`

- [ ] **Step 1: Add DTO types**

Insert the following block in `frontend/lib/api.ts` immediately after the `CampaignDto` type definition (near line 79):

```ts
export type CampaignReportRowDto = {
  id: number;
  title: string;
  display_title: string;
  kind: "INFLUENCER" | "GENERAL" | "QUINCENAL" | "MENSUAL" | "CIERRE_ETAPA";
  period_start: string;
  period_end: string;
  published_at: string;
};

export type StageWithReportsDto = {
  id: number;
  order: number;
  kind: "AWARENESS" | "EDUCATION" | "VALIDATION" | "CONVERSION" | "ONGOING" | "OTHER";
  name: string;
  description: string;
  start_date: string | null;
  end_date: string | null;
  reports: CampaignReportRowDto[];
};

export type CampaignDetailDto = {
  id: number;
  brand_name: string;
  name: string;
  brief: string;
  status: "ACTIVE" | "FINISHED" | "PAUSED";
  start_date: string | null;
  end_date: string | null;
  is_ongoing_operation: boolean;
  stages_with_reports: StageWithReportsDto[];
};
```

- [ ] **Step 2: Verify TypeScript compiles**

```bash
cd frontend && npx tsc --noEmit
```

Expected: no errors.

- [ ] **Step 3: Commit**

```bash
git add frontend/lib/api.ts
git commit -m "feat(api): add CampaignDetailDto / StageWithReportsDto / CampaignReportRowDto"
```

---

## Task 4: CampaignHeader section

**Files:**
- Create: `frontend/app/campaigns/[id]/sections/CampaignHeader.tsx`

- [ ] **Step 1: Create the component**

```tsx
import Link from "next/link";
import type { CampaignDetailDto } from "@/lib/api";
import { formatPeriod } from "@/lib/format";

const STATUS_PILL: Record<
  CampaignDetailDto["status"],
  { label: string; className: string }
> = {
  ACTIVE: { label: "ACTIVA", className: "status status-approved" },
  FINISHED: { label: "TERMINADA", className: "status status-archived" },
  PAUSED: { label: "PAUSADA", className: "status status-paused" },
};

type Props = {
  campaign: CampaignDetailDto;
  clientName: string;
};

export default function CampaignHeader({ campaign, clientName }: Props) {
  const period = formatPeriod(
    campaign.start_date,
    campaign.end_date,
    campaign.is_ongoing_operation,
  );
  const pill = STATUS_PILL[campaign.status];

  return (
    <header style={{ marginBottom: 40 }}>
      <nav className="eyebrow" aria-label="Breadcrumb">
        Chirri Portal · {clientName} ·{" "}
        <Link href="/campaigns" style={{ textDecoration: "underline" }}>
          campañas
        </Link>
      </nav>
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
        {campaign.name.toLowerCase()}
      </h1>
      <div style={{ display: "flex", gap: 14, alignItems: "center", marginTop: 14 }}>
        <span className={pill.className} aria-label={`Estado: ${pill.label.toLowerCase()}`}>
          ● {pill.label}
        </span>
        <span style={{ fontSize: 13, fontWeight: 700 }}>{period}</span>
      </div>
      {campaign.brief && (
        <p style={{ fontSize: 16, maxWidth: 720, marginTop: 18, lineHeight: 1.5, fontWeight: 500 }}>
          {campaign.brief}
        </p>
      )}
    </header>
  );
}
```

- [ ] **Step 2: Verify TypeScript compiles**

```bash
cd frontend && npx tsc --noEmit
```

Expected: no errors (the classes `status-archived` / `status-paused` may not exist yet in CSS — that's fine, they degrade to no-style; we don't create CSS in this ticket).

- [ ] **Step 3: Commit**

```bash
git add frontend/app/campaigns/[id]/sections/CampaignHeader.tsx
git commit -m "feat(campaigns): add CampaignHeader section"
```

---

## Task 5: StageBlock section

**Files:**
- Create: `frontend/app/campaigns/[id]/sections/StageBlock.tsx`

- [ ] **Step 1: Create the component**

```tsx
import Link from "next/link";
import type { StageWithReportsDto } from "@/lib/api";
import { formatPeriod, formatReportDate } from "@/lib/format";

const REPORT_KIND_LABEL: Record<
  StageWithReportsDto["reports"][number]["kind"],
  string
> = {
  MENSUAL: "MENSUAL",
  QUINCENAL: "QUINCENAL",
  CIERRE_ETAPA: "CIERRE DE ETAPA",
  GENERAL: "GENERAL",
  INFLUENCER: "INFLUENCER",
};

export default function StageBlock({ stage }: { stage: StageWithReportsDto }) {
  const period = formatPeriod(stage.start_date, stage.end_date, false);

  return (
    <li
      style={{
        display: "grid",
        gridTemplateColumns: "48px 1fr",
        gap: 20,
        padding: "24px 0",
        borderTop: "2px solid var(--chirri-black)",
      }}
    >
      <div
        className="font-display"
        style={{ fontSize: 40, lineHeight: 1, opacity: 0.6 }}
        aria-hidden="true"
      >
        {String(stage.order).padStart(2, "0")}
      </div>
      <div>
        <h3
          className="font-display"
          style={{
            fontSize: 36,
            lineHeight: 1,
            letterSpacing: "-0.02em",
            margin: "0 0 6px",
            textTransform: "lowercase",
          }}
        >
          {stage.name.toLowerCase()}
        </h3>
        <div style={{ fontSize: 12, fontWeight: 700, marginBottom: 12 }}>{period}</div>
        {stage.description && (
          <p style={{ fontSize: 14, lineHeight: 1.5, maxWidth: 620, marginBottom: 16 }}>
            {stage.description}
          </p>
        )}
        {stage.reports.length === 0 ? (
          <p style={{ fontSize: 13, color: "var(--chirri-muted)", fontStyle: "italic" }}>
            Esta etapa todavía no tiene reportes publicados.
          </p>
        ) : (
          <ul style={{ listStyle: "none", padding: 0, margin: 0, display: "flex", flexDirection: "column", gap: 8 }}>
            {stage.reports.map((r) => (
              <li key={r.id}>
                <Link
                  href={`/reports/${r.id}`}
                  className="card-link"
                  style={{
                    display: "grid",
                    gridTemplateColumns: "1fr auto auto",
                    gap: 16,
                    alignItems: "center",
                    padding: "12px 16px",
                    border: "2px solid var(--chirri-black)",
                    borderRadius: 12,
                    background: "var(--chirri-yellow-soft)",
                    textDecoration: "none",
                    color: "inherit",
                    fontSize: 14,
                    fontWeight: 600,
                  }}
                >
                  <span>{r.display_title}</span>
                  <span className="pill pill-white" style={{ fontSize: 10 }}>
                    {REPORT_KIND_LABEL[r.kind]}
                  </span>
                  <span style={{ fontSize: 12, fontWeight: 700 }}>
                    {formatReportDate(r.published_at)}
                  </span>
                </Link>
              </li>
            ))}
          </ul>
        )}
      </div>
    </li>
  );
}
```

- [ ] **Step 2: Verify TypeScript compiles**

```bash
cd frontend && npx tsc --noEmit
```

Expected: no errors.

- [ ] **Step 3: Commit**

```bash
git add frontend/app/campaigns/[id]/sections/StageBlock.tsx
git commit -m "feat(campaigns): add StageBlock section with reports list"
```

---

## Task 6: StagesTimeline section

**Files:**
- Create: `frontend/app/campaigns/[id]/sections/StagesTimeline.tsx`

- [ ] **Step 1: Create the component**

```tsx
import type { StageWithReportsDto } from "@/lib/api";
import StageBlock from "./StageBlock";

export default function StagesTimeline({
  stages,
}: {
  stages: StageWithReportsDto[];
}) {
  if (stages.length === 0) {
    return (
      <section
        style={{
          padding: 28,
          border: "2px dashed var(--chirri-black)",
          borderRadius: 18,
          background: "rgba(0,0,0,0.03)",
          marginBottom: 40,
        }}
      >
        <p style={{ margin: 0, fontSize: 14, fontWeight: 600 }}>
          Esta campaña todavía no tiene etapas publicadas.
        </p>
      </section>
    );
  }

  return (
    <section style={{ marginBottom: 40 }}>
      <ol
        style={{
          listStyle: "none",
          padding: 0,
          margin: 0,
          borderBottom: "2px solid var(--chirri-black)",
        }}
      >
        {stages.map((stage) => (
          <StageBlock key={stage.id} stage={stage} />
        ))}
      </ol>
    </section>
  );
}
```

- [ ] **Step 2: Verify TypeScript compiles**

```bash
cd frontend && npx tsc --noEmit
```

Expected: no errors.

- [ ] **Step 3: Commit**

```bash
git add frontend/app/campaigns/[id]/sections/StagesTimeline.tsx
git commit -m "feat(campaigns): add StagesTimeline section with empty state"
```

---

## Task 7: /campaigns/[id] page orchestrator

**Files:**
- Create: `frontend/app/campaigns/[id]/page.tsx`

- [ ] **Step 1: Create the page**

```tsx
import { notFound, redirect } from "next/navigation";
import { apiFetch, ApiError, type CampaignDetailDto } from "@/lib/api";
import { getAccessToken, getCurrentUser } from "@/lib/auth";
import TopBar from "@/components/top-bar";

import CampaignHeader from "./sections/CampaignHeader";
import StagesTimeline from "./sections/StagesTimeline";

export default async function CampaignDetailPage({
  params,
}: {
  params: { id: string };
}) {
  const user = await getCurrentUser();
  if (!user) redirect("/login");

  const token = getAccessToken();
  let campaign: CampaignDetailDto;
  try {
    campaign = await apiFetch<CampaignDetailDto>(`/api/campaigns/${params.id}/`, { token });
  } catch (err) {
    if (err instanceof ApiError && err.status === 404) notFound();
    console.error("campaigns_detail_fetch_failed", { id: params.id, err });
    throw err;
  }

  return (
    <>
      <TopBar user={user} active="campaigns" />
      <main className="page page-wide" style={{ background: "var(--chirri-pink)" }}>
        <CampaignHeader campaign={campaign} clientName={user.client?.name ?? "—"} />
        <StagesTimeline stages={campaign.stages_with_reports} />
      </main>
    </>
  );
}
```

- [ ] **Step 2: Verify TypeScript compiles**

```bash
cd frontend && npx tsc --noEmit
```

Expected: no errors.

- [ ] **Step 3: Boot frontend + manual smoke**

```bash
docker compose up -d
```

Then visit `http://localhost:3000/campaigns/1` (after logging in at `/login` with `belen.rizzo@balanz.com` / `balanz2026`). Expected:
- Header with campaign name, status pill, period, brief.
- At least one stage block with reports (seed has Balanz campaigns).
- Report rows linkeable — clicking one goes to `/reports/<id>`.

- [ ] **Step 4: Commit**

```bash
git add frontend/app/campaigns/[id]/page.tsx
git commit -m "feat(campaigns): add /campaigns/[id] server component page"
```

---

## Task 8: E2E smoke tests

**Files:**
- Create: `frontend/tests/campaigns.spec.ts`

- [ ] **Step 1: Create the spec file**

```ts
import { test, expect } from "@playwright/test";
import { login, trackConsoleErrors } from "./helpers";

test.describe("Campaign detail smoke", () => {
  test("login → /campaigns → click active campaign → detail renders", async ({ page }) => {
    const errors = trackConsoleErrors(page);

    await login(page);

    await page.goto("/campaigns");
    await page.getByRole("link", { name: /abrir/i }).first().click();

    await expect(page).toHaveURL(/\/campaigns\/\d+$/);

    // Header
    await expect(page.locator("h1").first()).toBeVisible();
    // Breadcrumb mentions Balanz.
    await expect(page.getByText(/balanz/i).first()).toBeVisible();
    // At least one stage heading (h3) is visible.
    await expect(page.locator("h3").first()).toBeVisible();
    // At least one report link → /reports/<id>.
    await expect(page.locator('a[href^="/reports/"]').first()).toBeVisible();

    expect(
      errors,
      `console/page errors on /campaigns/<id>:\n${errors.join("\n")}`,
    ).toEqual([]);
  });

  test("report row navigates to /reports/<id>", async ({ page }) => {
    await login(page);
    await page.goto("/campaigns");
    await page.getByRole("link", { name: /abrir/i }).first().click();
    await expect(page).toHaveURL(/\/campaigns\/\d+$/);

    await page.locator('a[href^="/reports/"]').first().click();
    await expect(page).toHaveURL(/\/reports\/\d+$/);
    await expect(page.locator("h1").first()).toBeVisible();
  });

  test("unknown campaign id returns 404", async ({ page }) => {
    await login(page);
    const response = await page.goto("/campaigns/999999");
    expect(response?.status()).toBe(404);
  });
});
```

- [ ] **Step 1.5: Add keyboard navigation assertion**

Append this test inside the same `test.describe(...)` block to lock in a11y:

```ts
  test("keyboard navigation: Tab reaches first report link and Enter opens it", async ({ page }) => {
    await login(page);
    await page.goto("/campaigns");
    await page.getByRole("link", { name: /abrir/i }).first().click();
    await expect(page).toHaveURL(/\/campaigns\/\d+$/);

    // Focus first report anchor via keyboard.
    const firstReport = page.locator('a[href^="/reports/"]').first();
    await firstReport.focus();
    await expect(firstReport).toBeFocused();

    await page.keyboard.press("Enter");
    await expect(page).toHaveURL(/\/reports\/\d+$/);
  });
```

- [ ] **Step 2: Run the E2E tests**

```bash
cd frontend && npx playwright test tests/campaigns.spec.ts --reporter=line
```

Expected: 3 tests PASS. If the first assertion about "Abrir" fails, inspect the `/campaigns` page and adjust the selector (should match `CampaignCardBig`'s "Abrir →" button copy).

- [ ] **Step 3: Commit**

```bash
git add frontend/tests/campaigns.spec.ts
git commit -m "test(campaigns): add E2E smoke for /campaigns/[id]"
```

---

## Task 9: Update docs + CI grep filter

**Files:**
- Modify: `README.md`
- Modify: `.github/workflows/deploy.yml`
- Modify: `frontend/package.json` (`test:e2e:smoke` script — include campaigns.spec.ts)

- [ ] **Step 1: Update README.md — "Rutas del portal"**

Locate the "Rutas del portal" subsection added by DEV-52 and append:

```markdown
- `/campaigns/[id]` — detalle de campaña con stages timeline y reportes por etapa.
```

(If the subsection does not exist, create it under the existing section structure, listing at minimum `/home`, `/campaigns`, `/campaigns/[id]`, `/reports/[id]`.)

- [ ] **Step 2: Update deploy.yml grep filter**

Open `.github/workflows/deploy.yml`, find the line inside `post_deploy_smoke` with `--grep "Report viewer|Home smoke"` and change it to:

```yaml
        run: npx playwright test --grep "Report viewer|Home smoke|Campaign detail" --reporter=line
```

- [ ] **Step 3: Extend test:e2e:smoke script**

In `frontend/package.json`, replace the `test:e2e:smoke` script value so it also includes `tests/campaigns.spec.ts`. Final value:

```json
"test:e2e:smoke": "playwright test tests/home.spec.ts tests/reports.spec.ts tests/campaigns.spec.ts --reporter=line"
```

- [ ] **Step 3.5: Verify deploy.yml post_deploy_smoke uses the deployed URL**

Open `.github/workflows/deploy.yml` and confirm the `post_deploy_smoke` job sets:

```yaml
env:
  PLAYWRIGHT_BASE_URL: ${{ secrets.DEPLOY_URL }}
```

and NOT `http://localhost:3000`. If the env is missing or wrong, add/fix it. The smoke must hit the deployed URL — per entropy dim 13 and Impactia pipeline stage 4, localhost-based post-deploy smoke doesn't count.

If `secrets.DEPLOY_URL` is not configured in GitHub repo settings, create a follow-up task to add it (the smoke job will fail loudly otherwise — which is the correct failure mode).

- [ ] **Step 4: Run full smoke locally**

```bash
cd frontend && npm run test:e2e:smoke
```

Expected: all tests across home/reports/campaigns PASS.

- [ ] **Step 5: Commit**

```bash
git add README.md .github/workflows/deploy.yml frontend/package.json
git commit -m "docs+ci: include /campaigns/[id] in routes list and smoke grep filter"
```

---

## Task 10: Full test battery + archive spec & plan

**Files:**
- Modify: `docs/superpowers/specs/2026-04-20-campaign-detail-design.md`
- Move: `docs/superpowers/plans/2026-04-20-campaign-detail.md` → `docs/superpowers/plans/completed/2026-04-20-campaign-detail.md`

- [ ] **Step 1: Run full backend + frontend battery**

```bash
cd "C:/Users/danie/Impactia/Git/Chirri Peppers/Chirri Portal" && docker compose exec backend pytest -q && cd frontend && npm run test:unit && npm run test:e2e:smoke
```

Expected: everything green.

- [ ] **Step 2: Mark spec as Done**

Edit `docs/superpowers/specs/2026-04-20-campaign-detail-design.md`. Change the frontmatter line:

```
Status: Design (entropy-aware enriched 2026-04-20)
```

to:

```
Status: Done — 2026-04-20
```

- [ ] **Step 3: Archive plan**

```bash
git mv "docs/superpowers/plans/2026-04-20-campaign-detail.md" "docs/superpowers/plans/completed/2026-04-20-campaign-detail.md"
```

Then add a status line at the top of the moved file (under the header):

```markdown
**Status:** Done — 2026-04-20
```

- [ ] **Step 4: Commit the archive**

```bash
git add docs/superpowers/specs/2026-04-20-campaign-detail-design.md docs/superpowers/plans/completed/2026-04-20-campaign-detail.md
git commit -m "docs: archive DEV-86 spec + plan as Done"
```

---

## Self-Review (filled by plan author)

**1. Spec coverage:**
- Sec 2 objective → Tasks 1–7 cover full user flow. ✓
- Sec 3 architecture → Tasks 1+2 (backend), Tasks 3–7 (frontend). ✓
- Sec 4 DTOs → Task 3 creates them; Task 1 tests the backend shape. ✓
- Sec 5 UI behavior → Tasks 4–7, including empty states (StagesTimeline empty, StageBlock empty). ✓
- Sec 6 tests → Task 1 (8 backend), Task 8 (3 E2E). ✓
- Sec 7 principles → structure enforces SRP/DRY. ✓
- Sec 8 observability → Task 2 logs `campaign_detail_served`. ✓
- Sec 9 security → Task 1 tests cover 401 / cross-tenant 404 / orphan user 404 / unknown id 404. ✓
- Sec 10 CI/CD → Task 9 updates deploy.yml grep filter. ✓
- Sec 11 hygiene → Task 10 archives. ✓

**2. Placeholder scan:** No TBD/TODO/"similar to"/"handle edge cases". Every code step has complete code blocks.

**3. Type consistency:** `CampaignDetailDto.stages_with_reports` used identically in Tasks 3, 6, 7. `StageWithReportsDto` and `CampaignReportRowDto` referenced identically everywhere. Backend serializer field name `stages_with_reports` matches frontend DTO field name.

**4. Principles applied across tasks:**
- **P2 SRP**: Task 1 splits serializers into three focused classes. Task 4/5/6 split UI into three single-purpose sections.
- **P3 DRY**: Task 4/5 reuse `formatPeriod` / `formatReportDate`; Task 1 reuses `conftest.py` fixtures.
- **P5 DIP**: Task 2 viewset receives user via DRF request; Task 7 page receives `campaign` via `apiFetch` — no direct model access.
- **P6 Minimal Surface Area**: Task 2 adds one new endpoint action (retrieve) — no new URL patterns. Task 3 adds types only where the server actually returns them.
- **P9 Fail Fast**: Task 1 tests force 404 on cross-tenant / draft / orphan / unknown — no silent `[]`.
- **P10 Simplicity**: single endpoint, single fetch in the page, no client state, no hooks.

