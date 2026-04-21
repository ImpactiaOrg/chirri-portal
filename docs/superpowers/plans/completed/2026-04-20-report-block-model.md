# Report Block Model Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Refactorizar el modelo `Report` de 13 secciones hardcoded a una lista ordenada de `ReportBlock` tipados (6 tipos) con `config` JSON validado por registry, manteniendo paridad visual 1:1 con los 2 reportes seeded.

**Architecture:** Backend Django 5 agrega `ReportBlock` (type + order + JSONField config + image) + `Report.original_pdf`. Admin usa `django-admin-sortable2` para drag-drop. Serializer expone `blocks[]` con prefetch. Frontend introduce un `BlockRenderer` dispatcher que mapea `block.type` a 6 componentes (`TextImageBlock`, `KpiGridBlock`, `MetricsTableBlock`, `TopContentBlock`, `AttributionTableBlock`, `ChartBlock`). `seed_demo` pobla 11 bloques para los reportes demo. La data sigue viniendo del `Report` agregado — `config` solo describe filtros y display.

**Tech Stack:** Django 5 + DRF · `django-admin-sortable2==2.1.10` · PostgreSQL 15 · Next.js 14 App Router SSR · Playwright E2E · pytest.

**Spec:** `docs/superpowers/specs/2026-04-20-report-block-model-design.md`
**Ticket:** [DEV-105](https://linear.app/impactia/issue/DEV-105)
**Blocks:** DEV-83

---

## Pre-flight

Branch esperado: `dev-105-report-block-model` (se asume ya creada por el orquestador). Todas las pruebas deben correr dentro del stack Docker — `docker compose exec backend pytest …` y `npm run test:e2e:smoke` desde `frontend/`. Stack tiene que estar arriba (`docker compose up -d`).

### Principios aplicados (referencia `~/.ai-skills/method/PRINCIPLES.md`)

Este plan se ancla explícitamente en:

- **P1 — Tests Before Code**: todos los tasks que escriben código empiezan con un test failing.
- **P2 — Single Responsibility**: un BlockComponent por tipo, un validador por tipo, registry centraliza el mapping.
- **P3 — Don't Repeat Yourself**: reuse de `KpiTile`, `ContentCard`, `BarChartMini`; sin re-implementar helpers existentes.
- **P4 — Open/Closed**: agregar un nuevo tipo de bloque (fase 2) = agregar entry al registry + un componente, sin tocar `BlockRenderer` ni los bloques existentes.
- **P5 — Depend on Abstractions**: `ReportBlock.clean()` llama al registry vía import local, no a validators concretos; frontend `BlockRenderer` despacha por type, no por if/else hardcoded.
- **P7 — Security by Default**: validators en boundaries (PDF size/mime, image size/mime, block config schema); tenant scoping en la view; admin-only editing; no raw queries.
- **P9 — Fail Fast and Loud**: config inválido → `ValidationError` en admin; type desconocido → `console.warn` + skip render.
- **P10 — Simplicity Over Cleverness**: JSONField + registry en lugar de serializers polimórficos / pydantic; runtime defensive checks en el frontend en lugar de generics por variant.

---

### Task 1: Validadores PDF para `Report.original_pdf`

**Files:**
- Modify: `backend/apps/reports/validators.py`
- Create: `backend/tests/unit/test_pdf_validators.py`

- [ ] **Step 1: Escribir el test failing**

Crear `backend/tests/unit/test_pdf_validators.py`:

```python
import io
import pytest
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile

from apps.reports.validators import (
    MAX_PDF_SIZE_BYTES,
    validate_pdf_size,
    validate_pdf_mimetype,
)


def _pdf_file(size_bytes: int, content_type: str = "application/pdf"):
    return SimpleUploadedFile(
        name="report.pdf",
        content=b"0" * size_bytes,
        content_type=content_type,
    )


def test_validate_pdf_size_accepts_under_limit():
    validate_pdf_size(_pdf_file(1024))  # no raise


def test_validate_pdf_size_rejects_over_limit():
    with pytest.raises(ValidationError):
        validate_pdf_size(_pdf_file(MAX_PDF_SIZE_BYTES + 1))


def test_validate_pdf_mimetype_accepts_pdf():
    validate_pdf_mimetype(_pdf_file(10, "application/pdf"))


@pytest.mark.parametrize("bad_type", ["image/jpeg", "application/octet-stream", "text/plain"])
def test_validate_pdf_mimetype_rejects_non_pdf(bad_type):
    with pytest.raises(ValidationError):
        validate_pdf_mimetype(_pdf_file(10, bad_type))
```

- [ ] **Step 2: Run test to verify it fails**

Run: `docker compose exec backend pytest tests/unit/test_pdf_validators.py -v`
Expected: FAIL with `ImportError: cannot import name 'MAX_PDF_SIZE_BYTES'`.

- [ ] **Step 3: Implement validators**

Append to `backend/apps/reports/validators.py`:

```python
MAX_PDF_SIZE_BYTES = 20 * 1024 * 1024
ALLOWED_PDF_MIMETYPES = {"application/pdf"}


def validate_pdf_size(file) -> None:
    if file.size > MAX_PDF_SIZE_BYTES:
        raise ValidationError(
            f"El PDF excede el tamaño máximo de {MAX_PDF_SIZE_BYTES // (1024 * 1024)} MB."
        )


def validate_pdf_mimetype(file) -> None:
    mimetype = getattr(file, "content_type", None)
    if mimetype not in ALLOWED_PDF_MIMETYPES:
        raise ValidationError(
            f"Formato no permitido ({mimetype}). Solo se aceptan PDFs."
        )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `docker compose exec backend pytest tests/unit/test_pdf_validators.py -v`
Expected: 4 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/apps/reports/validators.py backend/tests/unit/test_pdf_validators.py
git commit -m "feat(reports): add pdf size and mimetype validators"
```

---

### Task 2: Registry + validadores de config por tipo de bloque

**Files:**
- Create: `backend/apps/reports/blocks/__init__.py`
- Create: `backend/apps/reports/blocks/schemas.py`
- Create: `backend/apps/reports/blocks/registry.py`
- Create: `backend/tests/unit/test_block_config_validation.py`

- [ ] **Step 1: Escribir el test failing**

Crear `backend/tests/unit/test_block_config_validation.py`:

```python
import pytest
from django.core.exceptions import ValidationError

from apps.reports.blocks.registry import validate_config


# TEXT_IMAGE
def test_text_image_valid():
    validate_config("TEXT_IMAGE", {"title": "t", "text": "x", "columns": 2, "image_position": "left"})


@pytest.mark.parametrize("cols", [0, 4, -1, "two"])
def test_text_image_rejects_bad_columns(cols):
    with pytest.raises(ValidationError):
        validate_config("TEXT_IMAGE", {"columns": cols, "image_position": "left"})


def test_text_image_rejects_bad_image_position():
    with pytest.raises(ValidationError):
        validate_config("TEXT_IMAGE", {"columns": 1, "image_position": "bottom"})


# KPI_GRID
def test_kpi_grid_valid():
    validate_config("KPI_GRID", {"tiles": [{"label": "Reach", "source": "reach_total"}]})


def test_kpi_grid_rejects_empty_tiles():
    with pytest.raises(ValidationError):
        validate_config("KPI_GRID", {"tiles": []})


def test_kpi_grid_rejects_tile_without_source():
    with pytest.raises(ValidationError):
        validate_config("KPI_GRID", {"tiles": [{"label": "Reach"}]})


def test_kpi_grid_rejects_unknown_source():
    with pytest.raises(ValidationError):
        validate_config("KPI_GRID", {"tiles": [{"label": "X", "source": "foo"}]})


# METRICS_TABLE
def test_metrics_table_valid_metrics_source():
    validate_config("METRICS_TABLE", {
        "source": "metrics",
        "filter": {"network": "INSTAGRAM", "source_type": None, "has_comparison": None},
    })


def test_metrics_table_valid_yoy_source():
    validate_config("METRICS_TABLE", {"source": "yoy", "filter": {}})


def test_metrics_table_rejects_unknown_source():
    with pytest.raises(ValidationError):
        validate_config("METRICS_TABLE", {"source": "foo", "filter": {}})


def test_metrics_table_rejects_unknown_network_filter():
    with pytest.raises(ValidationError):
        validate_config("METRICS_TABLE", {"source": "metrics", "filter": {"network": "FACEBOOK"}})


# TOP_CONTENT
def test_top_content_valid_post():
    validate_config("TOP_CONTENT", {"kind": "POST", "limit": 6})


def test_top_content_valid_creator():
    validate_config("TOP_CONTENT", {"kind": "CREATOR"})


def test_top_content_rejects_bad_kind():
    with pytest.raises(ValidationError):
        validate_config("TOP_CONTENT", {"kind": "VIDEO"})


@pytest.mark.parametrize("lim", [0, -1, 21])
def test_top_content_rejects_bad_limit(lim):
    with pytest.raises(ValidationError):
        validate_config("TOP_CONTENT", {"kind": "POST", "limit": lim})


# ATTRIBUTION_TABLE
def test_attribution_table_valid():
    validate_config("ATTRIBUTION_TABLE", {"show_total": True})


def test_attribution_table_valid_defaults():
    validate_config("ATTRIBUTION_TABLE", {})


# CHART
def test_chart_valid_follower_snapshots():
    validate_config("CHART", {
        "source": "follower_snapshots", "group_by": "network", "chart_type": "bar",
    })


def test_chart_rejects_unsupported_source():
    with pytest.raises(ValidationError):
        validate_config("CHART", {"source": "engagement", "group_by": "network", "chart_type": "bar"})


def test_unknown_block_type_raises():
    with pytest.raises(ValidationError):
        validate_config("UNKNOWN", {})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `docker compose exec backend pytest tests/unit/test_block_config_validation.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'apps.reports.blocks'`.

- [ ] **Step 3: Crear el package y los schemas**

Crear `backend/apps/reports/blocks/__init__.py` vacío.

Crear `backend/apps/reports/blocks/schemas.py`:

```python
from django.core.exceptions import ValidationError

ALLOWED_NETWORKS = {"INSTAGRAM", "TIKTOK", "X"}
ALLOWED_SOURCE_TYPES = {"ORGANIC", "INFLUENCER", "PAID"}
ALLOWED_KPI_SOURCES = {
    "reach_total", "reach_organic", "reach_influencer",
    "reach_paid", "engagement_total",
}
ALLOWED_METRICS_SOURCES = {"metrics", "yoy", "q1_rollup"}
ALLOWED_IMAGE_POSITIONS = {"left", "right", "top"}
ALLOWED_TOP_CONTENT_KINDS = {"POST", "CREATOR"}
CHART_SUPPORTED_COMBINATIONS = {
    ("follower_snapshots", "network", "bar"),
}


def _require(config, key, typ):
    if key not in config:
        raise ValidationError({"config": [f"Falta key requerida: {key}"]})
    if not isinstance(config[key], typ):
        raise ValidationError({"config": [f"Key '{key}' debe ser {typ.__name__}"]})


def validate_text_image_config(config: dict) -> None:
    cols = config.get("columns")
    if cols not in (1, 2, 3):
        raise ValidationError({"config": ["columns debe ser 1, 2 o 3"]})
    pos = config.get("image_position")
    if pos not in ALLOWED_IMAGE_POSITIONS:
        raise ValidationError({"config": [
            f"image_position debe ser una de {sorted(ALLOWED_IMAGE_POSITIONS)}"
        ]})


def validate_kpi_grid_config(config: dict) -> None:
    tiles = config.get("tiles")
    if not isinstance(tiles, list) or len(tiles) == 0:
        raise ValidationError({"config": ["tiles debe ser lista no vacía"]})
    for tile in tiles:
        if not isinstance(tile, dict):
            raise ValidationError({"config": ["cada tile debe ser objeto"]})
        if "source" not in tile:
            raise ValidationError({"config": ["tile sin source"]})
        if tile["source"] not in ALLOWED_KPI_SOURCES:
            raise ValidationError({"config": [
                f"source desconocido: {tile['source']}"
            ]})


def validate_metrics_table_config(config: dict) -> None:
    source = config.get("source")
    if source not in ALLOWED_METRICS_SOURCES:
        raise ValidationError({"config": [
            f"source debe ser una de {sorted(ALLOWED_METRICS_SOURCES)}"
        ]})
    flt = config.get("filter", {})
    if not isinstance(flt, dict):
        raise ValidationError({"config": ["filter debe ser objeto"]})
    network = flt.get("network")
    if network is not None and network not in ALLOWED_NETWORKS:
        raise ValidationError({"config": [f"network desconocido: {network}"]})
    stype = flt.get("source_type")
    if stype is not None and stype not in ALLOWED_SOURCE_TYPES:
        raise ValidationError({"config": [f"source_type desconocido: {stype}"]})


def validate_top_content_config(config: dict) -> None:
    kind = config.get("kind")
    if kind not in ALLOWED_TOP_CONTENT_KINDS:
        raise ValidationError({"config": [
            f"kind debe ser POST o CREATOR"
        ]})
    lim = config.get("limit", 6)
    if not isinstance(lim, int) or lim < 1 or lim > 20:
        raise ValidationError({"config": ["limit debe ser int entre 1 y 20"]})


def validate_attribution_table_config(config: dict) -> None:
    show_total = config.get("show_total", True)
    if not isinstance(show_total, bool):
        raise ValidationError({"config": ["show_total debe ser boolean"]})


def validate_chart_config(config: dict) -> None:
    source = config.get("source")
    group_by = config.get("group_by")
    chart_type = config.get("chart_type")
    if (source, group_by, chart_type) not in CHART_SUPPORTED_COMBINATIONS:
        raise ValidationError({"config": [
            "combinación CHART no soportada en fase 1 — solo follower_snapshots + network + bar"
        ]})
```

Crear `backend/apps/reports/blocks/registry.py`:

```python
from django.core.exceptions import ValidationError

from .schemas import (
    validate_text_image_config,
    validate_kpi_grid_config,
    validate_metrics_table_config,
    validate_top_content_config,
    validate_attribution_table_config,
    validate_chart_config,
)

BLOCK_VALIDATORS = {
    "TEXT_IMAGE": validate_text_image_config,
    "KPI_GRID": validate_kpi_grid_config,
    "METRICS_TABLE": validate_metrics_table_config,
    "TOP_CONTENT": validate_top_content_config,
    "ATTRIBUTION_TABLE": validate_attribution_table_config,
    "CHART": validate_chart_config,
}


def validate_config(block_type: str, config: dict) -> None:
    validator = BLOCK_VALIDATORS.get(block_type)
    if validator is None:
        raise ValidationError({"type": [f"Tipo de bloque desconocido: {block_type}"]})
    validator(config)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `docker compose exec backend pytest tests/unit/test_block_config_validation.py -v`
Expected: All tests PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/apps/reports/blocks backend/tests/unit/test_block_config_validation.py
git commit -m "feat(reports): add block config registry and per-type validators"
```

---

### Task 3: Modelo `ReportBlock` + campo `Report.original_pdf`

**Files:**
- Modify: `backend/apps/reports/models.py`
- Create: `backend/tests/unit/test_report_block_model.py`

- [ ] **Step 1: Escribir el test failing**

Crear `backend/tests/unit/test_report_block_model.py`:

```python
import pytest
from django.core.exceptions import ValidationError
from django.db.utils import IntegrityError

from apps.reports.models import Report, ReportBlock

pytestmark = pytest.mark.django_db


def test_create_report_block(balanz_published_report):
    block = ReportBlock.objects.create(
        report=balanz_published_report,
        type=ReportBlock.Type.KPI_GRID,
        order=1,
        config={"tiles": [{"label": "Reach", "source": "reach_total"}]},
    )
    assert block.pk is not None
    assert block.report_id == balanz_published_report.pk


def test_unique_order_per_report(balanz_published_report):
    ReportBlock.objects.create(
        report=balanz_published_report, type="KPI_GRID", order=1,
        config={"tiles": [{"label": "R", "source": "reach_total"}]},
    )
    with pytest.raises(IntegrityError):
        ReportBlock.objects.create(
            report=balanz_published_report, type="KPI_GRID", order=1,
            config={"tiles": [{"label": "R", "source": "reach_total"}]},
        )


def test_clean_rejects_invalid_config(balanz_published_report):
    block = ReportBlock(
        report=balanz_published_report,
        type=ReportBlock.Type.KPI_GRID,
        order=1,
        config={"tiles": []},
    )
    with pytest.raises(ValidationError):
        block.clean()


def test_clean_accepts_valid_config(balanz_published_report):
    block = ReportBlock(
        report=balanz_published_report,
        type=ReportBlock.Type.TEXT_IMAGE,
        order=1,
        config={"columns": 2, "image_position": "left"},
    )
    block.clean()  # no raise


def test_ordering_by_report_then_order(balanz_published_report):
    for i in (3, 1, 2):
        ReportBlock.objects.create(
            report=balanz_published_report, type="KPI_GRID", order=i,
            config={"tiles": [{"label": "R", "source": "reach_total"}]},
        )
    orders = list(
        ReportBlock.objects.filter(report=balanz_published_report).values_list("order", flat=True)
    )
    assert orders == [1, 2, 3]


def test_report_has_original_pdf_field():
    field = Report._meta.get_field("original_pdf")
    assert field.blank is True
    assert field.null is True
```

- [ ] **Step 2: Run test to verify it fails**

Run: `docker compose exec backend pytest tests/unit/test_report_block_model.py -v`
Expected: FAIL with `ImportError: cannot import name 'ReportBlock'`.

- [ ] **Step 3: Implement model changes**

Edit `backend/apps/reports/models.py`:

- Actualizar import de validators en el top:

```python
from .validators import (
    validate_image_mimetype, validate_image_size,
    validate_pdf_mimetype, validate_pdf_size,
)
```

- Agregar `original_pdf` al modelo `Report` (después de `conclusions_text` / `intro_text`, antes de `created_at`):

```python
    original_pdf = models.FileField(
        upload_to="reports/pdf/%Y/%m/",
        blank=True,
        null=True,
        validators=[validate_pdf_size, validate_pdf_mimetype],
        help_text="PDF original del reporte (Google Slides export), descargable por el cliente.",
    )
```

- Agregar la clase `ReportBlock` al final del archivo:

```python
class ReportBlock(models.Model):
    class Type(models.TextChoices):
        TEXT_IMAGE = "TEXT_IMAGE", "Texto + imagen"
        KPI_GRID = "KPI_GRID", "Grilla de KPIs"
        METRICS_TABLE = "METRICS_TABLE", "Tabla de métricas"
        TOP_CONTENT = "TOP_CONTENT", "Best content"
        ATTRIBUTION_TABLE = "ATTRIBUTION_TABLE", "Tabla de atribución"
        CHART = "CHART", "Gráfico"

    report = models.ForeignKey(Report, on_delete=models.CASCADE, related_name="blocks")
    type = models.CharField(max_length=32, choices=Type.choices)
    order = models.PositiveIntegerField(db_index=True)
    config = models.JSONField(default=dict, blank=True)
    image = models.ImageField(
        upload_to="report_blocks/%Y/%m/",
        blank=True,
        null=True,
        validators=[validate_image_size, validate_image_mimetype],
        help_text="Solo usado por TEXT_IMAGE. En otros tipos se ignora.",
    )

    class Meta:
        ordering = ["report", "order"]
        indexes = [models.Index(fields=["report", "order"])]
        constraints = [
            models.UniqueConstraint(
                fields=["report", "order"], name="uniq_block_order_per_report",
            ),
        ]

    def clean(self):
        from .blocks.registry import validate_config
        validate_config(self.type, self.config)

    def __str__(self):
        return f"{self.report_id} · {self.type} #{self.order}"
```

- [ ] **Step 4: Generar migración**

Run: `docker compose exec backend python manage.py makemigrations reports --name report_blocks_and_pdf`
Expected: Genera `backend/apps/reports/migrations/00XX_report_blocks_and_pdf.py` con:
- `AddField Report.original_pdf`
- `CreateModel ReportBlock`

Verificar la migración abriendo el archivo (leer con Read, confirmar que contiene los dos cambios).

- [ ] **Step 5: Aplicar migración**

Run: `docker compose exec backend python manage.py migrate reports`
Expected: Migración aplica OK.

- [ ] **Step 6: Run test to verify it passes**

Run: `docker compose exec backend pytest tests/unit/test_report_block_model.py -v`
Expected: 6 tests PASS.

- [ ] **Step 7: Commit**

```bash
git add backend/apps/reports/models.py backend/apps/reports/migrations/ backend/tests/unit/test_report_block_model.py
git commit -m "feat(reports): add ReportBlock model and Report.original_pdf field"
```

---

### Task 4: Instalar `django-admin-sortable2` y configurar admin

**Files:**
- Modify: `backend/requirements.txt`
- Modify: `backend/config/settings/base.py`
- Modify: `backend/apps/reports/admin.py`

- [ ] **Step 1: Agregar dependencia**

Edit `backend/requirements.txt`, agregar (mantener orden alfabético en la zona de third-party apps):

```
django-admin-sortable2==2.1.10
```

- [ ] **Step 2: Rebuild backend container con la nueva dep**

Run: `docker compose build backend && docker compose up -d backend`
Expected: Container rebuild OK, starts con sortable2 disponible.

- [ ] **Step 2.1: Dependency health check (P7)**

Run: `docker compose exec backend pip check`
Expected: "No broken requirements found." — confirma que `django-admin-sortable2==2.1.10` no introduce conflictos transitivos con Django 5 / DRF.

Run: `docker compose exec backend python -c "import adminsortable2; print(adminsortable2.__version__)"`
Expected: imprime `2.1.10` (pin exacto — sin versión flotante).

**Notas de security review:**
- Versión pin explícita (no `>=` ni `~=`) → evita supply-chain drift.
- `django-admin-sortable2` es compatible con Django 5 y mantenido activamente a 2026 (último commit reciente en GitHub).
- No introduce secrets nuevos ni expone endpoints públicos — solo mixin de admin.
- Si `pip check` reporta conflictos, **parar** y reportar al orquestador antes de continuar.

- [ ] **Step 3: Registrar app en settings**

Edit `backend/config/settings/base.py`. En `INSTALLED_APPS`, agregar `"adminsortable2"` **antes** de `"django.contrib.admin"`:

```python
INSTALLED_APPS = [
    "adminsortable2",
    "django.contrib.admin",
    # ... resto igual
]
```

- [ ] **Step 4: Actualizar admin.py**

Reemplazar `backend/apps/reports/admin.py` por:

```python
from adminsortable2.admin import SortableInlineAdminMixin
from django.contrib import admin

from .models import (
    Report, ReportMetric, ReportBlock,
    TopContent, BrandFollowerSnapshot, OneLinkAttribution,
)


class ReportMetricInline(admin.TabularInline):
    model = ReportMetric
    extra = 0


class TopContentInline(admin.StackedInline):
    model = TopContent
    extra = 0
    fields = ("kind", "network", "source_type", "rank", "handle", "caption", "thumbnail", "post_url", "metrics")


class OneLinkAttributionInline(admin.TabularInline):
    model = OneLinkAttribution
    extra = 0


class ReportBlockInline(SortableInlineAdminMixin, admin.StackedInline):
    model = ReportBlock
    extra = 0
    fields = ("type", "config", "image")
    # order es gestionado por SortableInlineAdminMixin automáticamente


@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    list_display = ("display_title", "stage", "kind", "period_start", "period_end", "status", "published_at")
    list_filter = ("status", "kind", "stage__campaign__brand")
    search_fields = ("title", "stage__name", "stage__campaign__name")
    inlines = [
        ReportMetricInline,
        TopContentInline,
        OneLinkAttributionInline,
        ReportBlockInline,
    ]
    fieldsets = (
        (None, {
            "fields": (
                "stage", "kind", "period_start", "period_end",
                "title", "status", "published_at",
                "intro_text", "conclusions_text",
                "original_pdf",
            ),
        }),
    )
    actions = ["publish_reports"]

    @admin.action(description="Publicar reportes seleccionados")
    def publish_reports(self, request, queryset):
        from django.utils import timezone
        updated = queryset.filter(status=Report.Status.DRAFT).update(
            status=Report.Status.PUBLISHED, published_at=timezone.now()
        )
        self.message_user(request, f"{updated} reporte(s) publicado(s).")


@admin.register(ReportMetric)
class ReportMetricAdmin(admin.ModelAdmin):
    list_display = ("report", "network", "source_type", "metric_name", "value", "period_comparison")
    list_filter = ("network", "source_type")
    search_fields = ("report__title", "metric_name")


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

- [ ] **Step 5: Verificar que el admin arranca sin errores**

Run: `docker compose exec backend python manage.py check`
Expected: `System check identified no issues`.

Manualmente (solo verificación visual):
1. Abrir `http://localhost:8000/admin/` en el browser.
2. Login con superuser (ver README).
3. Entrar a un Report existente.
4. Confirmar que aparecen los inlines: Metrics, Top Content, OneLink, Blocks — este último con drag-handle.

- [ ] **Step 6: Commit**

```bash
git add backend/requirements.txt backend/config/settings/base.py backend/apps/reports/admin.py
git commit -m "feat(reports): wire sortable ReportBlockInline and inlines for top content and attribution"
```

---

### Task 5: Serializer expone `blocks[]` + `original_pdf_url` sin N+1

**Files:**
- Modify: `backend/apps/reports/serializers.py`
- Modify: `backend/apps/reports/views.py`
- Create: `backend/tests/unit/test_report_serializer_blocks.py`
- Modify: `backend/tests/unit/test_report_nplus1.py`

- [ ] **Step 1: Escribir el test failing**

Crear `backend/tests/unit/test_report_serializer_blocks.py`:

```python
import pytest
from django.core.files.uploadedfile import SimpleUploadedFile

from apps.reports.models import ReportBlock
from apps.reports.serializers import ReportDetailSerializer

pytestmark = pytest.mark.django_db


def _kpi_block(report, order):
    return ReportBlock.objects.create(
        report=report, order=order, type="KPI_GRID",
        config={"tiles": [{"label": "Reach", "source": "reach_total"}]},
    )


def test_empty_blocks_serializes_as_empty_list(balanz_published_report):
    data = ReportDetailSerializer(balanz_published_report).data
    assert data["blocks"] == []


def test_blocks_serialize_in_order(balanz_published_report):
    _kpi_block(balanz_published_report, 3)
    _kpi_block(balanz_published_report, 1)
    _kpi_block(balanz_published_report, 2)

    data = ReportDetailSerializer(balanz_published_report).data
    orders = [b["order"] for b in data["blocks"]]
    assert orders == [1, 2, 3]
    for block in data["blocks"]:
        assert block["type"] == "KPI_GRID"
        assert "config" in block
        assert block["image_url"] is None


def test_original_pdf_url_null_when_empty(balanz_published_report):
    data = ReportDetailSerializer(balanz_published_report).data
    assert data["original_pdf_url"] is None


def test_original_pdf_url_populated(balanz_published_report):
    balanz_published_report.original_pdf = SimpleUploadedFile(
        "report.pdf", b"%PDF-1.4 payload", content_type="application/pdf",
    )
    balanz_published_report.save()
    data = ReportDetailSerializer(balanz_published_report).data
    assert data["original_pdf_url"] is not None
    assert data["original_pdf_url"].endswith(".pdf")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `docker compose exec backend pytest tests/unit/test_report_serializer_blocks.py -v`
Expected: FAIL with `KeyError: 'blocks'`.

- [ ] **Step 3: Actualizar serializer**

Edit `backend/apps/reports/serializers.py`:

- Agregar import de `ReportBlock`:

```python
from .models import (
    Report, ReportMetric, ReportBlock,
    TopContent, OneLinkAttribution,
)
```

- Agregar la clase `ReportBlockSerializer` (antes de `ReportDetailSerializer`):

```python
class ReportBlockSerializer(serializers.ModelSerializer):
    image_url = serializers.SerializerMethodField()

    class Meta:
        model = ReportBlock
        fields = ("id", "type", "order", "config", "image_url")

    def get_image_url(self, obj) -> str | None:
        return obj.image.url if obj.image else None
```

- Extender `ReportDetailSerializer`:

```python
class ReportDetailSerializer(serializers.ModelSerializer):
    # ... campos existentes
    blocks = ReportBlockSerializer(many=True, read_only=True)
    original_pdf_url = serializers.SerializerMethodField()

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
            "blocks", "original_pdf_url",
        )

    # ... métodos existentes
    def get_original_pdf_url(self, obj) -> str | None:
        return obj.original_pdf.url if obj.original_pdf else None
```

- [ ] **Step 4: Actualizar view prefetch**

Edit `backend/apps/reports/views.py`, en `ReportDetailView.get_queryset()`:

```python
    .prefetch_related("metrics", "top_content", "onelink", "blocks")
```

- [ ] **Step 5: Run serializer test to verify it passes**

Run: `docker compose exec backend pytest tests/unit/test_report_serializer_blocks.py -v`
Expected: 4 tests PASS.

- [ ] **Step 6: Actualizar N+1 test**

Edit `backend/tests/unit/test_report_nplus1.py`. Reemplazar el cuerpo del test por:

```python
import pytest
from django.test.utils import CaptureQueriesContext
from django.db import connection

from apps.reports.models import Report, ReportMetric, ReportBlock, TopContent, OneLinkAttribution

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
    for i in range(20):
        ReportBlock.objects.create(
            report=balanz_published_report, order=i + 1,
            type=ReportBlock.Type.KPI_GRID,
            config={"tiles": [{"label": "R", "source": "reach_total"}]},
        )

    with CaptureQueriesContext(connection) as ctx:
        res = authed_balanz.get(f"/api/reports/{balanz_published_report.pk}/")
    assert res.status_code == 200
    # Query budget: auth + main report + select_related (stage/campaign/brand) +
    # prefetch x4 (metrics, top_content, onelink, blocks) + aggregations (q1 + yoy + snapshots).
    # Tight enough to fail if a row-scoped query slips in (N+1 on 20 blocks would push us well past 13).
    n = len(ctx.captured_queries)
    assert n <= 13, f"too many queries: {n}"
```

- [ ] **Step 7: Run N+1 test**

Run: `docker compose exec backend pytest tests/unit/test_report_nplus1.py -v`
Expected: PASS (query count ≤ 13).

- [ ] **Step 8: Commit**

```bash
git add backend/apps/reports/serializers.py backend/apps/reports/views.py backend/tests/unit/test_report_serializer_blocks.py backend/tests/unit/test_report_nplus1.py
git commit -m "feat(reports): serialize blocks and original_pdf_url with prefetch"
```

---

### Task 6: `seed_demo` genera 11 bloques por reporte completo

**Files:**
- Modify: `backend/apps/tenants/management/commands/seed_demo.py`
- Create: `backend/tests/unit/test_seed_demo_blocks.py`

- [ ] **Step 1: Escribir el test failing**

Crear `backend/tests/unit/test_seed_demo_blocks.py`:

```python
import pytest
from django.core.management import call_command

from apps.reports.models import Report, ReportBlock

pytestmark = pytest.mark.django_db


def test_seed_demo_creates_blocks_for_full_reports():
    call_command("seed_demo", "--wipe")

    full_reports = Report.objects.filter(
        title__startswith="Reporte general",
        stage__kind__in=["EDUCATION", "VALIDATION"],
    )
    assert full_reports.count() == 2
    for report in full_reports:
        blocks = list(report.blocks.order_by("order"))
        assert len(blocks) == 11, f"{report.title} has {len(blocks)} blocks"
        # Primer bloque siempre es KPI_GRID
        assert blocks[0].type == ReportBlock.Type.KPI_GRID
        # El último es METRICS_TABLE con Q1 rollup
        assert blocks[-1].type == ReportBlock.Type.METRICS_TABLE
        assert blocks[-1].config["source"] == "q1_rollup"
        # Orden es 1..11 consecutivo
        assert [b.order for b in blocks] == list(range(1, 12))
```

- [ ] **Step 2: Run test to verify it fails**

Run: `docker compose exec backend pytest tests/unit/test_seed_demo_blocks.py -v`
Expected: FAIL — `len(blocks) == 0` porque seed_demo todavía no crea bloques.

- [ ] **Step 3: Extender seed_demo**

Edit `backend/apps/tenants/management/commands/seed_demo.py`:

- Agregar import al top de los imports de reports (junto a los existentes):

```python
from apps.reports.models import ReportBlock
```

- Agregar la helper function al final del archivo (fuera de la clase `Command`):

```python
def _seed_blocks_for_full_report(report):
    ReportBlock.objects.bulk_create([
        ReportBlock(report=report, order=1, type=ReportBlock.Type.KPI_GRID, config={
            "tiles": [
                {"label": "Reach total", "source": "reach_total"},
                {"label": "Reach orgánico", "source": "reach_organic"},
                {"label": "Reach influencer", "source": "reach_influencer"},
            ],
        }),
        ReportBlock(report=report, order=2, type=ReportBlock.Type.METRICS_TABLE, config={
            "title": "Mes a mes", "source": "metrics",
            "filter": {"has_comparison": True},
        }),
        ReportBlock(report=report, order=3, type=ReportBlock.Type.METRICS_TABLE, config={
            "title": "Year over year", "source": "yoy", "filter": {},
        }),
        ReportBlock(report=report, order=4, type=ReportBlock.Type.METRICS_TABLE, config={
            "title": "Instagram", "source": "metrics",
            "filter": {"network": "INSTAGRAM"},
        }),
        ReportBlock(report=report, order=5, type=ReportBlock.Type.METRICS_TABLE, config={
            "title": "TikTok", "source": "metrics",
            "filter": {"network": "TIKTOK"},
        }),
        ReportBlock(report=report, order=6, type=ReportBlock.Type.METRICS_TABLE, config={
            "title": "X / Twitter", "source": "metrics",
            "filter": {"network": "X"},
        }),
        ReportBlock(report=report, order=7, type=ReportBlock.Type.TOP_CONTENT, config={
            "title": "Posts del mes", "kind": "POST", "limit": 6,
        }),
        ReportBlock(report=report, order=8, type=ReportBlock.Type.TOP_CONTENT, config={
            "title": "Creators del mes", "kind": "CREATOR", "limit": 6,
        }),
        ReportBlock(report=report, order=9, type=ReportBlock.Type.ATTRIBUTION_TABLE, config={
            "show_total": True,
        }),
        ReportBlock(report=report, order=10, type=ReportBlock.Type.CHART, config={
            "title": "Followers", "source": "follower_snapshots",
            "group_by": "network", "chart_type": "bar",
        }),
        ReportBlock(report=report, order=11, type=ReportBlock.Type.METRICS_TABLE, config={
            "title": "Q1 rollup", "source": "q1_rollup", "filter": {},
        }),
    ])
```

- En `_seed_report_viewer_fixtures` (o donde se iteran los reportes "completos"), después de crear un reporte completo llamar:

```python
_seed_blocks_for_full_report(report)
```

Encontrar el loop correcto leyendo `backend/apps/tenants/management/commands/seed_demo.py` con `Grep -n "Reporte general"` — insertar la llamada dentro del branch donde se crea un reporte de tipo GENERAL en stages EDUCATION/VALIDATION.

- [ ] **Step 4: Run test to verify it passes**

Run: `docker compose exec backend pytest tests/unit/test_seed_demo_blocks.py -v`
Expected: PASS.

- [ ] **Step 5: Regenerar data demo local**

Run: `docker compose exec backend python manage.py seed_demo --wipe`
Expected: Output muestra creación de 2 reportes con 11 bloques cada uno.

- [ ] **Step 6: Commit**

```bash
git add backend/apps/tenants/management/commands/seed_demo.py backend/tests/unit/test_seed_demo_blocks.py
git commit -m "feat(seed_demo): create 11 default blocks for full reports"
```

---

### Task 7: Tipos TypeScript en `lib/api.ts`

**Files:**
- Modify: `frontend/lib/api.ts`

- [ ] **Step 1: Agregar tipos**

Edit `frontend/lib/api.ts`. Agregar antes de `export type ReportDto`:

```typescript
export type ReportBlockType =
  | "TEXT_IMAGE"
  | "KPI_GRID"
  | "METRICS_TABLE"
  | "TOP_CONTENT"
  | "ATTRIBUTION_TABLE"
  | "CHART";

export type ReportBlockDto = {
  id: number;
  type: ReportBlockType;
  order: number;
  config: Record<string, unknown>;
  image_url: string | null;
};
```

Extender `ReportDto` agregando dos campos al final:

```typescript
  blocks: ReportBlockDto[];
  original_pdf_url: string | null;
```

- [ ] **Step 2: Type-check**

Run: `docker compose exec frontend npx tsc --noEmit`
Expected: sin errores.

- [ ] **Step 3: Commit**

```bash
git add frontend/lib/api.ts
git commit -m "feat(frontend): add ReportBlockDto and original_pdf_url to ReportDto"
```

---

### Task 8: `BlockRenderer` dispatcher + 6 block components

**Files:**
- Create: `frontend/app/reports/[id]/blocks/BlockRenderer.tsx`
- Create: `frontend/app/reports/[id]/blocks/TextImageBlock.tsx`
- Create: `frontend/app/reports/[id]/blocks/KpiGridBlock.tsx`
- Create: `frontend/app/reports/[id]/blocks/MetricsTableBlock.tsx`
- Create: `frontend/app/reports/[id]/blocks/TopContentBlock.tsx`
- Create: `frontend/app/reports/[id]/blocks/AttributionTableBlock.tsx`
- Create: `frontend/app/reports/[id]/blocks/ChartBlock.tsx`

- [ ] **Step 1: BlockRenderer (dispatcher)**

Crear `frontend/app/reports/[id]/blocks/BlockRenderer.tsx`:

```tsx
import type { ReportBlockDto, ReportDto } from "@/lib/api";
import TextImageBlock from "./TextImageBlock";
import KpiGridBlock from "./KpiGridBlock";
import MetricsTableBlock from "./MetricsTableBlock";
import TopContentBlock from "./TopContentBlock";
import AttributionTableBlock from "./AttributionTableBlock";
import ChartBlock from "./ChartBlock";

const BLOCK_COMPONENTS = {
  TEXT_IMAGE: TextImageBlock,
  KPI_GRID: KpiGridBlock,
  METRICS_TABLE: MetricsTableBlock,
  TOP_CONTENT: TopContentBlock,
  ATTRIBUTION_TABLE: AttributionTableBlock,
  CHART: ChartBlock,
} as const;

export default function BlockRenderer({
  block,
  report,
}: {
  block: ReportBlockDto;
  report: ReportDto;
}) {
  const Component = BLOCK_COMPONENTS[block.type as keyof typeof BLOCK_COMPONENTS];
  if (!Component) {
    console.warn("unknown_block_type", block.type);
    return null;
  }
  return <Component block={block} report={report} />;
}
```

- [ ] **Step 2: KpiGridBlock (reusa KpiTile)**

Crear `frontend/app/reports/[id]/blocks/KpiGridBlock.tsx`:

```tsx
import type { ReportBlockDto, ReportDto, Network } from "@/lib/api";
import KpiTile from "../components/KpiTile";

const NETWORKS: Network[] = ["INSTAGRAM", "TIKTOK", "X"];

type KpiSource =
  | "reach_total"
  | "reach_organic"
  | "reach_influencer"
  | "reach_paid"
  | "engagement_total";

type Tile = { label: string; source: KpiSource };

type KpiGridConfig = { title?: string; tiles: Tile[] };

function sumReachByType(
  report: ReportDto,
  filter: "total" | "ORGANIC" | "INFLUENCER" | "PAID",
): number {
  return NETWORKS.reduce((acc, n) => {
    return (
      acc +
      report.metrics
        .filter(
          (m) =>
            m.network === n &&
            m.metric_name === "reach" &&
            (filter === "total" ? true : m.source_type === filter),
        )
        .reduce((a, m) => a + Number(m.value), 0)
    );
  }, 0);
}

function sumEngagement(report: ReportDto): number {
  return report.metrics
    .filter((m) => m.metric_name === "engagement")
    .reduce((a, m) => a + Number(m.value), 0);
}

function computeTileValue(report: ReportDto, source: KpiSource): number {
  switch (source) {
    case "reach_total":
      return sumReachByType(report, "total");
    case "reach_organic":
      return sumReachByType(report, "ORGANIC");
    case "reach_influencer":
      return sumReachByType(report, "INFLUENCER");
    case "reach_paid":
      return sumReachByType(report, "PAID");
    case "engagement_total":
      return sumEngagement(report);
    default:
      return 0;
  }
}

export default function KpiGridBlock({
  block,
  report,
}: {
  block: ReportBlockDto;
  report: ReportDto;
}) {
  const cfg = block.config as unknown as KpiGridConfig;
  if (!Array.isArray(cfg?.tiles) || cfg.tiles.length === 0) {
    console.warn("invalid_kpi_grid_config", block.id, cfg);
    return null;
  }

  const values = cfg.tiles.map((t) => computeTileValue(report, t.source));
  if (values.every((v) => v === 0)) return null;

  return (
    <section style={{ marginBottom: 48 }}>
      {cfg.title ? <span className="pill-title">{cfg.title.toUpperCase()}</span>
        : <span className="pill-title">KPIs DEL MES</span>}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))",
          gap: 16,
          marginTop: 16,
        }}
      >
        {cfg.tiles.map((tile, i) => (
          <KpiTile key={i} label={tile.label} value={values[i]} />
        ))}
      </div>
    </section>
  );
}
```

- [ ] **Step 3: MetricsTableBlock (unifica NetworkSection/MonthlyCompare/YoyComparison/Q1Rollup)**

Crear `frontend/app/reports/[id]/blocks/MetricsTableBlock.tsx`:

```tsx
import type { ReportBlockDto, ReportDto, Network, SourceType } from "@/lib/api";

type Filter = {
  network?: Network | null;
  source_type?: SourceType | null;
  has_comparison?: boolean | null;
};

type MetricsTableConfig = {
  title?: string;
  source: "metrics" | "yoy" | "q1_rollup";
  filter?: Filter;
};

function formatInt(n: number) {
  return n.toLocaleString("es-AR");
}

function renderMetricsRows(report: ReportDto, filter: Filter) {
  const rows = report.metrics.filter((m) => {
    if (filter.network && m.network !== filter.network) return false;
    if (filter.source_type && m.source_type !== filter.source_type) return false;
    if (filter.has_comparison && m.period_comparison === null) return false;
    return true;
  });
  if (rows.length === 0) return null;
  return (
    <table style={{ width: "100%", borderCollapse: "collapse", marginTop: 12 }}>
      <thead>
        <tr>
          <th scope="col" style={{ textAlign: "left", padding: "8px 12px" }}>Métrica</th>
          <th scope="col" style={{ textAlign: "right", padding: "8px 12px" }}>Valor</th>
          <th scope="col" style={{ textAlign: "right", padding: "8px 12px" }}>Δ</th>
        </tr>
      </thead>
      <tbody>
        {rows.map((m, i) => (
          <tr key={i} style={{ borderTop: "1px solid rgba(0,0,0,0.05)" }}>
            <td style={{ padding: "8px 12px" }}>
              {m.network} · {m.source_type} · {m.metric_name}
            </td>
            <td style={{ textAlign: "right", padding: "8px 12px" }}>
              {formatInt(Number(m.value))}
            </td>
            <td style={{ textAlign: "right", padding: "8px 12px" }}>
              {m.period_comparison !== null ? `${m.period_comparison}%` : "—"}
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

function renderYoy(report: ReportDto) {
  if (!report.yoy || report.yoy.length === 0) return null;
  return (
    <table style={{ width: "100%", borderCollapse: "collapse", marginTop: 12 }}>
      <thead>
        <tr>
          <th scope="col" style={{ textAlign: "left", padding: "8px 12px" }}>Métrica</th>
          <th scope="col" style={{ textAlign: "right", padding: "8px 12px" }}>Hoy</th>
          <th scope="col" style={{ textAlign: "right", padding: "8px 12px" }}>Hace 1 año</th>
        </tr>
      </thead>
      <tbody>
        {report.yoy.map((r, i) => (
          <tr key={i} style={{ borderTop: "1px solid rgba(0,0,0,0.05)" }}>
            <td style={{ padding: "8px 12px" }}>{r.network} · {r.metric}</td>
            <td style={{ textAlign: "right", padding: "8px 12px" }}>{formatInt(r.current)}</td>
            <td style={{ textAlign: "right", padding: "8px 12px" }}>{formatInt(r.year_ago)}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

function renderQ1(report: ReportDto) {
  const q = report.q1_rollup;
  if (!q || q.rows.length === 0) return null;
  return (
    <table style={{ width: "100%", borderCollapse: "collapse", marginTop: 12 }}>
      <thead>
        <tr>
          <th scope="col" style={{ textAlign: "left", padding: "8px 12px" }}>Métrica</th>
          {q.months.map((m) => (
            <th key={m} scope="col" style={{ textAlign: "right", padding: "8px 12px" }}>{m}</th>
          ))}
        </tr>
      </thead>
      <tbody>
        {q.rows.map((r, i) => (
          <tr key={i} style={{ borderTop: "1px solid rgba(0,0,0,0.05)" }}>
            <td style={{ padding: "8px 12px" }}>{r.network} · {r.metric}</td>
            {r.values.map((v, j) => (
              <td key={j} style={{ textAlign: "right", padding: "8px 12px" }}>
                {v === null ? "—" : formatInt(v)}
              </td>
            ))}
          </tr>
        ))}
      </tbody>
    </table>
  );
}

export default function MetricsTableBlock({
  block,
  report,
}: {
  block: ReportBlockDto;
  report: ReportDto;
}) {
  const cfg = block.config as unknown as MetricsTableConfig;
  if (!cfg || !["metrics", "yoy", "q1_rollup"].includes(cfg.source)) {
    console.warn("invalid_metrics_table_config", block.id, cfg);
    return null;
  }

  let body: React.ReactNode = null;
  if (cfg.source === "metrics") body = renderMetricsRows(report, cfg.filter ?? {});
  else if (cfg.source === "yoy") body = renderYoy(report);
  else if (cfg.source === "q1_rollup") body = renderQ1(report);

  if (!body) return null;

  return (
    <section style={{ marginBottom: 48 }}>
      {cfg.title && <span className="pill-title">{cfg.title.toUpperCase()}</span>}
      {body}
    </section>
  );
}
```

- [ ] **Step 4: TopContentBlock**

Crear `frontend/app/reports/[id]/blocks/TopContentBlock.tsx`:

```tsx
import type { ReportBlockDto, ReportDto, TopContentDto } from "@/lib/api";
import ContentCard from "../components/ContentCard";

type TopContentConfig = { title?: string; kind: "POST" | "CREATOR"; limit?: number };

export default function TopContentBlock({
  block,
  report,
}: {
  block: ReportBlockDto;
  report: ReportDto;
}) {
  const cfg = block.config as unknown as TopContentConfig;
  if (!cfg || (cfg.kind !== "POST" && cfg.kind !== "CREATOR")) {
    console.warn("invalid_top_content_config", block.id, cfg);
    return null;
  }
  const limit = typeof cfg.limit === "number" && cfg.limit > 0 ? cfg.limit : 6;
  const items: TopContentDto[] = report.top_content
    .filter((c) => c.kind === cfg.kind)
    .slice(0, limit);

  if (items.length === 0) return null;

  const title = cfg.title ?? (cfg.kind === "POST" ? "Posts del mes" : "Creators del mes");

  return (
    <section style={{ marginBottom: 48 }}>
      <span className="pill-title">{title.toUpperCase()}</span>
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fill, minmax(220px, 1fr))",
          gap: 16,
          marginTop: 16,
        }}
      >
        {items.map((item, i) => (
          <ContentCard key={i} content={item} />
        ))}
      </div>
    </section>
  );
}
```

> **Nota:** `ContentCard` ya existe en `frontend/app/reports/[id]/components/ContentCard.tsx` y acepta `content: TopContentDto`. Reusarlo tal cual.

- [ ] **Step 5: AttributionTableBlock**

Crear `frontend/app/reports/[id]/blocks/AttributionTableBlock.tsx`:

```tsx
import type { ReportBlockDto, ReportDto } from "@/lib/api";

type AttributionTableConfig = { title?: string; show_total?: boolean };

export default function AttributionTableBlock({
  block,
  report,
}: {
  block: ReportBlockDto;
  report: ReportDto;
}) {
  const cfg = (block.config ?? {}) as AttributionTableConfig;
  const rows = report.onelink ?? [];
  if (rows.length === 0) return null;

  const showTotal = cfg.show_total !== false;
  const totalClicks = rows.reduce((a, r) => a + r.clicks, 0);
  const totalDownloads = rows.reduce((a, r) => a + r.app_downloads, 0);
  const title = cfg.title ?? "Atribución OneLink";

  return (
    <section style={{ marginBottom: 48 }}>
      <span className="pill-title">{title.toUpperCase()}</span>
      <table style={{ width: "100%", borderCollapse: "collapse", marginTop: 12 }}>
        <thead>
          <tr>
            <th scope="col" style={{ textAlign: "left", padding: "8px 12px" }}>Influencer</th>
            <th scope="col" style={{ textAlign: "right", padding: "8px 12px" }}>Clicks</th>
            <th scope="col" style={{ textAlign: "right", padding: "8px 12px" }}>Descargas</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((r, i) => (
            <tr key={i} style={{ borderTop: "1px solid rgba(0,0,0,0.05)" }}>
              <td style={{ padding: "8px 12px" }}>{r.influencer_handle}</td>
              <td style={{ textAlign: "right", padding: "8px 12px" }}>
                {r.clicks.toLocaleString("es-AR")}
              </td>
              <td style={{ textAlign: "right", padding: "8px 12px" }}>
                {r.app_downloads.toLocaleString("es-AR")}
              </td>
            </tr>
          ))}
          {showTotal && (
            <tr style={{ borderTop: "2px solid rgba(0,0,0,0.15)", fontWeight: 600 }}>
              <td style={{ padding: "8px 12px" }}>Total</td>
              <td style={{ textAlign: "right", padding: "8px 12px" }}>
                {totalClicks.toLocaleString("es-AR")}
              </td>
              <td style={{ textAlign: "right", padding: "8px 12px" }}>
                {totalDownloads.toLocaleString("es-AR")}
              </td>
            </tr>
          )}
        </tbody>
      </table>
    </section>
  );
}
```

- [ ] **Step 6: ChartBlock (reusa BarChartMini u otro gráfico existente)**

Crear `frontend/app/reports/[id]/blocks/ChartBlock.tsx`:

```tsx
import type { ReportBlockDto, ReportDto } from "@/lib/api";
import BarChartMini from "../components/BarChartMini";

type ChartConfig = {
  title?: string;
  source: "follower_snapshots";
  group_by: "network";
  chart_type: "bar";
};

const LABELS: Record<string, string> = {
  INSTAGRAM: "Instagram",
  TIKTOK: "TikTok",
  X: "X / Twitter",
};

export default function ChartBlock({
  block,
  report,
}: {
  block: ReportBlockDto;
  report: ReportDto;
}) {
  const cfg = block.config as unknown as ChartConfig;
  if (cfg?.source !== "follower_snapshots" || cfg.group_by !== "network" || cfg.chart_type !== "bar") {
    console.warn("invalid_chart_config", block.id, cfg);
    return null;
  }
  const entries = Object.entries(report.follower_snapshots ?? {})
    .filter(([, arr]) => arr.length >= 2);
  if (entries.length === 0) return null;

  const title = cfg.title ?? "Follower growth";

  return (
    <section style={{ marginBottom: 48 }}>
      <span className="pill-title mint">{title.toUpperCase()}</span>
      <div style={{ display: "flex", flexDirection: "column", gap: 32, marginTop: 16 }}>
        {entries.map(([network, arr]) => (
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

- [ ] **Step 7: TextImageBlock**

Crear `frontend/app/reports/[id]/blocks/TextImageBlock.tsx`:

```tsx
import type { ReportBlockDto } from "@/lib/api";

type TextImageConfig = {
  title?: string;
  text?: string;
  columns: 1 | 2 | 3;
  image_position: "left" | "right" | "top";
};

export default function TextImageBlock({ block }: { block: ReportBlockDto }) {
  const cfg = block.config as unknown as TextImageConfig;
  if (!cfg || ![1, 2, 3].includes(cfg.columns as number)) {
    console.warn("invalid_text_image_config", block.id, cfg);
    return null;
  }
  const hasImage = !!block.image_url;
  const hasText = !!(cfg.text || cfg.title);
  if (!hasImage && !hasText) return null;

  const position = cfg.image_position ?? "top";
  const direction =
    position === "top" || !hasImage
      ? "column"
      : position === "right"
        ? "row"
        : "row-reverse";

  return (
    <section style={{ marginBottom: 48 }}>
      {cfg.title && <span className="pill-title">{cfg.title.toUpperCase()}</span>}
      <div
        style={{
          display: "flex",
          flexDirection: direction,
          gap: 24,
          alignItems: "flex-start",
          marginTop: 16,
        }}
      >
        {hasImage && (
          // eslint-disable-next-line @next/next/no-img-element
          <img
            src={block.image_url!}
            alt=""
            style={{ maxWidth: hasText ? "50%" : "100%", borderRadius: 8 }}
          />
        )}
        {cfg.text && (
          <div
            style={{
              columnCount: cfg.columns,
              columnGap: 24,
              maxWidth: 720,
              whiteSpace: "pre-wrap",
            }}
          >
            {cfg.text}
          </div>
        )}
      </div>
    </section>
  );
}
```

- [ ] **Step 8: Type-check**

Run: `docker compose exec frontend npx tsc --noEmit`
Expected: sin errores.

- [ ] **Step 9: Commit**

```bash
git add frontend/app/reports/\[id\]/blocks/
git commit -m "feat(frontend): add BlockRenderer dispatcher and six block components"
```

---

### Task 9: Refactor `page.tsx` + botón PDF en `HeaderSection`

**Files:**
- Modify: `frontend/app/reports/[id]/page.tsx`
- Modify: `frontend/app/reports/[id]/sections/HeaderSection.tsx`

- [ ] **Step 1: Refactor page.tsx**

Reemplazar `frontend/app/reports/[id]/page.tsx` por:

```tsx
import { notFound, redirect } from "next/navigation";
import { apiFetch, ApiError, type ReportDto } from "@/lib/api";
import { getAccessToken, getCurrentUser } from "@/lib/auth";
import TopBar from "@/components/top-bar";

import HeaderSection from "./sections/HeaderSection";
import IntroText from "./sections/IntroText";
import ConclusionsSection from "./sections/ConclusionsSection";
import BlockRenderer from "./blocks/BlockRenderer";

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
        {report.blocks.map((block) => (
          <BlockRenderer key={block.id} block={block} report={report} />
        ))}
        <ConclusionsSection report={report} />
      </main>
    </>
  );
}
```

- [ ] **Step 2: Botón PDF en HeaderSection**

Editar `frontend/app/reports/[id]/sections/HeaderSection.tsx` para agregar el botón condicional antes del cierre de la `<section>`:

```tsx
      <p style={{ fontSize: 14, color: "var(--chirri-muted)", marginTop: 8 }}>
        Etapa: {report.stage_name} · Publicado: {formatReportDate(report.published_at)}
      </p>
      {report.original_pdf_url && (
        <a
          href={report.original_pdf_url}
          download
          aria-label="Descargar PDF original"
          style={{
            display: "inline-block",
            marginTop: 12,
            padding: "8px 16px",
            border: "1px solid var(--chirri-black)",
            borderRadius: 999,
            fontSize: 14,
            textDecoration: "none",
          }}
        >
          Descargar PDF
        </a>
      )}
    </section>
```

- [ ] **Step 3: Type-check**

Run: `docker compose exec frontend npx tsc --noEmit`
Expected: sin errores.

- [ ] **Step 4: Arrancar el stack y probar visualmente**

Run: `docker compose up -d`

Abrir `http://localhost:3000`, loguearse con `belen.rizzo@balanz.com` / `balanz2026`, abrir el reporte "Reporte general · Marzo" de EDUCATION. Confirmar que:
- KPIs en la parte superior renderizan con números reales.
- Tablas de métricas por red aparecen en orden (Mes a mes, YoY, Instagram, TikTok, X).
- Top posts y Top creators renderizan.
- Tabla de atribución aparece.
- Chart de followers aparece.
- Tabla Q1 rollup al final.
- Conclusiones cierran el reporte.

Sacar screenshot si algo difiere del render previo — la paridad visual es el criterio de éxito.

- [ ] **Step 5: Remover secciones obsoletas**

Los archivos en `frontend/app/reports/[id]/sections/` que ahora son reemplazados por bloques — `KpisSummary.tsx`, `MonthlyCompare.tsx`, `YoyComparison.tsx`, `NetworkSection.tsx`, `BestContentChapter.tsx`, `OneLinkTable.tsx`, `FollowerGrowthSection.tsx`, `Q1RollupTable.tsx` — pueden borrarse ahora porque `page.tsx` ya no los importa.

Borrar los 8 archivos. Mantener `HeaderSection.tsx`, `IntroText.tsx`, `ConclusionsSection.tsx`.

Run: `docker compose exec frontend npx tsc --noEmit` de nuevo para confirmar que nadie más los importa.

- [ ] **Step 6: Commit**

```bash
git add frontend/app/reports/\[id\]/page.tsx frontend/app/reports/\[id\]/sections/
git commit -m "refactor(frontend): render report via blocks and expose pdf download"
```

---

### Task 10: E2E smoke test — `Report viewer · blocks`

**Files:**
- Create: `frontend/tests/report-blocks.spec.ts`

- [ ] **Step 1: Escribir los E2E tests**

Crear `frontend/tests/report-blocks.spec.ts`:

```typescript
import { test, expect } from "@playwright/test";
import { login, trackConsoleErrors } from "./helpers";

test.describe("Report viewer · blocks", () => {
  test("seeded report renders all block sections in order", async ({ page }) => {
    const errors = trackConsoleErrors(page);

    await login(page);
    await page.goto("/campaigns");
    const activeSection = page
      .locator("section")
      .filter({ has: page.getByText(/activas ·/i) });
    await activeSection.getByRole("link").first().click();
    await expect(page).toHaveURL(/\/campaigns\/\d+$/);

    // Open first published report
    await page.locator('a[href^="/reports/"]').first().click();
    await expect(page).toHaveURL(/\/reports\/\d+$/);

    // Pill-titles we expect in order (from seed_demo blocks).
    const expectedPills = [
      /KPIS DEL MES/i,
      /MES A MES/i,
      /YEAR OVER YEAR/i,
      /INSTAGRAM/i,
      /TIKTOK/i,
      /X \/ TWITTER/i,
      /POSTS DEL MES/i,
      /CREATORS DEL MES/i,
      /ATRIBUCIÓN ONELINK/i,
      /FOLLOWERS/i,
      /Q1 ROLLUP/i,
    ];
    for (const pill of expectedPills) {
      await expect(page.getByText(pill).first()).toBeVisible();
    }

    // Verify DOM order: first pill appears before last in DOM.
    const firstPill = page.getByText(expectedPills[0]).first();
    const lastPill = page.getByText(expectedPills[expectedPills.length - 1]).first();
    const firstBox = await firstPill.boundingBox();
    const lastBox = await lastPill.boundingBox();
    expect(firstBox && lastBox && firstBox.y < lastBox.y).toBeTruthy();

    expect(
      errors,
      `console/page errors on /reports/<id>:\n${errors.join("\n")}`,
    ).toEqual([]);
  });

  test("PDF download button absent when report has no original_pdf", async ({ page }) => {
    await login(page);
    await page.goto("/campaigns");
    const activeSection = page
      .locator("section")
      .filter({ has: page.getByText(/activas ·/i) });
    await activeSection.getByRole("link").first().click();
    await page.locator('a[href^="/reports/"]').first().click();
    await expect(page).toHaveURL(/\/reports\/\d+$/);

    // seed_demo doesn't upload PDFs, so button should not appear.
    await expect(page.getByRole("link", { name: /descargar pdf original/i })).toHaveCount(0);
  });
});
```

- [ ] **Step 2: Run E2E**

Run: `cd frontend && npm run test:e2e:smoke -- --grep "Report viewer · blocks"`
Expected: ambos tests PASS.

- [ ] **Step 3: Correr la battery completa**

Run: `cd frontend && npm run test:battery`
Expected: backend pytest + E2E smoke full pasan en verde.

- [ ] **Step 4: Commit**

```bash
git add frontend/tests/report-blocks.spec.ts
git commit -m "test(e2e): report viewer blocks smoke"
```

---

### Task 11: Docs update + archivar plan

**Files:**
- Modify: `README.md`
- Move: `docs/superpowers/plans/2026-04-20-report-block-model.md` → `docs/superpowers/plans/completed/`

- [ ] **Step 1: Actualizar README**

Abrir `README.md` y agregar/actualizar una sección "Reportes" explicando el modelo de bloques. Texto mínimo:

```markdown
### Reportes

Cada `Report` tiene una base fija (título, período, intro, conclusiones, `original_pdf` opcional)
y una lista ordenada de `ReportBlock`. Los bloques definen qué se muestra y en qué orden; la data
viene del `Report` agregado. Tipos soportados en fase 1:

| Tipo               | Cuándo usarlo                                              |
|--------------------|------------------------------------------------------------|
| `TEXT_IMAGE`       | Bloque narrativo con título, texto multi-columna e imagen. |
| `KPI_GRID`         | Tarjetas de KPIs (reach total / orgánico / influencer).    |
| `METRICS_TABLE`    | Tabla filtrable de métricas, YoY o Q1 rollup.              |
| `TOP_CONTENT`      | Grid de mejores posts o creators.                          |
| `ATTRIBUTION_TABLE`| Tabla de OneLink (clicks + descargas por influencer).      |
| `CHART`            | Bar chart de follower snapshots por red.                   |

Los bloques se crean desde Django admin (reordenables con drag-drop) o vía `seed_demo`.
Tras mergear DEV-105 en prod, correr una vez:

    docker compose exec backend python manage.py seed_demo --wipe

para regenerar los reportes demo con bloques.
```

Ajustar estilo/wording si el README ya tiene una sección de reportes — no duplicar.

- [ ] **Step 2: Archivar el plan**

Mover el archivo:

```bash
mkdir -p docs/superpowers/plans/completed
git mv docs/superpowers/plans/2026-04-20-report-block-model.md docs/superpowers/plans/completed/
```

- [ ] **Step 3: Commit**

```bash
git add README.md docs/superpowers/plans/
git commit -m "docs(reports): document block model and archive DEV-105 plan"
```

---

## Final verification

- [ ] **Battery full verde**

Run: `cd frontend && npm run test:battery`
Expected: backend pytest + E2E smoke todo en verde.

- [ ] **CI/CD pipeline check (5 stages — spec §11.13)**

Confirmar, antes de abrir PR, que cada etapa del pipeline Impactia está cubierta:

1. **PR gate** (`.github/workflows/test.yml`): corre backend pytest + frontend typecheck + E2E smoke en push/PR a `main`/`development`. **Sin cambios** — ya es required check. Verificar abriendo el archivo y confirmando que `push` y `pull_request` triggers existen.
2. **Build**: `deploy.yml` construye el Docker image en el host Hetzner (`docker compose ... build`) a partir del checkout de `development`. La nueva dep `django-admin-sortable2==2.1.10` entra en el build por `requirements.txt` (Task 4). Sin `:latest` tags — el build es por SHA (`git reset --hard origin/development`).
3. **Branch → env mapping**: `deploy.yml` tiene `on.push.branches: [development]` → deploy a Hetzner. `main` queda production-ready. **Sin cambios**.
4. **Post-deploy smoke**: `deploy.yml` línea 66: `npx playwright test --grep "Report viewer|Home smoke|Campaign detail" --reporter=line` contra `PLAYWRIGHT_BASE_URL=${{ secrets.DEPLOY_URL }}`. El `describe("Report viewer · blocks", …)` en Task 10 **matchea** el regex `Report viewer` → el nuevo spec entra al smoke post-deploy automáticamente. Verificar con: `grep -n "describe" frontend/tests/report-blocks.spec.ts`.
5. **Rollback documentado**: en caso de regresión en prod → `git revert <merge-commit> && git push origin development` dispara redeploy al commit anterior. La migración `00XX_report_blocks_and_pdf` es reversible (`python manage.py migrate reports <prev>`) pero implica perder bloques creados; mejor revertir solo frontend si los bloques ya fueron editados en admin. Documentado en README §Reportes (Task 11).

Verificar que **no se introdujeron secrets nuevos** — `grep -rn "secrets\." .github/workflows/` no debería tener entradas nuevas. Todos los secrets (`HETZNER_*`, `DEPLOY_URL`) ya existen.

- [ ] **Entropy-aware enriquece este plan** — se ejecuta inmediatamente después de escribir este plan (Step 4 del pipeline entropy-driven). No requiere acción del implementador.

- [ ] **Visual regression (e2e-frontend)** — se dispara automáticamente en Step 5.5 del pipeline. Si el render difiere visualmente vs baseline, el usuario decide si actualizar snapshots o fixear la UI.

- [ ] **Entropy-scan post-ejecución** — Step 6 del pipeline; scanea `backend/reports` + `frontend/reports`. Criterio de éxito: ambos dominios en grade ≥ B.

- [ ] **Ship-with-review** — Step 8 crea PR con título corto y body que referencia spec + plan + grades.

---

## Notas para el implementador

- **Nunca hagas `git push` ni `git merge` sin confirmación del usuario.** El pipeline lo hace ship-with-review al final.
- **Cada task termina con un commit**. No batches de varios tasks en un solo commit.
- **Cuando un test pide `balanz_published_report`, ese fixture ya existe** — viene de `backend/conftest.py` (verificar con `grep -rn balanz_published_report backend/` si hay dudas).
- **Si un step se rompe con un error inesperado**, parar y reportar — no inventes workarounds.
- **Tenant scoping** en el backend va en la view, no en middleware (CLAUDE.md gotcha). No tocar ese patrón en este plan — solo se extiende prefetch.
- **Usá `docker compose exec backend ...`** para todos los comandos de Django/pytest. El stack levanta con `docker compose up -d`.
- **TopContentInline y OneLinkAttributionInline** estaban originalmente planeados para DEV-83 pero entran acá porque los bloques `TOP_CONTENT` y `ATTRIBUTION_TABLE` los necesitan populados para ser útiles.
