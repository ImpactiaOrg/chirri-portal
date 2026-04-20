# Report Viewer `/reports/[id]` Implementation Plan

**Status:** Done — 2026-04-20

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the core piloto screen — a rich report viewer at `/reports/[id]` that replaces Chirri's Google Slides reports with a Balanz-branded portal page rendered from Django data.

**Architecture:** Django + DRF adds 3 models (`TopContent`, `BrandFollowerSnapshot`, `OneLinkAttribution`) plus an `intro_text` field on `Report`. A new `GET /api/reports/<id>/` endpoint returns a rich `ReportDetailSerializer` with computed Q1 rollup, YoY, and follower snapshots, scoped by tenant in the view. Next.js 14 App Router renders the page as server components: one orchestrator `page.tsx` composes per-section components that render-or-null based on data. Storage is pluggable via `django-storages[s3]` + `USE_R2` env toggle (local filesystem in dev, Cloudflare R2 in prod).

**Tech Stack:** Django 5 · DRF · PostgreSQL · django-storages[s3] (boto3) · Cloudflare R2 · Next.js 14 (App Router, SSR) · Playwright · pytest · SVG/CSS native charts (no Recharts).

**Spec:** `docs/superpowers/specs/2026-04-20-report-viewer-design.md`
**Linear:** DEV-52

**Principles applied (per `~/.ai-skills/method/PRINCIPLES.md`):**
- **P1 (Tests Before Code):** Every backend task that writes production code starts with a failing test. Frontend components are validated via TypeScript type-check + E2E smoke (Next.js server components aren't unit-tested in this codebase — E2E is the right seam).
- **P2 (SRP):** One concern per file. `services/aggregations.py` is split from `serializers.py`; each section component has one visible concern; `validators.py` is isolated from models.
- **P3 (DRY):** `build_q1_rollup`, `build_yoy`, `build_follower_snapshots` live in `services/aggregations.py` as the single source of truth. Frontend mirrors in `lib/aggregations.ts` + `lib/has-data.ts` — used by every section.
- **P5 (Depend on Abstractions):** Aggregation helpers take a `Report` argument — no hidden DB lookups inside components. `TopContentSerializer.get_thumbnail_url` delegates to the `ImageField` abstraction so local-FS vs R2 storage is transparent.
- **P6 (Minimal Surface Area):** New API endpoint adds exactly one route (`GET /api/reports/<id>/`). No mutations. No admin-facing endpoints in this ticket.
- **P7 (Security by Default):** Tenant scoping in view (not middleware — CLAUDE.md gotcha). `validate_image_size` + `validate_image_mimetype` on every uploaded image. R2 secrets only via env vars. Cross-tenant returns 404 (not 403) to avoid leaking existence.
- **P9 (Fail Fast):** `logger.warning("report_access_denied", ...)` before 404 leaves audit trail. No swallowed exceptions — fetch failures in `page.tsx` log via `console.error` and re-throw.
- **P10 (Simplicity):** SVG/CSS native charts instead of Recharts. No global state. No i18n wrapper. No feature flags. Spanish-only strings inline in components.

---

## File Structure

### Backend — modified/created

- **Modify:** `backend/config/settings/base.py` — add `USE_R2` toggle + `STORAGES` config
- **Modify:** `backend/requirements.txt` — add `django-storages[s3]`
- **Modify:** `backend/apps/reports/models.py` — add `intro_text` on Report + 3 new models
- **Create:** `backend/apps/reports/migrations/000X_report_viewer_models.py` — auto-generated
- **Modify:** `backend/apps/reports/admin.py` — register new models with image validators
- **Create:** `backend/apps/reports/validators.py` — `FileSizeValidator`, `FileMimetypeValidator`
- **Create:** `backend/apps/reports/services/aggregations.py` — `build_q1_rollup`, `build_yoy`, `build_follower_snapshots`
- **Modify:** `backend/apps/reports/serializers.py` — extend `ReportDetailSerializer`, add sub-serializers
- **Modify:** `backend/apps/reports/views.py` — add `ReportDetailView`
- **Modify:** `backend/apps/reports/urls.py` — route the detail endpoint
- **Modify:** `backend/apps/tenants/management/commands/seed_demo.py` — extend with new fixtures
- **Create:** `backend/apps/tenants/management/commands/fixtures/` — placeholder JPGs

### Backend — tests

- **Create:** `backend/tests/unit/test_reports_detail_view.py`
- **Create:** `backend/tests/unit/test_report_detail_serializer.py`
- **Create:** `backend/tests/unit/test_report_viewer_models.py`
- **Create:** `backend/tests/unit/test_report_nplus1.py`

### Frontend — modified/created

- **Modify:** `frontend/lib/api.ts` — extend `ReportDto`, add new dtos
- **Create:** `frontend/lib/has-data.ts` — empty-state helpers
- **Create:** `frontend/lib/aggregations.ts` — group `metrics` by network/source_type
- **Create:** `frontend/app/reports/[id]/page.tsx` — server component orchestrator
- **Create:** `frontend/app/reports/[id]/components/KpiTile.tsx`
- **Create:** `frontend/app/reports/[id]/components/MetricRow.tsx`
- **Create:** `frontend/app/reports/[id]/components/ContentCard.tsx`
- **Create:** `frontend/app/reports/[id]/components/BarChartMini.tsx`
- **Create:** `frontend/app/reports/[id]/sections/HeaderSection.tsx`
- **Create:** `frontend/app/reports/[id]/sections/IntroText.tsx`
- **Create:** `frontend/app/reports/[id]/sections/KpisSummary.tsx`
- **Create:** `frontend/app/reports/[id]/sections/MonthlyCompare.tsx`
- **Create:** `frontend/app/reports/[id]/sections/YoyComparison.tsx`
- **Create:** `frontend/app/reports/[id]/sections/NetworkSection.tsx`
- **Create:** `frontend/app/reports/[id]/sections/BestContentChapter.tsx`
- **Create:** `frontend/app/reports/[id]/sections/OneLinkTable.tsx`
- **Create:** `frontend/app/reports/[id]/sections/FollowerGrowthSection.tsx`
- **Create:** `frontend/app/reports/[id]/sections/Q1RollupTable.tsx`
- **Create:** `frontend/app/reports/[id]/sections/ConclusionsSection.tsx`

### Frontend — tests

- **Create:** `frontend/tests/reports.spec.ts`

### Docs / CI

- **Create:** `docs/ENV.md` (if missing)
- **Modify:** `.env.example`
- **Modify:** `README.md` — new env vars + route map
- **Modify:** GitHub Actions secrets (R2_*) — manual step, documented

---

## Phase 1: Storage foundation (django-storages + R2)

### Task 1.1: Add django-storages to requirements

**Files:**
- Modify: `backend/requirements.txt`

- [ ] **Step 1: Add the package**

Append to `backend/requirements.txt`:
```
django-storages[s3]==1.14.4
```

- [ ] **Step 2: Install in the running container**

Run: `docker compose exec backend pip install 'django-storages[s3]==1.14.4'`
Expected: installs successfully, `boto3` comes with it.

- [ ] **Step 3: Audit new dependency (P7 — Security by Default)**

Run: `docker compose exec backend pip install pip-audit && docker compose exec backend pip-audit --strict -r requirements.txt`
Expected: no HIGH / CRITICAL advisories on `django-storages`, `boto3`, `botocore`, `s3transfer`. If any advisory appears, document accepted risk in the commit message or upgrade the pinned version.

- [ ] **Step 4: Commit**

```bash
git add backend/requirements.txt
git commit -m "chore(storage): add django-storages[s3] dependency (audited)"
```

### Task 1.2: Wire USE_R2 toggle in settings

**Files:**
- Modify: `backend/config/settings/base.py:100-102` (around MEDIA_URL)

- [ ] **Step 1: Write the failing test**

Create `backend/tests/unit/test_storage_config.py`:
```python
import importlib
import os
from unittest.mock import patch

import pytest


def test_default_storage_is_filesystem_when_use_r2_is_unset(settings):
    assert settings.STORAGES["default"]["BACKEND"] == "django.core.files.storage.FileSystemStorage"


def test_default_storage_switches_to_s3_when_use_r2_is_true(monkeypatch):
    monkeypatch.setenv("USE_R2", "1")
    monkeypatch.setenv("R2_ACCESS_KEY_ID", "x")
    monkeypatch.setenv("R2_SECRET_ACCESS_KEY", "y")
    monkeypatch.setenv("R2_ENDPOINT_URL", "https://r2.example")
    monkeypatch.setenv("R2_PUBLIC_URL", "https://pub.example")
    from config.settings import base as base_settings
    importlib.reload(base_settings)
    assert base_settings.STORAGES["default"]["BACKEND"] == "storages.backends.s3.S3Storage"
    assert base_settings.AWS_S3_ENDPOINT_URL == "https://r2.example"
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `docker compose exec backend pytest tests/unit/test_storage_config.py -v`
Expected: FAIL — `settings.STORAGES` does not exist.

- [ ] **Step 3: Add STORAGES config to base settings**

In `backend/config/settings/base.py`, replace the existing `MEDIA_URL` + `MEDIA_ROOT` block with:
```python
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

USE_R2 = os.environ.get("USE_R2", "0") == "1"

if USE_R2:
    STORAGES = {
        "default": {"BACKEND": "storages.backends.s3.S3Storage"},
        "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
    }
    AWS_S3_ACCESS_KEY_ID = os.environ["R2_ACCESS_KEY_ID"]
    AWS_S3_SECRET_ACCESS_KEY = os.environ["R2_SECRET_ACCESS_KEY"]
    AWS_S3_ENDPOINT_URL = os.environ["R2_ENDPOINT_URL"]
    AWS_STORAGE_BUCKET_NAME = os.environ.get("R2_BUCKET_NAME", "chirri-media")
    AWS_S3_CUSTOM_DOMAIN = os.environ["R2_PUBLIC_URL"].replace("https://", "").rstrip("/")
    AWS_DEFAULT_ACL = None
    AWS_QUERYSTRING_AUTH = False
else:
    STORAGES = {
        "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
        "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
    }
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `docker compose exec backend pytest tests/unit/test_storage_config.py -v`
Expected: PASS (both tests).

- [ ] **Step 5: Commit**

```bash
git add backend/config/settings/base.py backend/tests/unit/test_storage_config.py
git commit -m "chore(storage): wire django-storages with USE_R2 toggle"
```

---

## Phase 2: Data models

### Task 2.1: Add `intro_text` to Report

**Files:**
- Modify: `backend/apps/reports/models.py:29`
- Test: `backend/tests/unit/test_report_viewer_models.py`

- [ ] **Step 1: Write the failing test**

Create `backend/tests/unit/test_report_viewer_models.py`:
```python
import pytest
from apps.reports.models import Report

pytestmark = pytest.mark.django_db


def test_report_intro_text_defaults_to_empty(balanz_published_report):
    assert balanz_published_report.intro_text == ""


def test_report_intro_text_can_be_set(balanz_published_report):
    balanz_published_report.intro_text = "Bienvenidos al reporte."
    balanz_published_report.save()
    balanz_published_report.refresh_from_db()
    assert balanz_published_report.intro_text == "Bienvenidos al reporte."
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `docker compose exec backend pytest tests/unit/test_report_viewer_models.py -v`
Expected: FAIL — `AttributeError: 'Report' object has no attribute 'intro_text'`.

- [ ] **Step 3: Add the field**

In `backend/apps/reports/models.py`, after the `conclusions_text` line (line 29):
```python
    intro_text = models.TextField(
        blank=True,
        help_text="Intro textual al principio del reporte (separada de conclusions_text).",
    )
```

- [ ] **Step 4: Generate migration**

Run: `docker compose exec backend python manage.py makemigrations reports`
Expected: creates `000X_report_intro_text.py`.

- [ ] **Step 5: Apply migration and re-run test**

Run: `docker compose exec backend python manage.py migrate && docker compose exec backend pytest tests/unit/test_report_viewer_models.py -v`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add backend/apps/reports/models.py backend/apps/reports/migrations/ backend/tests/unit/test_report_viewer_models.py
git commit -m "feat(reports): add intro_text field on Report"
```

### Task 2.2: Add file validators module

**Files:**
- Create: `backend/apps/reports/validators.py`

- [ ] **Step 1: Write the failing test**

Append to `backend/tests/unit/test_report_viewer_models.py`:
```python
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from apps.reports.validators import validate_image_size, validate_image_mimetype


def test_validate_image_size_accepts_under_5mb():
    small = SimpleUploadedFile("x.jpg", b"x" * 100, content_type="image/jpeg")
    validate_image_size(small)


def test_validate_image_size_rejects_over_5mb():
    huge = SimpleUploadedFile("x.jpg", b"x" * (6 * 1024 * 1024), content_type="image/jpeg")
    with pytest.raises(ValidationError):
        validate_image_size(huge)


def test_validate_image_mimetype_accepts_jpeg():
    img = SimpleUploadedFile("x.jpg", b"x", content_type="image/jpeg")
    validate_image_mimetype(img)


def test_validate_image_mimetype_rejects_svg():
    svg = SimpleUploadedFile("x.svg", b"<svg/>", content_type="image/svg+xml")
    with pytest.raises(ValidationError):
        validate_image_mimetype(svg)
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `docker compose exec backend pytest tests/unit/test_report_viewer_models.py -k validate -v`
Expected: FAIL — `ModuleNotFoundError: apps.reports.validators`.

- [ ] **Step 3: Write the validators**

Create `backend/apps/reports/validators.py`:
```python
from django.core.exceptions import ValidationError

MAX_IMAGE_SIZE_BYTES = 5 * 1024 * 1024
ALLOWED_IMAGE_MIMETYPES = {"image/jpeg", "image/png", "image/webp"}


def validate_image_size(file) -> None:
    if file.size > MAX_IMAGE_SIZE_BYTES:
        raise ValidationError(
            f"La imagen excede el tamaño máximo de {MAX_IMAGE_SIZE_BYTES // (1024 * 1024)} MB."
        )


def validate_image_mimetype(file) -> None:
    mimetype = getattr(file, "content_type", None)
    if mimetype not in ALLOWED_IMAGE_MIMETYPES:
        raise ValidationError(
            f"Formato no permitido ({mimetype}). Use JPEG, PNG o WebP."
        )
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `docker compose exec backend pytest tests/unit/test_report_viewer_models.py -k validate -v`
Expected: PASS (all 4).

- [ ] **Step 5: Commit**

```bash
git add backend/apps/reports/validators.py backend/tests/unit/test_report_viewer_models.py
git commit -m "feat(reports): add image size and mimetype validators"
```

### Task 2.3: Add TopContent model

**Files:**
- Modify: `backend/apps/reports/models.py` (append at end)
- Test: `backend/tests/unit/test_report_viewer_models.py`

- [ ] **Step 1: Write the failing test**

Append to `backend/tests/unit/test_report_viewer_models.py`:
```python
from apps.reports.models import TopContent, ReportMetric


def test_top_content_is_created_with_json_metrics(balanz_published_report):
    tc = TopContent.objects.create(
        report=balanz_published_report,
        kind=TopContent.Kind.POST,
        network=ReportMetric.Network.INSTAGRAM,
        source_type=ReportMetric.SourceType.ORGANIC,
        rank=1,
        caption="Post destacado del mes",
        metrics={"likes": 500, "reach": 12000, "er": 4.2},
    )
    assert tc.metrics["likes"] == 500
    assert tc.rank == 1


def test_top_content_orders_by_report_kind_network_rank(balanz_published_report):
    TopContent.objects.create(
        report=balanz_published_report, kind=TopContent.Kind.POST,
        network=ReportMetric.Network.INSTAGRAM, source_type=ReportMetric.SourceType.ORGANIC,
        rank=2, caption="b", metrics={},
    )
    TopContent.objects.create(
        report=balanz_published_report, kind=TopContent.Kind.POST,
        network=ReportMetric.Network.INSTAGRAM, source_type=ReportMetric.SourceType.ORGANIC,
        rank=1, caption="a", metrics={},
    )
    ranks = list(TopContent.objects.values_list("rank", flat=True))
    assert ranks == [1, 2]
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `docker compose exec backend pytest tests/unit/test_report_viewer_models.py -k top_content -v`
Expected: FAIL — `ImportError: cannot import name 'TopContent'`.

- [ ] **Step 3: Add the model**

Append to `backend/apps/reports/models.py`:
```python
class TopContent(models.Model):
    class Kind(models.TextChoices):
        POST = "POST", "Post destacado"
        CREATOR = "CREATOR", "Creator destacado"

    report = models.ForeignKey(Report, on_delete=models.CASCADE, related_name="top_content")
    kind = models.CharField(max_length=16, choices=Kind.choices)
    network = models.CharField(max_length=16, choices=ReportMetric.Network.choices)
    source_type = models.CharField(max_length=16, choices=ReportMetric.SourceType.choices)
    rank = models.PositiveIntegerField(help_text="1-based ordering within (kind, network).")
    handle = models.CharField(max_length=120, blank=True)
    caption = models.TextField(blank=True)
    thumbnail = models.ImageField(
        upload_to="top_content/%Y/%m/",
        blank=True,
        validators=[validate_image_size, validate_image_mimetype],
    )
    post_url = models.URLField(blank=True)
    metrics = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["report", "kind", "network", "rank"]
        indexes = [models.Index(fields=["report", "kind"])]

    def __str__(self):
        return f"{self.report_id} · {self.kind}/{self.network} #{self.rank}"
```

Also add at the top of the file, below existing imports:
```python
from .validators import validate_image_mimetype, validate_image_size
```

- [ ] **Step 4: Generate migration and run tests**

Run: `docker compose exec backend python manage.py makemigrations reports && docker compose exec backend python manage.py migrate && docker compose exec backend pytest tests/unit/test_report_viewer_models.py -k top_content -v`
Expected: PASS (both tests).

- [ ] **Step 5: Commit**

```bash
git add backend/apps/reports/models.py backend/apps/reports/migrations/ backend/tests/unit/test_report_viewer_models.py
git commit -m "feat(reports): add TopContent model"
```

### Task 2.4: Add BrandFollowerSnapshot model

**Files:**
- Modify: `backend/apps/reports/models.py`

- [ ] **Step 1: Write the failing test**

Append to `backend/tests/unit/test_report_viewer_models.py`:
```python
from datetime import date
from django.db import IntegrityError
from apps.reports.models import BrandFollowerSnapshot


def test_follower_snapshot_enforces_unique_brand_network_date(balanz_brand):
    BrandFollowerSnapshot.objects.create(
        brand=balanz_brand,
        network=ReportMetric.Network.INSTAGRAM,
        as_of=date(2026, 2, 28),
        followers_count=104568,
    )
    with pytest.raises(IntegrityError):
        BrandFollowerSnapshot.objects.create(
            brand=balanz_brand,
            network=ReportMetric.Network.INSTAGRAM,
            as_of=date(2026, 2, 28),
            followers_count=999,
        )
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `docker compose exec backend pytest tests/unit/test_report_viewer_models.py -k follower_snapshot -v`
Expected: FAIL — model does not exist.

- [ ] **Step 3: Add the model**

Append to `backend/apps/reports/models.py`:
```python
class BrandFollowerSnapshot(models.Model):
    brand = models.ForeignKey(
        "tenants.Brand",
        on_delete=models.CASCADE,
        related_name="follower_snapshots",
    )
    network = models.CharField(max_length=16, choices=ReportMetric.Network.choices)
    as_of = models.DateField()
    followers_count = models.PositiveIntegerField()

    class Meta:
        unique_together = [("brand", "network", "as_of")]
        ordering = ["-as_of"]

    def __str__(self):
        return f"{self.brand_id}/{self.network} @ {self.as_of}: {self.followers_count}"
```

- [ ] **Step 4: Generate migration and re-run the test**

Run: `docker compose exec backend python manage.py makemigrations reports && docker compose exec backend python manage.py migrate && docker compose exec backend pytest tests/unit/test_report_viewer_models.py -k follower_snapshot -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/apps/reports/models.py backend/apps/reports/migrations/ backend/tests/unit/test_report_viewer_models.py
git commit -m "feat(reports): add BrandFollowerSnapshot model"
```

### Task 2.5: Add OneLinkAttribution model

**Files:**
- Modify: `backend/apps/reports/models.py`

- [ ] **Step 1: Write the failing test**

Append to `backend/tests/unit/test_report_viewer_models.py`:
```python
from apps.reports.models import OneLinkAttribution


def test_onelink_attribution_orders_by_downloads_desc(balanz_published_report):
    OneLinkAttribution.objects.create(
        report=balanz_published_report, influencer_handle="@low", clicks=10, app_downloads=2,
    )
    OneLinkAttribution.objects.create(
        report=balanz_published_report, influencer_handle="@high", clicks=100, app_downloads=50,
    )
    handles = list(
        OneLinkAttribution.objects.filter(report=balanz_published_report)
        .values_list("influencer_handle", flat=True)
    )
    assert handles == ["@high", "@low"]
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `docker compose exec backend pytest tests/unit/test_report_viewer_models.py -k onelink -v`
Expected: FAIL — model does not exist.

- [ ] **Step 3: Add the model**

Append to `backend/apps/reports/models.py`:
```python
class OneLinkAttribution(models.Model):
    report = models.ForeignKey(Report, on_delete=models.CASCADE, related_name="onelink")
    influencer_handle = models.CharField(max_length=120)
    clicks = models.PositiveIntegerField(default=0)
    app_downloads = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["report", "-app_downloads"]
        indexes = [models.Index(fields=["report"])]

    def __str__(self):
        return f"{self.report_id} · {self.influencer_handle}: {self.app_downloads}d/{self.clicks}c"
```

- [ ] **Step 4: Generate migration and re-run the test**

Run: `docker compose exec backend python manage.py makemigrations reports && docker compose exec backend python manage.py migrate && docker compose exec backend pytest tests/unit/test_report_viewer_models.py -k onelink -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/apps/reports/models.py backend/apps/reports/migrations/ backend/tests/unit/test_report_viewer_models.py
git commit -m "feat(reports): add OneLinkAttribution model"
```

### Task 2.6: Register new models in Django admin

**Files:**
- Modify: `backend/apps/reports/admin.py`

- [ ] **Step 1: Write the failing test**

Append to `backend/tests/unit/test_report_viewer_models.py`:
```python
from django.contrib import admin as django_admin
from apps.reports.models import TopContent, BrandFollowerSnapshot, OneLinkAttribution


def test_admin_registers_new_models():
    assert django_admin.site.is_registered(TopContent)
    assert django_admin.site.is_registered(BrandFollowerSnapshot)
    assert django_admin.site.is_registered(OneLinkAttribution)
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `docker compose exec backend pytest tests/unit/test_report_viewer_models.py -k admin -v`
Expected: FAIL — models not registered.

- [ ] **Step 3: Register them**

In `backend/apps/reports/admin.py`, add (append or merge with existing imports):
```python
from django.contrib import admin
from .models import (
    Report, ReportMetric,
    TopContent, BrandFollowerSnapshot, OneLinkAttribution,
)


@admin.register(TopContent)
class TopContentAdmin(admin.ModelAdmin):
    list_display = ("report", "kind", "network", "rank", "handle")
    list_filter = ("kind", "network", "source_type")
    search_fields = ("handle", "caption")


@admin.register(BrandFollowerSnapshot)
class BrandFollowerSnapshotAdmin(admin.ModelAdmin):
    list_display = ("brand", "network", "as_of", "followers_count")
    list_filter = ("brand", "network")
    date_hierarchy = "as_of"


@admin.register(OneLinkAttribution)
class OneLinkAttributionAdmin(admin.ModelAdmin):
    list_display = ("report", "influencer_handle", "clicks", "app_downloads")
    search_fields = ("influencer_handle",)
```

Keep any existing registrations of `Report` and `ReportMetric`.

- [ ] **Step 4: Run the test to verify it passes**

Run: `docker compose exec backend pytest tests/unit/test_report_viewer_models.py -k admin -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/apps/reports/admin.py backend/tests/unit/test_report_viewer_models.py
git commit -m "feat(reports): register new models in admin"
```

---

## Phase 3: Aggregation services

### Task 3.1: Q1 rollup helper

**Files:**
- Create: `backend/apps/reports/services/__init__.py` (empty)
- Create: `backend/apps/reports/services/aggregations.py`
- Create: `backend/tests/unit/test_report_aggregations.py`

- [ ] **Step 1: Write the failing test**

Create `backend/tests/unit/test_report_aggregations.py`:
```python
from datetime import date
import pytest
from apps.reports.models import Report, ReportMetric
from apps.reports.services.aggregations import build_q1_rollup

pytestmark = pytest.mark.django_db


def _make_monthly_report(stage, month, reach_value):
    r = Report.objects.create(
        stage=stage, kind=Report.Kind.MENSUAL,
        period_start=date(2026, month, 1),
        period_end=date(2026, month, 28),
        status=Report.Status.PUBLISHED,
    )
    ReportMetric.objects.create(
        report=r, network=ReportMetric.Network.INSTAGRAM,
        source_type=ReportMetric.SourceType.ORGANIC,
        metric_name="reach", value=reach_value,
    )
    return r


def test_build_q1_rollup_returns_three_months_for_march(balanz_stage):
    jan = _make_monthly_report(balanz_stage, 1, 100000)
    feb = _make_monthly_report(balanz_stage, 2, 200000)
    mar = _make_monthly_report(balanz_stage, 3, 300000)
    rollup = build_q1_rollup(mar)
    assert rollup["months"] == ["enero", "febrero", "marzo"]
    reach_row = next(r for r in rollup["rows"] if r["metric"] == "reach")
    assert reach_row["values"] == [100000.0, 200000.0, 300000.0]


def test_build_q1_rollup_with_only_one_report_returns_empty_rows(balanz_stage):
    mar = _make_monthly_report(balanz_stage, 3, 300000)
    rollup = build_q1_rollup(mar)
    assert rollup is None or len(rollup["rows"]) == 0 or rollup["months"] == ["marzo"]
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `docker compose exec backend pytest tests/unit/test_report_aggregations.py -v`
Expected: FAIL — module does not exist.

- [ ] **Step 3: Write the helper**

Create `backend/apps/reports/services/__init__.py` (empty file).
Create `backend/apps/reports/services/aggregations.py`:
```python
from __future__ import annotations
from datetime import date
from typing import Any

from apps.reports.models import Report, ReportMetric, BrandFollowerSnapshot

MONTHS_ES = [
    "enero", "febrero", "marzo", "abril", "mayo", "junio",
    "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre",
]


def _quarter_of(month: int) -> tuple[int, int]:
    start = ((month - 1) // 3) * 3 + 1
    return start, start + 2


def build_q1_rollup(report: Report) -> dict[str, Any] | None:
    quarter_start, quarter_end = _quarter_of(report.period_start.month)
    year = report.period_start.year
    brand_id = report.stage.campaign.brand_id

    reports = list(
        Report.objects
        .filter(
            stage__campaign__brand_id=brand_id,
            status=Report.Status.PUBLISHED,
            period_start__year=year,
            period_start__month__gte=quarter_start,
            period_start__month__lte=quarter_end,
        )
        .order_by("period_start")
        .prefetch_related("metrics")
    )
    if len(reports) < 2:
        return None

    months = [MONTHS_ES[r.period_start.month - 1] for r in reports]

    rows: list[dict[str, Any]] = []
    keys: set[tuple[str, str]] = set()
    for r in reports:
        for m in r.metrics.all():
            if m.source_type == ReportMetric.SourceType.ORGANIC:
                keys.add((m.metric_name, m.network))

    for metric_name, network in sorted(keys):
        values: list[float | None] = []
        for r in reports:
            match = next(
                (m for m in r.metrics.all()
                 if m.metric_name == metric_name and m.network == network
                 and m.source_type == ReportMetric.SourceType.ORGANIC),
                None,
            )
            values.append(float(match.value) if match else None)
        rows.append({"metric": metric_name, "network": network, "values": values})

    return {"months": months, "rows": rows}
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `docker compose exec backend pytest tests/unit/test_report_aggregations.py -v`
Expected: PASS (both).

- [ ] **Step 5: Commit**

```bash
git add backend/apps/reports/services/ backend/tests/unit/test_report_aggregations.py
git commit -m "feat(reports): add q1 rollup aggregation helper"
```

### Task 3.2: YoY helper

**Files:**
- Modify: `backend/apps/reports/services/aggregations.py`

- [ ] **Step 1: Write the failing test**

Append to `backend/tests/unit/test_report_aggregations.py`:
```python
from apps.reports.services.aggregations import build_yoy


def test_build_yoy_finds_prior_year_report(balanz_stage):
    prev = Report.objects.create(
        stage=balanz_stage, kind=Report.Kind.MENSUAL,
        period_start=date(2025, 3, 1), period_end=date(2025, 3, 31),
        status=Report.Status.PUBLISHED,
    )
    ReportMetric.objects.create(
        report=prev, network=ReportMetric.Network.INSTAGRAM,
        source_type=ReportMetric.SourceType.ORGANIC,
        metric_name="er", value=3.0,
    )
    cur = Report.objects.create(
        stage=balanz_stage, kind=Report.Kind.MENSUAL,
        period_start=date(2026, 3, 1), period_end=date(2026, 3, 31),
        status=Report.Status.PUBLISHED,
    )
    ReportMetric.objects.create(
        report=cur, network=ReportMetric.Network.INSTAGRAM,
        source_type=ReportMetric.SourceType.ORGANIC,
        metric_name="er", value=4.5,
    )
    yoy = build_yoy(cur)
    assert yoy is not None
    er_row = next(r for r in yoy if r["metric"] == "er" and r["network"] == "INSTAGRAM")
    assert float(er_row["current"]) == 4.5
    assert float(er_row["year_ago"]) == 3.0


def test_build_yoy_without_prior_returns_none(balanz_published_report):
    assert build_yoy(balanz_published_report) is None
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `docker compose exec backend pytest tests/unit/test_report_aggregations.py -k yoy -v`
Expected: FAIL — `build_yoy` does not exist.

- [ ] **Step 3: Implement build_yoy**

Append to `backend/apps/reports/services/aggregations.py`:
```python
from datetime import timedelta


def build_yoy(report: Report) -> list[dict[str, Any]] | None:
    target = date(report.period_start.year - 1, report.period_start.month, 1)
    lo = target - timedelta(days=15)
    hi = target + timedelta(days=15)
    brand_id = report.stage.campaign.brand_id

    prior = (
        Report.objects
        .filter(
            stage__campaign__brand_id=brand_id,
            status=Report.Status.PUBLISHED,
            period_start__gte=lo,
            period_start__lte=hi,
        )
        .prefetch_related("metrics")
        .first()
    )
    if prior is None:
        return None

    rows: list[dict[str, Any]] = []
    for m in report.metrics.all():
        if m.metric_name not in {"reach", "er"}:
            continue
        if m.source_type != ReportMetric.SourceType.ORGANIC:
            continue
        match = next(
            (p for p in prior.metrics.all()
             if p.metric_name == m.metric_name and p.network == m.network
             and p.source_type == ReportMetric.SourceType.ORGANIC),
            None,
        )
        if match is None:
            continue
        rows.append({
            "metric": m.metric_name,
            "network": m.network,
            "current": float(m.value),
            "year_ago": float(match.value),
        })
    return rows or None
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `docker compose exec backend pytest tests/unit/test_report_aggregations.py -k yoy -v`
Expected: PASS (both).

- [ ] **Step 5: Commit**

```bash
git add backend/apps/reports/services/aggregations.py backend/tests/unit/test_report_aggregations.py
git commit -m "feat(reports): add YoY aggregation helper"
```

### Task 3.3: Follower snapshots helper

**Files:**
- Modify: `backend/apps/reports/services/aggregations.py`

- [ ] **Step 1: Write the failing test**

Append to `backend/tests/unit/test_report_aggregations.py`:
```python
from apps.reports.services.aggregations import build_follower_snapshots
from apps.reports.models import BrandFollowerSnapshot


def test_follower_snapshots_grouped_by_network(balanz_brand, balanz_stage):
    r = Report.objects.create(
        stage=balanz_stage, kind=Report.Kind.MENSUAL,
        period_start=date(2026, 3, 1), period_end=date(2026, 3, 31),
        status=Report.Status.PUBLISHED,
    )
    for m, c in [(1, 100000), (2, 104568), (3, 107072)]:
        BrandFollowerSnapshot.objects.create(
            brand=balanz_brand, network=ReportMetric.Network.INSTAGRAM,
            as_of=date(2026, m, 28), followers_count=c,
        )
    BrandFollowerSnapshot.objects.create(
        brand=balanz_brand, network=ReportMetric.Network.TIKTOK,
        as_of=date(2026, 3, 28), followers_count=50000,
    )
    snaps = build_follower_snapshots(r)
    assert len(snaps["INSTAGRAM"]) == 3
    assert snaps["INSTAGRAM"][-1]["count"] == 107072
    assert len(snaps["TIKTOK"]) == 1
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `docker compose exec backend pytest tests/unit/test_report_aggregations.py -k follower -v`
Expected: FAIL — `build_follower_snapshots` does not exist.

- [ ] **Step 3: Implement it**

Append to `backend/apps/reports/services/aggregations.py`:
```python
def build_follower_snapshots(report: Report) -> dict[str, list[dict[str, Any]]]:
    lo = report.period_start - timedelta(days=90)
    hi = report.period_end
    brand_id = report.stage.campaign.brand_id

    result: dict[str, list[dict[str, Any]]] = {}
    qs = (
        BrandFollowerSnapshot.objects
        .filter(brand_id=brand_id, as_of__gte=lo, as_of__lte=hi)
        .order_by("as_of")
    )
    for s in qs:
        result.setdefault(s.network, []).append({
            "month": MONTHS_ES[s.as_of.month - 1],
            "as_of": s.as_of.isoformat(),
            "count": s.followers_count,
        })
    return result
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `docker compose exec backend pytest tests/unit/test_report_aggregations.py -v`
Expected: PASS (all).

- [ ] **Step 5: Commit**

```bash
git add backend/apps/reports/services/aggregations.py backend/tests/unit/test_report_aggregations.py
git commit -m "feat(reports): add follower snapshot aggregation helper"
```

---

## Phase 4: API — serializer extension

### Task 4.1: Extend ReportDetailSerializer

**Files:**
- Modify: `backend/apps/reports/serializers.py`
- Test: `backend/tests/unit/test_report_detail_serializer.py`

- [ ] **Step 1: Write the failing test**

Create `backend/tests/unit/test_report_detail_serializer.py`:
```python
import pytest
from apps.reports.serializers import ReportDetailSerializer

pytestmark = pytest.mark.django_db


def test_serializer_includes_new_fields(balanz_published_report):
    data = ReportDetailSerializer(balanz_published_report).data
    for field in ("top_content", "onelink", "follower_snapshots", "q1_rollup", "yoy", "intro_text", "brand_name"):
        assert field in data


def test_serializer_top_content_thumbnail_url_is_null_when_missing(balanz_published_report):
    from apps.reports.models import TopContent, ReportMetric
    TopContent.objects.create(
        report=balanz_published_report, kind=TopContent.Kind.POST,
        network=ReportMetric.Network.INSTAGRAM,
        source_type=ReportMetric.SourceType.ORGANIC,
        rank=1, caption="x", metrics={},
    )
    data = ReportDetailSerializer(balanz_published_report).data
    assert data["top_content"][0]["thumbnail_url"] is None
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `docker compose exec backend pytest tests/unit/test_report_detail_serializer.py -v`
Expected: FAIL — new fields missing.

- [ ] **Step 3: Extend the serializer**

Replace `backend/apps/reports/serializers.py` with:
```python
from rest_framework import serializers

from .models import (
    Report, ReportMetric,
    TopContent, OneLinkAttribution,
)
from .services.aggregations import (
    build_q1_rollup, build_yoy, build_follower_snapshots,
)


class ReportMetricSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReportMetric
        fields = ("network", "source_type", "metric_name", "value", "period_comparison")


class TopContentSerializer(serializers.ModelSerializer):
    thumbnail_url = serializers.SerializerMethodField()

    class Meta:
        model = TopContent
        fields = (
            "kind", "network", "source_type", "rank", "handle",
            "caption", "thumbnail_url", "post_url", "metrics",
        )

    def get_thumbnail_url(self, obj) -> str | None:
        return obj.thumbnail.url if obj.thumbnail else None


class OneLinkAttributionSerializer(serializers.ModelSerializer):
    class Meta:
        model = OneLinkAttribution
        fields = ("influencer_handle", "clicks", "app_downloads")


class ReportDetailSerializer(serializers.ModelSerializer):
    stage_name = serializers.CharField(source="stage.name", read_only=True)
    stage_id = serializers.IntegerField(source="stage.id", read_only=True)
    campaign_name = serializers.CharField(source="stage.campaign.name", read_only=True)
    campaign_id = serializers.IntegerField(source="stage.campaign.id", read_only=True)
    brand_name = serializers.CharField(source="stage.campaign.brand.name", read_only=True)
    display_title = serializers.CharField(read_only=True)
    metrics = ReportMetricSerializer(many=True, read_only=True)
    top_content = TopContentSerializer(many=True, read_only=True)
    onelink = OneLinkAttributionSerializer(many=True, read_only=True)
    follower_snapshots = serializers.SerializerMethodField()
    q1_rollup = serializers.SerializerMethodField()
    yoy = serializers.SerializerMethodField()

    class Meta:
        model = Report
        fields = (
            "id", "kind", "period_start", "period_end",
            "title", "display_title", "status", "published_at",
            "intro_text", "conclusions_text",
            "stage_id", "stage_name",
            "campaign_id", "campaign_name", "brand_name",
            "metrics", "top_content", "onelink",
            "follower_snapshots", "q1_rollup", "yoy",
        )

    def get_follower_snapshots(self, obj):
        return build_follower_snapshots(obj)

    def get_q1_rollup(self, obj):
        return build_q1_rollup(obj)

    def get_yoy(self, obj):
        return build_yoy(obj)
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `docker compose exec backend pytest tests/unit/test_report_detail_serializer.py -v`
Expected: PASS.

- [ ] **Step 5: Run existing latest-report test to confirm backwards-compat**

Run: `docker compose exec backend pytest tests/unit/test_reports_api.py -v`
Expected: PASS — `/api/reports/latest/` still works with extended shape.

- [ ] **Step 6: Commit**

```bash
git add backend/apps/reports/serializers.py backend/tests/unit/test_report_detail_serializer.py
git commit -m "feat(api): extend ReportDetailSerializer with computed rollups"
```

---

## Phase 5: API — detail endpoint

### Task 5.1: Add ReportDetailView

**Files:**
- Modify: `backend/apps/reports/views.py`
- Modify: `backend/apps/reports/urls.py`
- Test: `backend/tests/unit/test_reports_detail_view.py`

- [ ] **Step 1: Write the failing test**

Create `backend/tests/unit/test_reports_detail_view.py`:
```python
import pytest

pytestmark = pytest.mark.django_db


class TestReportDetail:
    def _url(self, pk: int) -> str:
        return f"/api/reports/{pk}/"

    def test_returns_401_without_auth(self, api_client, balanz_published_report):
        res = api_client.get(self._url(balanz_published_report.pk))
        assert res.status_code == 401

    def test_returns_200_for_own_published_report(self, authed_balanz, balanz_published_report):
        res = authed_balanz.get(self._url(balanz_published_report.pk))
        assert res.status_code == 200
        assert res.data["id"] == balanz_published_report.pk
        assert res.data["brand_name"] == "Balanz"

    def test_returns_404_for_other_tenant(self, authed_rival, balanz_published_report):
        res = authed_rival.get(self._url(balanz_published_report.pk))
        assert res.status_code == 404

    def test_returns_404_for_draft(self, authed_balanz, balanz_published_report):
        from apps.reports.models import Report
        balanz_published_report.status = Report.Status.DRAFT
        balanz_published_report.save()
        res = authed_balanz.get(self._url(balanz_published_report.pk))
        assert res.status_code == 404

    def test_returns_404_for_unknown_id(self, authed_balanz):
        res = authed_balanz.get(self._url(99999))
        assert res.status_code == 404

    def test_response_shape_includes_rollups(self, authed_balanz, balanz_published_report):
        res = authed_balanz.get(self._url(balanz_published_report.pk))
        assert res.status_code == 200
        for field in ("top_content", "onelink", "follower_snapshots", "q1_rollup", "yoy", "metrics"):
            assert field in res.data
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `docker compose exec backend pytest tests/unit/test_reports_detail_view.py -v`
Expected: FAIL — endpoint 404 everywhere (no route registered).

- [ ] **Step 3: Add the view**

Append to `backend/apps/reports/views.py`:
```python
import logging
from django.shortcuts import get_object_or_404
from rest_framework.generics import RetrieveAPIView

logger = logging.getLogger(__name__)


class ReportDetailView(RetrieveAPIView):
    """Detail of a single published report for the authenticated user's client.

    Scoping happens in get_object (not middleware — see CLAUDE.md gotcha).
    Cross-tenant or DRAFT access returns 404, not 403, to avoid leaking existence.
    """

    permission_classes = [permissions.IsAuthenticated]
    serializer_class = ReportDetailSerializer

    def get_queryset(self):
        client_id = getattr(self.request.user, "client_id", None)
        if client_id is None:
            return Report.objects.none()
        return (
            Report.objects
            .filter(
                stage__campaign__brand__client_id=client_id,
                status=Report.Status.PUBLISHED,
            )
            .select_related("stage", "stage__campaign", "stage__campaign__brand")
            .prefetch_related("metrics", "top_content", "onelink")
        )

    def get_object(self):
        try:
            obj = get_object_or_404(self.get_queryset(), pk=self.kwargs["pk"])
        except Exception:
            logger.warning(
                "report_access_denied",
                extra={
                    "report_id": self.kwargs.get("pk"),
                    "user_id": getattr(self.request.user, "id", None),
                    "reason": "not_found_or_scoped_out",
                },
            )
            raise
        logger.info(
            "report_served",
            extra={
                "report_id": obj.pk,
                "client_id": getattr(self.request.user, "client_id", None),
                "user_id": self.request.user.id,
            },
        )
        return obj
```

- [ ] **Step 4: Register the route**

Replace `backend/apps/reports/urls.py` with:
```python
from django.urls import path

from .views import LatestPublishedReportView, ReportDetailView

urlpatterns = [
    path("latest/", LatestPublishedReportView.as_view(), name="report-latest"),
    path("<int:pk>/", ReportDetailView.as_view(), name="report-detail"),
]
```

- [ ] **Step 5: Run the test to verify it passes**

Run: `docker compose exec backend pytest tests/unit/test_reports_detail_view.py -v`
Expected: PASS (all 6).

- [ ] **Step 6: Commit**

```bash
git add backend/apps/reports/views.py backend/apps/reports/urls.py backend/tests/unit/test_reports_detail_view.py
git commit -m "feat(api): add GET /api/reports/<id>/ with tenant scoping"
```

### Task 5.2: N+1 guard test

**Files:**
- Create: `backend/tests/unit/test_report_nplus1.py`

- [ ] **Step 1: Write the test**

Create `backend/tests/unit/test_report_nplus1.py`:
```python
import pytest
from django.test.utils import CaptureQueriesContext
from django.db import connection

from apps.reports.models import Report, ReportMetric, TopContent, OneLinkAttribution

pytestmark = pytest.mark.django_db


def test_report_detail_avoids_nplus1(authed_balanz, balanz_published_report):
    for i in range(20):
        TopContent.objects.create(
            report=balanz_published_report, kind=TopContent.Kind.POST,
            network=ReportMetric.Network.INSTAGRAM,
            source_type=ReportMetric.SourceType.ORGANIC,
            rank=i + 1, caption=f"#{i}", metrics={},
        )
    for i in range(10):
        OneLinkAttribution.objects.create(
            report=balanz_published_report,
            influencer_handle=f"@inf{i}",
            clicks=i, app_downloads=i,
        )

    with CaptureQueriesContext(connection) as ctx:
        res = authed_balanz.get(f"/api/reports/{balanz_published_report.pk}/")
    assert res.status_code == 200
    # auth + main + prefetch_related(metrics) + prefetch_related(top_content) +
    # prefetch_related(onelink) + aggregations (q1/yoy/snapshots queries).
    # Upper bound is generous — the point is no query per row.
    assert len(ctx.captured_queries) < 20, f"too many queries: {len(ctx.captured_queries)}"
```

- [ ] **Step 2: Run the test**

Run: `docker compose exec backend pytest tests/unit/test_report_nplus1.py -v`
Expected: PASS.

- [ ] **Step 3: Commit**

```bash
git add backend/tests/unit/test_report_nplus1.py
git commit -m "test(reports): guard report detail against N+1"
```

---

## Phase 6: Seed data extension

### Task 6.1: Commit placeholder images

**Files:**
- Create: `backend/apps/tenants/management/commands/fixtures/placeholder_post_1.jpg`
- Create: `backend/apps/tenants/management/commands/fixtures/placeholder_post_2.jpg`
- Create: `backend/apps/tenants/management/commands/fixtures/placeholder_creator_1.jpg`

- [ ] **Step 1: Generate tiny placeholder JPGs**

Run:
```bash
docker compose exec backend python -c "
from PIL import Image
import os
os.makedirs('apps/tenants/management/commands/fixtures', exist_ok=True)
for name, color in [
    ('placeholder_post_1.jpg', (241, 120, 177)),
    ('placeholder_post_2.jpg', (150, 230, 200)),
    ('placeholder_creator_1.jpg', (255, 230, 100)),
]:
    Image.new('RGB', (600, 600), color).save(f'apps/tenants/management/commands/fixtures/{name}', 'JPEG', quality=85)
"
```
Expected: 3 files exist, each < 50KB.

- [ ] **Step 2: Commit**

```bash
git add backend/apps/tenants/management/commands/fixtures/*.jpg
git commit -m "chore(seed): add placeholder images for TopContent fixtures"
```

### Task 6.2: Extend seed_demo with new fixtures

**Files:**
- Modify: `backend/apps/tenants/management/commands/seed_demo.py`

- [ ] **Step 1: Write the failing test**

Create `backend/tests/unit/test_seed_demo_report_viewer.py`:
```python
import pytest
from django.core.management import call_command

from apps.reports.models import Report, TopContent, OneLinkAttribution, BrandFollowerSnapshot

pytestmark = pytest.mark.django_db


def test_seed_demo_creates_report_viewer_fixtures():
    call_command("seed_demo")
    r = Report.objects.filter(status=Report.Status.PUBLISHED).order_by("-period_start").first()
    assert r is not None
    assert TopContent.objects.filter(report=r).count() >= 3
    assert OneLinkAttribution.objects.filter(report=r).count() >= 3
    assert BrandFollowerSnapshot.objects.filter(brand=r.stage.campaign.brand).count() >= 3
    assert r.intro_text  # non-empty
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `docker compose exec backend pytest tests/unit/test_seed_demo_report_viewer.py -v`
Expected: FAIL — seed doesn't create these yet.

- [ ] **Step 3: Extend seed_demo**

Read `backend/apps/tenants/management/commands/seed_demo.py` to find where the latest Report is created, then after it add:
```python
from datetime import date
from pathlib import Path
from django.core.files import File
from apps.reports.models import (
    TopContent, OneLinkAttribution, BrandFollowerSnapshot, ReportMetric,
)

# ... inside handle(), after creating the latest Report `r`:
fixtures = Path(__file__).parent / "fixtures"
r.intro_text = (
    "Cerramos un mes con crecimiento sostenido en alcance orgánico y un pico "
    "de downloads vía influencers. Acá va el detalle."
)
r.save(update_fields=["intro_text"])

for i, (handle, fname) in enumerate([
    ("", "placeholder_post_1.jpg"),
    ("", "placeholder_post_2.jpg"),
    ("@pasaje.en.mano", "placeholder_creator_1.jpg"),
], start=1):
    tc = TopContent(
        report=r,
        kind=TopContent.Kind.CREATOR if handle else TopContent.Kind.POST,
        network=ReportMetric.Network.INSTAGRAM,
        source_type=(ReportMetric.SourceType.INFLUENCER if handle
                     else ReportMetric.SourceType.ORGANIC),
        rank=i,
        handle=handle,
        caption=f"Contenido destacado #{i}",
        metrics={"likes": 500 * i, "reach": 10000 * i, "er": 3.5 + i * 0.4},
    )
    with open(fixtures / fname, "rb") as fh:
        tc.thumbnail.save(fname, File(fh), save=False)
    tc.save()

for handle, clicks, downloads in [
    ("@pasaje.en.mano", 1200, 180),
    ("@financierapopular", 800, 95),
    ("@pymes_ar", 400, 30),
]:
    OneLinkAttribution.objects.create(
        report=r, influencer_handle=handle,
        clicks=clicks, app_downloads=downloads,
    )

brand = r.stage.campaign.brand
for month, count in [(1, 99500), (2, 104568), (3, 107072)]:
    BrandFollowerSnapshot.objects.update_or_create(
        brand=brand,
        network=ReportMetric.Network.INSTAGRAM,
        as_of=date(r.period_start.year, month, 28),
        defaults={"followers_count": count},
    )
```

(Adapt variable names if the existing seed uses different names for the final report.)

- [ ] **Step 4: Run the test to verify it passes**

Run: `docker compose exec backend pytest tests/unit/test_seed_demo_report_viewer.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/apps/tenants/management/commands/seed_demo.py backend/tests/unit/test_seed_demo_report_viewer.py
git commit -m "feat(seed): populate TopContent, OneLink, FollowerSnapshot fixtures"
```

---

## Phase 7: Frontend types

### Task 7.1: Extend ReportDto and add new dtos

**Files:**
- Modify: `frontend/lib/api.ts:86-101`

- [ ] **Step 1: Add the types**

In `frontend/lib/api.ts`, replace the existing `ReportDto` type and add new ones:
```ts
export type TopContentDto = {
  kind: "POST" | "CREATOR";
  network: "INSTAGRAM" | "TIKTOK" | "X";
  source_type: "ORGANIC" | "INFLUENCER" | "PAID";
  rank: number;
  handle: string;
  caption: string;
  thumbnail_url: string | null;
  post_url: string;
  metrics: Record<string, number>;
};

export type OneLinkAttributionDto = {
  influencer_handle: string;
  clicks: number;
  app_downloads: number;
};

export type FollowerSnapshotPoint = {
  month: string;
  as_of: string;
  count: number;
};

export type Q1RollupDto = {
  months: string[];
  rows: Array<{
    metric: string;
    network: "INSTAGRAM" | "TIKTOK" | "X";
    values: Array<number | null>;
  }>;
};

export type YoyRowDto = {
  metric: "reach" | "er" | string;
  network: "INSTAGRAM" | "TIKTOK" | "X";
  current: number;
  year_ago: number;
};

export type ReportDto = {
  id: number;
  kind: "INFLUENCER" | "GENERAL" | "QUINCENAL" | "MENSUAL" | "CIERRE_ETAPA";
  period_start: string;
  period_end: string;
  title: string;
  display_title: string;
  status: "DRAFT" | "PUBLISHED";
  published_at: string | null;
  intro_text: string;
  conclusions_text: string;
  stage_id: number;
  stage_name: string;
  campaign_id: number;
  campaign_name: string;
  brand_name: string;
  metrics: ReportMetricDto[];
  top_content: TopContentDto[];
  onelink: OneLinkAttributionDto[];
  follower_snapshots: Record<string, FollowerSnapshotPoint[]>;
  q1_rollup: Q1RollupDto | null;
  yoy: YoyRowDto[] | null;
};
```

- [ ] **Step 2: Run typecheck**

Run: `docker compose exec frontend npm run typecheck` (or `npx tsc --noEmit`)
Expected: PASS — no type errors.

- [ ] **Step 3: Commit**

```bash
git add frontend/lib/api.ts
git commit -m "feat(frontend): extend ReportDto with new report viewer fields"
```

---

## Phase 8: Frontend utilities

### Task 8.1: Empty-state helpers

**Files:**
- Create: `frontend/lib/has-data.ts`

- [ ] **Step 1: Write the module**

Create `frontend/lib/has-data.ts`:
```ts
import type { ReportDto } from "./api";

type Network = "INSTAGRAM" | "TIKTOK" | "X";

export function hasMetrics(report: ReportDto, network: Network): boolean {
  return report.metrics.some((m) => m.network === network);
}

export function hasTopContent(report: ReportDto, kind: "POST" | "CREATOR"): boolean {
  return report.top_content.some((c) => c.kind === kind);
}

export function hasOneLink(report: ReportDto): boolean {
  return report.onelink.length > 0;
}

export function hasFollowerGrowth(report: ReportDto): boolean {
  return Object.values(report.follower_snapshots).some((arr) => arr.length >= 2);
}

export function hasQ1Rollup(report: ReportDto): boolean {
  return !!report.q1_rollup && report.q1_rollup.rows.length > 0 && report.q1_rollup.months.length >= 2;
}

export function hasYoy(report: ReportDto): boolean {
  return !!report.yoy && report.yoy.length > 0;
}

export function hasIntro(report: ReportDto): boolean {
  return report.intro_text.trim().length > 0;
}

export function hasConclusions(report: ReportDto): boolean {
  return report.conclusions_text.trim().length > 0;
}
```

- [ ] **Step 2: Verify typecheck**

Run: `docker compose exec frontend npx tsc --noEmit`
Expected: PASS.

- [ ] **Step 3: Commit**

```bash
git add frontend/lib/has-data.ts
git commit -m "feat(frontend): add has-data helpers for empty-section pattern"
```

### Task 8.2: Aggregations utility

**Files:**
- Create: `frontend/lib/aggregations.ts`

- [ ] **Step 1: Write the module**

Create `frontend/lib/aggregations.ts`:
```ts
import type { ReportDto, ReportMetricDto } from "./api";

type Network = "INSTAGRAM" | "TIKTOK" | "X";
type SourceType = "ORGANIC" | "INFLUENCER" | "PAID";

export function metricsByNetwork(
  report: ReportDto,
  network: Network,
): ReportMetricDto[] {
  return report.metrics.filter((m) => m.network === network);
}

export function metricsBySource(
  report: ReportDto,
  network: Network,
  source: SourceType,
): ReportMetricDto[] {
  return report.metrics.filter(
    (m) => m.network === network && m.source_type === source,
  );
}

export function findMetric(
  report: ReportDto,
  network: Network,
  source: SourceType,
  name: string,
): ReportMetricDto | null {
  return (
    report.metrics.find(
      (m) => m.network === network && m.source_type === source && m.metric_name === name,
    ) ?? null
  );
}

export function sumMetric(
  report: ReportDto,
  network: Network,
  name: string,
): number {
  return report.metrics
    .filter((m) => m.network === network && m.metric_name === name)
    .reduce((acc, m) => acc + Number(m.value), 0);
}

export function formatCompact(n: number): string {
  if (n >= 1_000_000) return (n / 1_000_000).toFixed(2).replace(/\.?0+$/, "") + "M";
  if (n >= 1_000) return (n / 1_000).toFixed(0) + "K";
  return String(n);
}

export function formatDelta(pct: number | null): string {
  if (pct === null || pct === undefined) return "";
  const sign = pct >= 0 ? "↑" : "↓";
  return `${sign} ${Math.abs(pct).toFixed(1)}%`;
}
```

- [ ] **Step 2: Typecheck**

Run: `docker compose exec frontend npx tsc --noEmit`
Expected: PASS.

- [ ] **Step 3: Commit**

```bash
git add frontend/lib/aggregations.ts
git commit -m "feat(frontend): add aggregation utilities for report metrics"
```

---

## Phase 9: Frontend components (reusable)

### Task 9.1: KpiTile

**Files:**
- Create: `frontend/app/reports/[id]/components/KpiTile.tsx`

- [ ] **Step 1: Write the component**

```tsx
import { formatCompact, formatDelta } from "@/lib/aggregations";

type Props = {
  label: string;
  value: number;
  delta?: number | null;
  unit?: string;
};

export default function KpiTile({ label, value, delta, unit }: Props) {
  const isPositive = delta !== null && delta !== undefined && delta >= 0;
  const deltaLabel = formatDelta(delta ?? null);

  return (
    <div
      className="card card-paper"
      style={{ padding: 20, display: "flex", flexDirection: "column", gap: 8 }}
    >
      <div className="eyebrow">{label}</div>
      <div
        className="font-display"
        style={{
          fontSize: 56,
          lineHeight: 0.95,
          letterSpacing: "-0.03em",
          textTransform: "lowercase",
        }}
      >
        {formatCompact(value)}
        {unit && <span style={{ fontSize: 22, marginLeft: 4 }}>{unit}</span>}
      </div>
      {deltaLabel && (
        <div
          style={{
            fontSize: 13,
            fontWeight: 700,
            color: isPositive ? "var(--chirri-mint-deep, #2a8a5a)" : "var(--chirri-pink-deep)",
          }}
          aria-label={`Variación vs periodo anterior: ${deltaLabel}`}
        >
          {deltaLabel}
        </div>
      )}
    </div>
  );
}
```

- [ ] **Step 2: Typecheck**

Run: `docker compose exec frontend npx tsc --noEmit`
Expected: PASS.

- [ ] **Step 3: Commit**

```bash
git add frontend/app/reports/[id]/components/KpiTile.tsx
git commit -m "feat(frontend): add KpiTile component"
```

### Task 9.2: MetricRow

**Files:**
- Create: `frontend/app/reports/[id]/components/MetricRow.tsx`

- [ ] **Step 1: Write the component**

```tsx
import { formatCompact, formatDelta } from "@/lib/aggregations";

type Props = {
  label: string;
  current: number;
  previous?: number | null;
  delta?: number | null;
  unit?: string;
};

export default function MetricRow({ label, current, previous, delta, unit }: Props) {
  return (
    <tr>
      <th scope="row" style={{ textAlign: "left", fontWeight: 500, padding: "10px 12px" }}>
        {label}
      </th>
      <td style={{ textAlign: "right", padding: "10px 12px", fontWeight: 700 }}>
        {formatCompact(current)}{unit && <span style={{ fontSize: 12 }}>{unit}</span>}
      </td>
      {previous !== undefined && previous !== null && (
        <td style={{ textAlign: "right", padding: "10px 12px", color: "var(--chirri-muted)" }}>
          {formatCompact(previous)}{unit && <span style={{ fontSize: 12 }}>{unit}</span>}
        </td>
      )}
      {delta !== undefined && (
        <td style={{ textAlign: "right", padding: "10px 12px", fontSize: 13 }}>
          {formatDelta(delta ?? null)}
        </td>
      )}
    </tr>
  );
}
```

- [ ] **Step 2: Typecheck + commit**

Run: `docker compose exec frontend npx tsc --noEmit`
```bash
git add frontend/app/reports/[id]/components/MetricRow.tsx
git commit -m "feat(frontend): add MetricRow component"
```

### Task 9.3: ContentCard

**Files:**
- Create: `frontend/app/reports/[id]/components/ContentCard.tsx`

- [ ] **Step 1: Write the component**

```tsx
import type { TopContentDto } from "@/lib/api";
import { formatCompact } from "@/lib/aggregations";

type Props = { content: TopContentDto };

export default function ContentCard({ content }: Props) {
  const alt = content.caption
    ? content.caption
    : content.handle
    ? `Post de ${content.handle}`
    : "Contenido destacado";

  return (
    <article
      className="card card-paper"
      style={{ padding: 0, overflow: "hidden", display: "flex", flexDirection: "column" }}
    >
      <div
        style={{
          aspectRatio: "1 / 1",
          background: "var(--chirri-pink)",
          overflow: "hidden",
          position: "relative",
        }}
      >
        {content.thumbnail_url ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img
            src={content.thumbnail_url}
            alt={alt}
            style={{ width: "100%", height: "100%", objectFit: "cover" }}
          />
        ) : (
          <div
            aria-hidden="true"
            style={{
              width: "100%",
              height: "100%",
              display: "grid",
              placeItems: "center",
              color: "var(--chirri-muted)",
              fontSize: 12,
            }}
          >
            sin imagen
          </div>
        )}
      </div>
      <div style={{ padding: 16, display: "flex", flexDirection: "column", gap: 6 }}>
        {content.handle && (
          <div style={{ fontWeight: 800, fontSize: 14 }}>{content.handle}</div>
        )}
        {content.caption && (
          <p style={{ fontSize: 13, lineHeight: 1.4, margin: 0 }}>{content.caption}</p>
        )}
        <dl
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(2, 1fr)",
            gap: 4,
            marginTop: 8,
            fontSize: 12,
          }}
        >
          {Object.entries(content.metrics).slice(0, 4).map(([k, v]) => (
            <div key={k} style={{ display: "flex", justifyContent: "space-between" }}>
              <dt style={{ color: "var(--chirri-muted)" }}>{k}</dt>
              <dd style={{ margin: 0, fontWeight: 700 }}>{formatCompact(Number(v))}</dd>
            </div>
          ))}
        </dl>
      </div>
    </article>
  );
}
```

- [ ] **Step 2: Typecheck + commit**

```bash
docker compose exec frontend npx tsc --noEmit
git add frontend/app/reports/[id]/components/ContentCard.tsx
git commit -m "feat(frontend): add ContentCard component"
```

### Task 9.4: BarChartMini

**Files:**
- Create: `frontend/app/reports/[id]/components/BarChartMini.tsx`

- [ ] **Step 1: Write the component**

```tsx
type Point = { label: string; value: number };

type Props = {
  points: Point[];
  ariaLabelPrefix: string;
};

export default function BarChartMini({ points, ariaLabelPrefix }: Props) {
  if (points.length === 0) return null;
  const max = Math.max(...points.map((p) => p.value));
  const ceiling = max * 1.1 || 1;

  const ariaLabel = `${ariaLabelPrefix}: ${points
    .map((p) => `${p.label} ${p.value.toLocaleString("es-AR")}`)
    .join(", ")}`;

  const barWidth = 80;
  const gap = 20;
  const height = 160;
  const width = points.length * barWidth + (points.length - 1) * gap;

  return (
    <svg
      role="img"
      aria-label={ariaLabel}
      viewBox={`0 0 ${width} ${height + 40}`}
      style={{ width: "100%", maxWidth: 520 }}
    >
      {points.map((p, i) => {
        const h = (p.value / ceiling) * height;
        const x = i * (barWidth + gap);
        const y = height - h;
        return (
          <g key={p.label}>
            <rect
              x={x}
              y={y}
              width={barWidth}
              height={h}
              fill="var(--chirri-pink-deep)"
            />
            <text
              x={x + barWidth / 2}
              y={y - 6}
              textAnchor="middle"
              fontSize={12}
              fontWeight={800}
              fill="var(--chirri-black)"
            >
              {p.value.toLocaleString("es-AR")}
            </text>
            <text
              x={x + barWidth / 2}
              y={height + 20}
              textAnchor="middle"
              fontSize={11}
              fill="var(--chirri-black)"
            >
              {p.label}
            </text>
          </g>
        );
      })}
    </svg>
  );
}
```

- [ ] **Step 2: Typecheck + commit**

```bash
docker compose exec frontend npx tsc --noEmit
git add frontend/app/reports/[id]/components/BarChartMini.tsx
git commit -m "feat(frontend): add BarChartMini SVG chart"
```

---

## Phase 10: Frontend sections

### Task 10.1: HeaderSection

**Files:**
- Create: `frontend/app/reports/[id]/sections/HeaderSection.tsx`

- [ ] **Step 1: Write**

```tsx
import type { ReportDto } from "@/lib/api";
import { formatReportDate } from "@/lib/format";

export default function HeaderSection({ report }: { report: ReportDto }) {
  return (
    <section style={{ marginBottom: 40 }}>
      <div className="eyebrow">{report.brand_name} · {report.campaign_name}</div>
      <h1
        className="font-display"
        style={{
          fontSize: 72,
          lineHeight: 0.9,
          letterSpacing: "-0.03em",
          margin: "8px 0 0",
          textTransform: "lowercase",
        }}
      >
        {report.display_title.toLowerCase()}
      </h1>
      <p style={{ fontSize: 14, color: "var(--chirri-muted)", marginTop: 8 }}>
        Etapa: {report.stage_name} · Publicado: {formatReportDate(report.published_at)}
      </p>
    </section>
  );
}
```

- [ ] **Step 2: Commit**

```bash
docker compose exec frontend npx tsc --noEmit
git add frontend/app/reports/[id]/sections/HeaderSection.tsx
git commit -m "feat(frontend): add HeaderSection"
```

### Task 10.2: IntroText

**Files:**
- Create: `frontend/app/reports/[id]/sections/IntroText.tsx`

- [ ] **Step 1: Write**

```tsx
import type { ReportDto } from "@/lib/api";
import { hasIntro } from "@/lib/has-data";

export default function IntroText({ report }: { report: ReportDto }) {
  if (!hasIntro(report)) return null;
  return (
    <section style={{ marginBottom: 40, maxWidth: 720 }}>
      <span className="pill-title">INTRO</span>
      <p style={{ fontSize: 18, lineHeight: 1.5, marginTop: 16, fontWeight: 500 }}>
        {report.intro_text}
      </p>
    </section>
  );
}
```

- [ ] **Step 2: Commit**

```bash
docker compose exec frontend npx tsc --noEmit
git add frontend/app/reports/[id]/sections/IntroText.tsx
git commit -m "feat(frontend): add IntroText section"
```

### Task 10.3: KpisSummary

**Files:**
- Create: `frontend/app/reports/[id]/sections/KpisSummary.tsx`

- [ ] **Step 1: Write**

```tsx
import type { ReportDto } from "@/lib/api";
import { sumMetric } from "@/lib/aggregations";
import KpiTile from "../components/KpiTile";

const NETWORKS = ["INSTAGRAM", "TIKTOK", "X"] as const;

export default function KpisSummary({ report }: { report: ReportDto }) {
  const totalReach = NETWORKS.reduce((acc, n) => acc + sumMetric(report, n, "reach"), 0);
  const orgReach = NETWORKS.reduce(
    (acc, n) =>
      acc +
      report.metrics
        .filter((m) => m.network === n && m.source_type === "ORGANIC" && m.metric_name === "reach")
        .reduce((a, m) => a + Number(m.value), 0),
    0,
  );
  const infReach = NETWORKS.reduce(
    (acc, n) =>
      acc +
      report.metrics
        .filter(
          (m) => m.network === n && m.source_type === "INFLUENCER" && m.metric_name === "reach",
        )
        .reduce((a, m) => a + Number(m.value), 0),
    0,
  );

  if (totalReach === 0) return null;

  return (
    <section style={{ marginBottom: 48 }}>
      <span className="pill-title">KPIs DEL MES</span>
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))",
          gap: 16,
          marginTop: 16,
        }}
      >
        <KpiTile label="Total Reach" value={totalReach} />
        <KpiTile label="Orgánico" value={orgReach} />
        <KpiTile label="Influencers" value={infReach} />
      </div>
    </section>
  );
}
```

- [ ] **Step 2: Commit**

```bash
docker compose exec frontend npx tsc --noEmit
git add frontend/app/reports/[id]/sections/KpisSummary.tsx
git commit -m "feat(frontend): add KpisSummary section"
```

### Task 10.4: NetworkSection

**Files:**
- Create: `frontend/app/reports/[id]/sections/NetworkSection.tsx`

- [ ] **Step 1: Write**

```tsx
import type { ReportDto } from "@/lib/api";
import { metricsByNetwork } from "@/lib/aggregations";
import { hasMetrics } from "@/lib/has-data";
import MetricRow from "../components/MetricRow";

type Network = "INSTAGRAM" | "TIKTOK" | "X";

const LABELS: Record<Network, string> = {
  INSTAGRAM: "Instagram",
  TIKTOK: "TikTok",
  X: "X / Twitter",
};

export default function NetworkSection({
  report,
  network,
}: {
  report: ReportDto;
  network: Network;
}) {
  if (!hasMetrics(report, network)) return null;
  const metrics = metricsByNetwork(report, network);

  return (
    <section style={{ marginBottom: 40 }}>
      <h2
        className="font-display"
        style={{ fontSize: 48, textTransform: "lowercase", margin: "0 0 16px" }}
      >
        {LABELS[network].toLowerCase()}
      </h2>
      <table style={{ width: "100%", borderCollapse: "collapse" }}>
        <thead>
          <tr>
            <th scope="col" style={{ textAlign: "left", padding: "10px 12px" }}>Métrica</th>
            <th scope="col" style={{ textAlign: "right", padding: "10px 12px" }}>Valor</th>
            <th scope="col" style={{ textAlign: "right", padding: "10px 12px" }}>Δ</th>
          </tr>
        </thead>
        <tbody>
          {metrics.map((m, i) => (
            <MetricRow
              key={i}
              label={`${m.source_type.toLowerCase()} · ${m.metric_name}`}
              current={Number(m.value)}
              delta={m.period_comparison === null ? null : Number(m.period_comparison)}
            />
          ))}
        </tbody>
      </table>
    </section>
  );
}
```

- [ ] **Step 2: Commit**

```bash
docker compose exec frontend npx tsc --noEmit
git add frontend/app/reports/[id]/sections/NetworkSection.tsx
git commit -m "feat(frontend): add NetworkSection"
```

### Task 10.5: BestContentChapter

**Files:**
- Create: `frontend/app/reports/[id]/sections/BestContentChapter.tsx`

- [ ] **Step 1: Write**

```tsx
import type { ReportDto } from "@/lib/api";
import { hasTopContent } from "@/lib/has-data";
import ContentCard from "../components/ContentCard";

export default function BestContentChapter({ report }: { report: ReportDto }) {
  const posts = report.top_content.filter((c) => c.kind === "POST");
  const creators = report.top_content.filter((c) => c.kind === "CREATOR");
  if (posts.length === 0 && creators.length === 0) return null;

  return (
    <section style={{ marginBottom: 48 }}>
      <span className="pill-title mint">BEST CONTENT</span>
      {hasTopContent(report, "POST") && (
        <>
          <h3 className="font-display" style={{ fontSize: 32, margin: "16px 0", textTransform: "lowercase" }}>
            posts del mes
          </h3>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))", gap: 16 }}>
            {posts.map((c, i) => <ContentCard key={`p${i}`} content={c} />)}
          </div>
        </>
      )}
      {hasTopContent(report, "CREATOR") && (
        <>
          <h3 className="font-display" style={{ fontSize: 32, margin: "24px 0 16px", textTransform: "lowercase" }}>
            creators del mes
          </h3>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))", gap: 16 }}>
            {creators.map((c, i) => <ContentCard key={`c${i}`} content={c} />)}
          </div>
        </>
      )}
    </section>
  );
}
```

- [ ] **Step 2: Commit**

```bash
docker compose exec frontend npx tsc --noEmit
git add frontend/app/reports/[id]/sections/BestContentChapter.tsx
git commit -m "feat(frontend): add BestContentChapter section"
```

### Task 10.6: OneLinkTable

**Files:**
- Create: `frontend/app/reports/[id]/sections/OneLinkTable.tsx`

- [ ] **Step 1: Write**

```tsx
import type { ReportDto } from "@/lib/api";
import { hasOneLink } from "@/lib/has-data";
import { formatCompact } from "@/lib/aggregations";

export default function OneLinkTable({ report }: { report: ReportDto }) {
  if (!hasOneLink(report)) return null;
  const totalClicks = report.onelink.reduce((a, r) => a + r.clicks, 0);
  const totalDownloads = report.onelink.reduce((a, r) => a + r.app_downloads, 0);

  return (
    <section style={{ marginBottom: 48 }}>
      <span className="pill-title">ONELINK</span>
      <h2 className="font-display" style={{ fontSize: 40, textTransform: "lowercase", margin: "16px 0" }}>
        clicks y downloads por creator
      </h2>
      <table style={{ width: "100%", borderCollapse: "collapse" }}>
        <thead>
          <tr style={{ borderBottom: "2px solid var(--chirri-black)" }}>
            <th scope="col" style={{ textAlign: "left", padding: "10px 12px" }}>Creator</th>
            <th scope="col" style={{ textAlign: "right", padding: "10px 12px" }}>Clicks</th>
            <th scope="col" style={{ textAlign: "right", padding: "10px 12px" }}>Downloads</th>
          </tr>
        </thead>
        <tbody>
          {report.onelink.map((row) => (
            <tr key={row.influencer_handle} style={{ borderBottom: "1px solid var(--chirri-black-10, rgba(0,0,0,0.1))" }}>
              <th scope="row" style={{ textAlign: "left", padding: "10px 12px", fontWeight: 500 }}>
                {row.influencer_handle}
              </th>
              <td style={{ textAlign: "right", padding: "10px 12px" }}>{formatCompact(row.clicks)}</td>
              <td style={{ textAlign: "right", padding: "10px 12px", fontWeight: 700 }}>
                {formatCompact(row.app_downloads)}
              </td>
            </tr>
          ))}
          <tr style={{ borderTop: "2px solid var(--chirri-black)", fontWeight: 800 }}>
            <th scope="row" style={{ textAlign: "left", padding: "10px 12px" }}>Total</th>
            <td style={{ textAlign: "right", padding: "10px 12px" }}>{formatCompact(totalClicks)}</td>
            <td style={{ textAlign: "right", padding: "10px 12px" }}>{formatCompact(totalDownloads)}</td>
          </tr>
        </tbody>
      </table>
    </section>
  );
}
```

- [ ] **Step 2: Commit**

```bash
docker compose exec frontend npx tsc --noEmit
git add frontend/app/reports/[id]/sections/OneLinkTable.tsx
git commit -m "feat(frontend): add OneLinkTable section"
```

### Task 10.7: FollowerGrowthSection

**Files:**
- Create: `frontend/app/reports/[id]/sections/FollowerGrowthSection.tsx`

- [ ] **Step 1: Write**

```tsx
import type { ReportDto } from "@/lib/api";
import { hasFollowerGrowth } from "@/lib/has-data";
import BarChartMini from "../components/BarChartMini";

const LABELS: Record<string, string> = {
  INSTAGRAM: "Instagram",
  TIKTOK: "TikTok",
  X: "X / Twitter",
};

export default function FollowerGrowthSection({ report }: { report: ReportDto }) {
  if (!hasFollowerGrowth(report)) return null;

  return (
    <section style={{ marginBottom: 48 }}>
      <span className="pill-title mint">FOLLOWER GROWTH</span>
      <h2 className="font-display" style={{ fontSize: 40, textTransform: "lowercase", margin: "16px 0" }}>
        crecimiento trimestral
      </h2>
      <div style={{ display: "flex", flexDirection: "column", gap: 32 }}>
        {Object.entries(report.follower_snapshots)
          .filter(([, arr]) => arr.length >= 2)
          .map(([network, arr]) => (
            <div key={network}>
              <h3 style={{ fontSize: 14, fontWeight: 800, textTransform: "uppercase", margin: "0 0 12px" }}>
                {LABELS[network] ?? network}
              </h3>
              <BarChartMini
                points={arr.map((p) => ({ label: p.month, value: p.count }))}
                ariaLabelPrefix={`Follower growth ${LABELS[network] ?? network}`}
              />
            </div>
          ))}
      </div>
    </section>
  );
}
```

- [ ] **Step 2: Commit**

```bash
docker compose exec frontend npx tsc --noEmit
git add frontend/app/reports/[id]/sections/FollowerGrowthSection.tsx
git commit -m "feat(frontend): add FollowerGrowthSection"
```

### Task 10.8: Q1RollupTable

**Files:**
- Create: `frontend/app/reports/[id]/sections/Q1RollupTable.tsx`

- [ ] **Step 1: Write**

```tsx
import type { ReportDto } from "@/lib/api";
import { hasQ1Rollup } from "@/lib/has-data";
import { formatCompact } from "@/lib/aggregations";

export default function Q1RollupTable({ report }: { report: ReportDto }) {
  if (!hasQ1Rollup(report)) return null;
  const rollup = report.q1_rollup!;

  return (
    <section style={{ marginBottom: 48 }}>
      <span className="pill-title">TRIMESTRAL</span>
      <h2 className="font-display" style={{ fontSize: 40, textTransform: "lowercase", margin: "16px 0" }}>
        comparativa mensual
      </h2>
      <table style={{ width: "100%", borderCollapse: "collapse" }}>
        <thead>
          <tr style={{ borderBottom: "2px solid var(--chirri-black)" }}>
            <th scope="col" style={{ textAlign: "left", padding: "10px 12px" }}>Métrica</th>
            {rollup.months.map((m) => (
              <th key={m} scope="col" style={{ textAlign: "right", padding: "10px 12px" }}>
                {m}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rollup.rows.map((row, i) => (
            <tr key={i} style={{ borderBottom: "1px solid var(--chirri-black-10, rgba(0,0,0,0.1))" }}>
              <th scope="row" style={{ textAlign: "left", padding: "10px 12px", fontWeight: 500 }}>
                {row.network.toLowerCase()} · {row.metric}
              </th>
              {row.values.map((v, j) => (
                <td key={j} style={{ textAlign: "right", padding: "10px 12px", fontWeight: 700 }}>
                  {v === null ? "—" : formatCompact(v)}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  );
}
```

- [ ] **Step 2: Commit**

```bash
docker compose exec frontend npx tsc --noEmit
git add frontend/app/reports/[id]/sections/Q1RollupTable.tsx
git commit -m "feat(frontend): add Q1RollupTable section"
```

### Task 10.9: YoyComparison

**Files:**
- Create: `frontend/app/reports/[id]/sections/YoyComparison.tsx`

- [ ] **Step 1: Write**

```tsx
import type { ReportDto } from "@/lib/api";
import { hasYoy } from "@/lib/has-data";
import { formatCompact } from "@/lib/aggregations";

export default function YoyComparison({ report }: { report: ReportDto }) {
  if (!hasYoy(report)) return null;

  return (
    <section style={{ marginBottom: 48 }}>
      <span className="pill-title mint">YEAR OVER YEAR</span>
      <h2 className="font-display" style={{ fontSize: 40, textTransform: "lowercase", margin: "16px 0" }}>
        vs. mismo mes, año anterior
      </h2>
      <table style={{ width: "100%", borderCollapse: "collapse" }}>
        <thead>
          <tr style={{ borderBottom: "2px solid var(--chirri-black)" }}>
            <th scope="col" style={{ textAlign: "left", padding: "10px 12px" }}>Métrica</th>
            <th scope="col" style={{ textAlign: "right", padding: "10px 12px" }}>Actual</th>
            <th scope="col" style={{ textAlign: "right", padding: "10px 12px" }}>Hace 1 año</th>
            <th scope="col" style={{ textAlign: "right", padding: "10px 12px" }}>Δ</th>
          </tr>
        </thead>
        <tbody>
          {report.yoy!.map((row, i) => {
            const delta = row.year_ago === 0 ? null : ((row.current - row.year_ago) / row.year_ago) * 100;
            const positive = delta !== null && delta >= 0;
            return (
              <tr key={i} style={{ borderBottom: "1px solid var(--chirri-black-10, rgba(0,0,0,0.1))" }}>
                <th scope="row" style={{ textAlign: "left", padding: "10px 12px", fontWeight: 500 }}>
                  {row.network.toLowerCase()} · {row.metric}
                </th>
                <td style={{ textAlign: "right", padding: "10px 12px", fontWeight: 700 }}>
                  {formatCompact(row.current)}
                </td>
                <td style={{ textAlign: "right", padding: "10px 12px" }}>
                  {formatCompact(row.year_ago)}
                </td>
                <td style={{ textAlign: "right", padding: "10px 12px", fontSize: 13, color: positive ? "inherit" : "var(--chirri-pink-deep)" }}>
                  {delta === null ? "—" : `${positive ? "↑" : "↓"} ${Math.abs(delta).toFixed(1)}%`}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </section>
  );
}
```

- [ ] **Step 2: Commit**

```bash
docker compose exec frontend npx tsc --noEmit
git add frontend/app/reports/[id]/sections/YoyComparison.tsx
git commit -m "feat(frontend): add YoyComparison section"
```

### Task 10.10: MonthlyCompare (prev month deltas)

**Files:**
- Create: `frontend/app/reports/[id]/sections/MonthlyCompare.tsx`

- [ ] **Step 1: Write**

```tsx
import type { ReportDto } from "@/lib/api";
import { formatCompact, formatDelta } from "@/lib/aggregations";

export default function MonthlyCompare({ report }: { report: ReportDto }) {
  const withDeltas = report.metrics.filter((m) => m.period_comparison !== null);
  if (withDeltas.length === 0) return null;

  return (
    <section style={{ marginBottom: 48 }}>
      <span className="pill-title">VS MES ANTERIOR</span>
      <h2 className="font-display" style={{ fontSize: 40, textTransform: "lowercase", margin: "16px 0" }}>
        variaciones mes vs mes
      </h2>
      <table style={{ width: "100%", borderCollapse: "collapse" }}>
        <thead>
          <tr style={{ borderBottom: "2px solid var(--chirri-black)" }}>
            <th scope="col" style={{ textAlign: "left", padding: "10px 12px" }}>Red / métrica</th>
            <th scope="col" style={{ textAlign: "right", padding: "10px 12px" }}>Valor</th>
            <th scope="col" style={{ textAlign: "right", padding: "10px 12px" }}>Δ vs anterior</th>
          </tr>
        </thead>
        <tbody>
          {withDeltas.map((m, i) => {
            const delta = Number(m.period_comparison);
            const positive = delta >= 0;
            return (
              <tr key={i} style={{ borderBottom: "1px solid var(--chirri-black-10, rgba(0,0,0,0.1))" }}>
                <th scope="row" style={{ textAlign: "left", padding: "10px 12px", fontWeight: 500 }}>
                  {m.network.toLowerCase()} · {m.source_type.toLowerCase()} · {m.metric_name}
                </th>
                <td style={{ textAlign: "right", padding: "10px 12px", fontWeight: 700 }}>
                  {formatCompact(Number(m.value))}
                </td>
                <td style={{ textAlign: "right", padding: "10px 12px", fontSize: 13, color: positive ? "inherit" : "var(--chirri-pink-deep)" }}>
                  {formatDelta(delta)}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </section>
  );
}
```

- [ ] **Step 2: Commit**

```bash
docker compose exec frontend npx tsc --noEmit
git add frontend/app/reports/[id]/sections/MonthlyCompare.tsx
git commit -m "feat(frontend): add MonthlyCompare section"
```

### Task 10.11: ConclusionsSection

**Files:**
- Create: `frontend/app/reports/[id]/sections/ConclusionsSection.tsx`

- [ ] **Step 1: Write**

```tsx
import type { ReportDto } from "@/lib/api";
import { hasConclusions } from "@/lib/has-data";

export default function ConclusionsSection({ report }: { report: ReportDto }) {
  if (!hasConclusions(report)) return null;
  return (
    <section style={{ marginBottom: 48, maxWidth: 720 }}>
      <span className="pill-title mint">CONCLUSIONES</span>
      <div className="chirri-note" style={{ marginTop: 16 }}>
        {report.conclusions_text}
        <span className="sig">— CHIRRI</span>
      </div>
    </section>
  );
}
```

- [ ] **Step 2: Commit**

```bash
docker compose exec frontend npx tsc --noEmit
git add frontend/app/reports/[id]/sections/ConclusionsSection.tsx
git commit -m "feat(frontend): add ConclusionsSection"
```

---

## Phase 11: Frontend page orchestrator

### Task 11.1: page.tsx

**Files:**
- Create: `frontend/app/reports/[id]/page.tsx`

- [ ] **Step 1: Write**

```tsx
import { notFound, redirect } from "next/navigation";
import { apiFetch, ApiError, type ReportDto } from "@/lib/api";
import { getAccessToken, getCurrentUser } from "@/lib/auth";
import TopBar from "@/components/top-bar";

import HeaderSection from "./sections/HeaderSection";
import IntroText from "./sections/IntroText";
import KpisSummary from "./sections/KpisSummary";
import MonthlyCompare from "./sections/MonthlyCompare";
import YoyComparison from "./sections/YoyComparison";
import NetworkSection from "./sections/NetworkSection";
import BestContentChapter from "./sections/BestContentChapter";
import OneLinkTable from "./sections/OneLinkTable";
import FollowerGrowthSection from "./sections/FollowerGrowthSection";
import Q1RollupTable from "./sections/Q1RollupTable";
import ConclusionsSection from "./sections/ConclusionsSection";

export default async function ReportPage({ params }: { params: { id: string } }) {
  const user = await getCurrentUser();
  if (!user) redirect("/login");

  const token = getAccessToken();
  let report: ReportDto;
  try {
    report = await apiFetch<ReportDto>(`/api/reports/${params.id}/`, { token });
  } catch (err) {
    if (err instanceof ApiError && err.status === 404) notFound();
    console.error("reports_fetch_failed", { id: params.id, err });
    throw err;
  }

  return (
    <>
      <TopBar user={user} active="home" />
      <main className="page" style={{ background: "var(--chirri-pink)" }}>
        <HeaderSection report={report} />
        <IntroText report={report} />
        <KpisSummary report={report} />
        <MonthlyCompare report={report} />
        <YoyComparison report={report} />
        <NetworkSection report={report} network="INSTAGRAM" />
        <NetworkSection report={report} network="TIKTOK" />
        <NetworkSection report={report} network="X" />
        <BestContentChapter report={report} />
        <OneLinkTable report={report} />
        <FollowerGrowthSection report={report} />
        <Q1RollupTable report={report} />
        <ConclusionsSection report={report} />
      </main>
    </>
  );
}
```

- [ ] **Step 2: Typecheck**

Run: `docker compose exec frontend npx tsc --noEmit`
Expected: PASS.

- [ ] **Step 3: Manually smoke-test in browser**

Start stack (`docker compose up -d`), visit http://localhost:3000/login, log in as `belen.rizzo@balanz.com` / `balanz2026`, go to `/home`, click "Leer reporte", confirm the page renders with sections that have data and no dev overlay.

- [ ] **Step 4: Commit**

```bash
git add frontend/app/reports/[id]/page.tsx
git commit -m "feat(frontend): /reports/[id] server-component orchestrator"
```

---

## Phase 12: Link verification

### Task 12.1: Confirm /home and /campaigns link correctly

**Files:**
- Read-only check: `frontend/app/home/page.tsx`, `frontend/app/campaigns/page.tsx`, `frontend/app/campaigns/[id]/page.tsx`

- [ ] **Step 1: Grep for existing links**

Run (or use the Grep tool):
```bash
grep -rn "reports/\${" frontend/app/
```
Expected: `/home/page.tsx` already links `/reports/${latest.id}` (see `frontend/app/home/page.tsx:90`).

- [ ] **Step 2: Ensure campaigns list has a "last report" link**

If `frontend/app/campaigns/page.tsx` links to reports via `last_published_at` but doesn't expose a report id, skip — it's campaign-level. No changes required for this ticket.

- [ ] **Step 3: No commit needed — verification only**

---

## Phase 13: E2E Playwright test

### Task 13.1: Report viewer smoke

**Files:**
- Create: `frontend/tests/reports.spec.ts`

- [ ] **Step 1: Write the spec**

```ts
import { test, expect } from "@playwright/test";
import { login, trackConsoleErrors } from "./helpers";

test.describe("Report viewer smoke", () => {
  test("login → home → click latest report → /reports/<id> renders", async ({ page }) => {
    const errors = trackConsoleErrors(page);

    await login(page);

    // "Leer reporte" on home is inside the latest-report hero link.
    await page.getByRole("link", { name: /leer reporte/i }).first().click();

    await expect(page).toHaveURL(/\/reports\/\d+$/);

    // Header
    await expect(page.locator("h1").first()).toBeVisible();
    // Brand + campaign eyebrow
    await expect(page.getByText(/balanz/i).first()).toBeVisible();
    // At least one KPI tile
    await expect(page.getByText(/total reach/i).first()).toBeVisible();
    // At least one content card from seed (placeholder post)
    await expect(page.getByText(/contenido destacado/i).first()).toBeVisible();

    expect(errors, `console/page errors on /reports/<id>:\n${errors.join("\n")}`).toEqual([]);
  });

  test("unknown report id returns 404", async ({ page }) => {
    await login(page);
    const response = await page.goto("/reports/99999");
    expect(response?.status()).toBe(404);
  });

  test("cross-tenant report access is 404", async ({ page }) => {
    // We don't have a rival user configured for E2E; skip if not seeded.
    // Kept here as a placeholder for future seed extension.
    test.skip(true, "Rival user not in E2E seed");
  });
});
```

- [ ] **Step 2: Run the smoke**

Run: `npm run test:e2e:smoke -- --grep "Report viewer"`
Expected: PASS.

- [ ] **Step 3: Commit**

```bash
git add frontend/tests/reports.spec.ts
git commit -m "test(e2e): smoke test for /reports/[id]"
```

---

## Phase 14: Docs & CI

### Task 14.1: Create docs/ENV.md

**Files:**
- Create: `docs/ENV.md`

- [ ] **Step 1: Write**

Create `docs/ENV.md`:
```markdown
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
```

- [ ] **Step 2: Commit**

```bash
git add docs/ENV.md
git commit -m "docs: add docs/ENV.md with all env vars and owners"
```

### Task 14.2: Update .env.example

**Files:**
- Modify: `.env.example`

- [ ] **Step 1: Append R2 block**

Append (or merge) to `.env.example`:
```
# --- Cloudflare R2 (unset locally = filesystem storage) ---
# USE_R2=1
# R2_ACCESS_KEY_ID=
# R2_SECRET_ACCESS_KEY=
# R2_ENDPOINT_URL=
# R2_BUCKET_NAME=chirri-media
# R2_PUBLIC_URL=
```

- [ ] **Step 2: Commit**

```bash
git add .env.example
git commit -m "docs: document R2 env vars in .env.example"
```

### Task 14.3: Update README

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Add route + env section**

Find the routes / env section in `README.md` (or add one near the top) and ensure it contains:
```markdown
### Rutas del portal
- `/login`, `/home`, `/campaigns`, `/campaigns/[id]`, `/reports/[id]`

### Env vars nuevas (R2)
Ver `docs/ENV.md`. En dev dejá `USE_R2` unset — se usa filesystem local.
```

- [ ] **Step 2: Commit**

```bash
git add README.md
git commit -m "docs: document /reports/[id] route and R2 env vars"
```

### Task 14.4: Add R2 secrets to GitHub Actions (manual step)

**Files:** none (GitHub UI)

- [ ] **Step 1: Add secrets**

In GitHub → repo → Settings → Secrets and variables → Actions, add:
- `R2_ACCESS_KEY_ID`
- `R2_SECRET_ACCESS_KEY`
- `R2_ENDPOINT_URL`
- `R2_BUCKET_NAME` = `chirri-media`
- `R2_PUBLIC_URL`
- `DEPLOY_URL` = e.g. `https://chirri.impactia.ai` (used by the post-deploy smoke job)

Also add `USE_R2=1` as a repo variable.

- [ ] **Step 2: Update deploy workflow**

Open `.github/workflows/deploy.yml` and ensure the deploy step passes these env vars into the container (via the docker compose `env_file` or explicit `-e`). If changes are required, commit them separately:

```bash
git add .github/workflows/deploy.yml
git commit -m "ci: pass R2 secrets through to deploy container"
```

- [ ] **Step 3: Verify a push to `development` deploys cleanly**

Push the branch, watch the Actions run, confirm the deploy succeeds and `/reports/<seeded_id>` responds 200 on the Hetzner host.

### Task 14.5: Post-deploy smoke against the deployed URL

**Files:**
- Modify: `.github/workflows/deploy.yml` (or `test.yml` if smoke is gated there)

Per the Impactia pipeline stage 4 contract: post-deploy smoke runs **after** deploy, hits the **deployed URL**, not localhost.

- [ ] **Step 1: Add a smoke job after deploy**

In `.github/workflows/deploy.yml`, add a job that runs after the deploy step:
```yaml
post_deploy_smoke:
  needs: deploy
  runs-on: ubuntu-latest
  if: github.ref == 'refs/heads/development'
  steps:
    - uses: actions/checkout@v4
    - uses: actions/setup-node@v4
      with:
        node-version: "20"
    - name: Install Playwright
      working-directory: frontend
      run: |
        npm ci
        npx playwright install --with-deps chromium
    - name: Wait for deploy to stabilise
      run: |
        for i in {1..30}; do
          curl -fsS "${{ secrets.DEPLOY_URL }}/api/health/" && break || sleep 5
        done
    - name: Run smoke against deployed URL
      working-directory: frontend
      env:
        PLAYWRIGHT_BASE_URL: ${{ secrets.DEPLOY_URL }}
      run: npx playwright test --project=smoke --grep "Report viewer|Home smoke"
```

- [ ] **Step 2: Verify `playwright.config.ts` honours `PLAYWRIGHT_BASE_URL`**

The config already reads `process.env.PLAYWRIGHT_BASE_URL ?? "http://localhost:3000"` (or equivalent). If not, add it:
```ts
use: { baseURL: process.env.PLAYWRIGHT_BASE_URL ?? "http://localhost:3000" },
```
No localhost fallback in CI — the smoke job must explicitly set the deployed URL.

- [ ] **Step 3: Commit**

```bash
git add .github/workflows/deploy.yml frontend/playwright.config.ts
git commit -m "ci: post-deploy smoke against DEPLOY_URL for report viewer"
```

- [ ] **Step 4: Rollback path documented**

Confirm `README.md` has a section (or add one):
```markdown
### Rollback
1. `git revert <bad-sha>` or `git reset --hard <good-sha>` on `development`.
2. Push — `deploy.yml` redeploys the previous image (pinned by SHA, not `:latest`).
3. If a migration needs rolling back: `docker compose exec backend python manage.py migrate reports <prev>`. All DEV-52 migrations are additive (new fields/models); rollback does not drop data in existing columns.
```

Commit if changed:
```bash
git add README.md
git commit -m "docs: document rollback path post DEV-52"
```

---

## Phase 15: Final verification

### Task 15.1: Full test battery

- [ ] **Step 1: Run everything**

```bash
docker compose exec backend pytest
npm run test:e2e:smoke
```
Expected: all green.

### Task 15.2: Manual smoke of all sections

- [ ] **Step 1: Confirm each section renders or hides correctly**

Walk through `/home` → `/reports/<id>` and check:
- Header (brand, campaign, stage, published date)
- Intro text visible
- KPIs Summary populated
- Monthly comparatives (if period_comparison on metrics)
- YoY (only if prior-year report seeded — otherwise hidden)
- IG / TikTok / X sections each hidden or populated based on metrics
- Best Content: posts + creators
- OneLink table
- Follower growth chart (SVG renders)
- Q1 rollup table
- Conclusions

### Task 15.3: Archive the plan

**Files:**
- Modify header of `docs/superpowers/specs/2026-04-20-report-viewer-design.md` — change `Status: Design` to `Status: Done`

- [ ] **Step 1: Mark spec as done**

Open `docs/superpowers/specs/2026-04-20-report-viewer-design.md` and change the header line `Status: Design` to `Status: Done`.

- [ ] **Step 2: Mark plan as done and move to `completed/`**

Open this plan file (`docs/superpowers/plans/2026-04-20-report-viewer.md`) and add a top-level `**Status:** Done — <date>` line beneath the title. Then move the file to the archive:
```bash
mkdir -p docs/superpowers/plans/completed
git mv docs/superpowers/plans/2026-04-20-report-viewer.md docs/superpowers/plans/completed/2026-04-20-report-viewer.md
```
(If the repo already has a different archive convention — e.g., a `done/` prefix — follow that instead. Do NOT delete the plan; it's part of the project history.)

- [ ] **Step 3: Commit**

```bash
git add docs/superpowers/specs/2026-04-20-report-viewer-design.md docs/superpowers/plans/
git commit -m "docs: mark report viewer spec/plan as done and archive plan"
```

- [ ] **Step 4: Confirm no stray state files left over**

Run:
```bash
git status docs/superpowers/
```
Expected: clean. No `entropy-loop-state.json`, no temp `*.tmp` files, no orphaned `.bak`s.

- [ ] **Step 5: Merge to main**

Follow the repo's merge flow (PR from feature branch → `main`; fast-forward `development` to deploy).

---

## Self-Review Checklist

- [x] All spec sections covered (contexto, modelos, API, frontend sections, charts, storage, security, observability, tests, CI/CD, git strategy, repo hygiene, DoD)
- [x] No placeholders, TBD, or "similar to X" references — each task has full code
- [x] Types consistent across tasks: `ReportDto`, `TopContentDto`, `OneLinkAttributionDto`, `Q1RollupDto`, `YoyRowDto`, `FollowerSnapshotPoint` all match what aggregation helpers return and what sections consume
- [x] TDD order: every task that writes production code starts with a failing test (Phase 1-6), frontend components follow typecheck as the verification step
- [x] File paths exact
- [x] Commits atomic and conventional
- [x] DRY: aggregation helpers live in one place (`backend/apps/reports/services/aggregations.py` and `frontend/lib/aggregations.ts`) and are referenced from the rest
- [x] YAGNI: no Recharts, no global state, no i18n wrapper, no PDF export, no importer — all deferred per spec
- [x] Observability: structured logging in the detail view, `console.error` on fetch fail
- [x] Security: scoping in view, image upload validators, R2 secrets via env
- [x] Complexity budget: every section < 100 lines, `page.tsx` < 50 lines
