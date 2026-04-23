# DEV-116 Typed Blocks Refactor Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reemplazar el modelo `ReportBlock` `type + config: JSONField` por jerarquía tipada con herencia multi-tabla de Django + `django-polymorphic`, eliminando `ReportMetric` y los agregados cross-report.

**Architecture:** Multi-table inheritance desde `ReportBlock` base (ahora `PolymorphicModel`) a 6 subtipos (`TextImageBlock`, `KpiGridBlock`, `MetricsTableBlock`, `TopContentBlock`, `AttributionTableBlock`, `ChartBlock`). Cada subtipo con columnas tipadas; las listas de items (tiles, rows, data_points) son tablas FK propias. `TopContent` y `OneLinkAttribution` migran su FK al subtipo específico. `ReportMetric` se elimina.

**Tech Stack:** Django 5.0 + DRF 3.15 + `django-polymorphic` (nuevo) + `django-admin-sortable2` (ya presente) + pytest-django + Next.js 14 + TypeScript.

**Spec:** `docs/superpowers/specs/2026-04-22-dev-116-typed-blocks-refactor-design.md`

**Ticket:** [DEV-116](https://linear.app/impactia/issue/DEV-116)

**Branch sugerida:** `dzacharias/dev-116-typed-blocks-refactor`

---

## Pre-flight

Antes de arrancar:

- [ ] **Crear branch desde `development`**

```bash
cd "C:/Users/danie/Impactia/Git/Chirri Peppers/Chirri Portal"
git checkout development
git pull
git checkout -b dzacharias/dev-116-typed-blocks-refactor
```

- [ ] **Verificar stack arriba**

```bash
docker compose ps --format "{{.Service}}: {{.State}}"
```
Expected: `backend: running`, `db: running`, `redis: running`, `frontend: running`.

- [ ] **Baseline: tests actuales en verde**

```bash
docker compose exec -T backend pytest backend/tests/unit/ -q
cd frontend && npm run typecheck && npm run test:e2e:smoke
```
Expected: todo pasa. Si algo falla antes de empezar, stop y reportar.

---

## Phase 1 — Dependencies + choices module

**Goal:** Agregar `django-polymorphic`, extraer `Network` / `SourceType` a módulo reusable.

### Task 1.1: Agregar django-polymorphic a requirements

**Files:**
- Modify: `backend/requirements.txt`

- [ ] **Step 1: Verificar versión compatible + dependency audit (P7)**

Ver https://pypi.org/project/django-polymorphic/. Última release compatible con Django 5: `django-polymorphic==3.1.0`.

Chequeo de sanidad (spec dim 7 — security by default):

```bash
# License: debe ser OSI-compatible (django-polymorphic es BSD-3-Clause)
pip show django-polymorphic 2>/dev/null | grep -i license
# Last release date: no más de 18 meses de antigüedad
# Ver PyPI → Project description → Release history
```

Expected: License BSD-3-Clause, release ≤18 meses atrás. Si no cumple, escalar al PR reviewer antes de proceder.

Agregar entry en `docs/ENV.md` o `docs/DEPENDENCIES.md` (crear si no existe) registrando: nombre, versión, license, propósito, last-audited date.

- [ ] **Step 2: Agregar a requirements.txt**

```
# Abrir backend/requirements.txt y agregar después de django-admin-sortable2:
django-polymorphic==3.1.0
```

- [ ] **Step 3: Rebuildear imagen backend**

```bash
docker compose build backend
docker compose up -d backend
```

- [ ] **Step 4: Verificar import**

```bash
docker compose exec -T backend python -c "from polymorphic.models import PolymorphicModel; print('ok')"
```
Expected: `ok`.

- [ ] **Step 5: Agregar app a INSTALLED_APPS**

Modify: `backend/config/settings.py` — buscar `INSTALLED_APPS` y agregar `"polymorphic"` antes de las apps propias del proyecto:

```python
INSTALLED_APPS = [
    # ... django defaults ...
    "polymorphic",   # nuevo — necesario para MTI de ReportBlock
    # ... apps propias ...
]
```

- [ ] **Step 6: Verificar startup sin errores**

```bash
docker compose exec -T backend python manage.py check
```
Expected: `System check identified no issues (0 silenced).`

- [ ] **Step 7: Commit**

```bash
git add backend/requirements.txt backend/config/settings.py
git commit -m "build(backend): add django-polymorphic 3.1.0 for typed block MTI"
```

---

### Task 1.2: Extraer Network/SourceType a choices.py

**Files:**
- Create: `backend/apps/reports/choices.py`
- Modify: `backend/apps/reports/models.py` (imports)

- [ ] **Step 1: Write failing test**

Create: `backend/tests/unit/test_reports_choices.py`

```python
"""Network y SourceType ahora viven en choices.py — evita coupling con
ReportMetric (que se va a eliminar en DEV-116)."""
import pytest


def test_network_choices_importable_from_choices_module():
    from apps.reports.choices import Network
    assert Network.INSTAGRAM == "INSTAGRAM"
    assert Network.TIKTOK == "TIKTOK"
    assert Network.X == "X"


def test_source_type_choices_importable_from_choices_module():
    from apps.reports.choices import SourceType
    assert SourceType.ORGANIC == "ORGANIC"
    assert SourceType.INFLUENCER == "INFLUENCER"
    assert SourceType.PAID == "PAID"


def test_network_choices_backward_compatible_via_reportmetric():
    """Mientras ReportMetric exista (fase transicional), sus choices
    siguen funcionando igual."""
    from apps.reports.models import ReportMetric
    assert ReportMetric.Network.INSTAGRAM == "INSTAGRAM"
```

- [ ] **Step 2: Run test to verify it fails**

```bash
docker compose exec -T backend pytest backend/tests/unit/test_reports_choices.py -v
```
Expected: FAIL — `ModuleNotFoundError: No module named 'apps.reports.choices'`

- [ ] **Step 3: Create choices.py**

Create: `backend/apps/reports/choices.py`

```python
"""Choices compartidos por los bloques tipados (DEV-116).

Extraído de ReportMetric para que los bloques puedan referenciarlos sin
depender de un modelo que está siendo eliminado.
"""
from django.db import models


class Network(models.TextChoices):
    INSTAGRAM = "INSTAGRAM", "Instagram"
    TIKTOK = "TIKTOK", "TikTok"
    X = "X", "X/Twitter"


class SourceType(models.TextChoices):
    ORGANIC = "ORGANIC", "Orgánico"
    INFLUENCER = "INFLUENCER", "Influencer"
    PAID = "PAID", "Pauta"
```

- [ ] **Step 4: Update ReportMetric to re-export from choices**

Modify `backend/apps/reports/models.py` — cambiar las clases internas de `ReportMetric` para que apunten al módulo nuevo:

```python
# En el top del archivo (después de los imports existentes):
from .choices import Network, SourceType

# Dentro de ReportMetric, reemplazar las clases Network y SourceType internas:
class ReportMetric(models.Model):
    """A single metric value in a Report, tagged by network and source type."""

    # Back-compat aliases — Network y SourceType viven en choices.py ahora.
    Network = Network
    SourceType = SourceType

    # resto del modelo sin cambios...
```

- [ ] **Step 5: Run test to verify passes**

```bash
docker compose exec -T backend pytest backend/tests/unit/test_reports_choices.py -v
```
Expected: 3 passed.

- [ ] **Step 6: Run full backend suite to verify no regression**

```bash
docker compose exec -T backend pytest backend/tests/unit/ -q
```
Expected: todos pasan (con las adaptaciones triviales si rompió algún test por cambio de import path).

- [ ] **Step 7: Commit**

```bash
git add backend/apps/reports/choices.py backend/apps/reports/models.py backend/tests/unit/test_reports_choices.py
git commit -m "refactor(reports): extract Network/SourceType to choices.py

Preparation for DEV-116: decouples enum definitions from ReportMetric
so typed blocks can reference them without a doomed model.

Backward compatibility preserved via ReportMetric.Network/SourceType
aliases."
```

---

## Phase 2 — Scaffold typed block models + migration

**Goal:** Implementar los 6 subtipos MTI + 3 child tables. Migración destructiva 0009. Al terminar esta fase, los modelos viejos (`ReportBlock.type`, `config`, `image`, `ReportMetric`) están eliminados.

### Task 2.1: Write failing tests para ReportBlock base polymorphic

**Files:**
- Create: `backend/tests/unit/blocks/__init__.py`
- Create: `backend/tests/unit/blocks/test_report_block_base.py`

- [ ] **Step 1: Create test directory structure**

```bash
mkdir -p backend/tests/unit/blocks && touch backend/tests/unit/blocks/__init__.py
```

- [ ] **Step 2: Write failing test**

Create: `backend/tests/unit/blocks/test_report_block_base.py`

```python
"""Tests para ReportBlock base post-DEV-116.

Verifica que ReportBlock ahora es PolymorphicModel, tiene campos base
(report, order, instructions, timestamps) y NO tiene los campos viejos
(type, config, image).
"""
import pytest
from django.db import IntegrityError


@pytest.mark.django_db
def test_report_block_is_polymorphic_model():
    from polymorphic.models import PolymorphicModel
    from apps.reports.models import ReportBlock
    assert issubclass(ReportBlock, PolymorphicModel)


@pytest.mark.django_db
def test_report_block_base_fields_exist():
    from apps.reports.models import ReportBlock
    fields = {f.name for f in ReportBlock._meta.get_fields()}
    assert {"report", "order", "instructions", "created_at", "updated_at"}.issubset(fields)


@pytest.mark.django_db
def test_report_block_old_fields_gone():
    from apps.reports.models import ReportBlock
    fields = {f.name for f in ReportBlock._meta.get_fields()}
    assert "config" not in fields
    assert "type" not in fields
    assert "image" not in fields


@pytest.mark.django_db
def test_report_block_uniq_order_per_report(report_factory):
    """El constraint UniqueConstraint(report, order) sigue vigente."""
    from apps.reports.models import ReportBlock, TextImageBlock
    report = report_factory()
    TextImageBlock.objects.create(report=report, order=1, title="A")
    with pytest.raises(IntegrityError):
        TextImageBlock.objects.create(report=report, order=1, title="B")


@pytest.mark.django_db
def test_instructions_field_defaults_blank():
    from apps.reports.models import TextImageBlock
    from apps.reports.tests.factories import make_report
    report = make_report()
    block = TextImageBlock.objects.create(report=report, order=1)
    assert block.instructions == ""
```

> **Nota:** `report_factory` y `make_report` se crean en Task 2.2. Si ejecutás este test antes, va a fallar por import error — es esperado (TDD).

- [ ] **Step 3: Run to verify it fails**

```bash
docker compose exec -T backend pytest backend/tests/unit/blocks/test_report_block_base.py -v
```
Expected: FAIL con errores de import (factory no existe) y/o `AttributeError` en `_meta.get_fields()`.

### Task 2.2: Create report factory utility

**Files:**
- Create: `backend/apps/reports/tests/__init__.py`
- Create: `backend/apps/reports/tests/factories.py`
- Modify: `backend/tests/conftest.py` (o crear si no existe)

- [ ] **Step 1: Create factory module**

```bash
mkdir -p backend/apps/reports/tests
touch backend/apps/reports/tests/__init__.py
```

Create: `backend/apps/reports/tests/factories.py`

```python
"""Test factories para DEV-116. Factories minimalistas (sin factory_boy
para no agregar deps — helpers funcionales alcanzan)."""
from datetime import date, datetime, timezone

from apps.campaigns.models import Brand, Campaign, Stage
from apps.reports.models import Report
from apps.tenants.models import Client


def make_client(name="Test Client"):
    return Client.objects.create(name=name)


def make_brand(client=None, name="Test Brand"):
    if client is None:
        client = make_client()
    return Brand.objects.create(client=client, name=name)


def make_campaign(brand=None, name="Test Campaign"):
    if brand is None:
        brand = make_brand()
    return Campaign.objects.create(
        brand=brand, name=name, status=Campaign.Status.ACTIVE,
        start_date=date(2026, 1, 1),
    )


def make_stage(campaign=None, order=1, name="Test Stage"):
    if campaign is None:
        campaign = make_campaign()
    return Stage.objects.create(
        campaign=campaign, order=order, name=name,
        kind=Stage.Kind.AWARENESS,
    )


def make_report(stage=None, kind=Report.Kind.GENERAL):
    if stage is None:
        stage = make_stage()
    return Report.objects.create(
        stage=stage, kind=kind,
        period_start=date(2026, 3, 1), period_end=date(2026, 3, 31),
        title="Test Report", status=Report.Status.PUBLISHED,
        published_at=datetime(2026, 4, 2, 12, 0, tzinfo=timezone.utc),
    )
```

- [ ] **Step 2: Create conftest with report_factory fixture**

Create or modify: `backend/tests/conftest.py`

```python
"""Conftest para tests unit de DEV-116."""
import pytest
from apps.reports.tests.factories import make_report


@pytest.fixture
def report_factory(db):
    """Fixture: callable que crea un Report nuevo cada vez."""
    return make_report
```

> Si `backend/tests/conftest.py` ya existe, solo agregar el fixture `report_factory`.

- [ ] **Step 3: Verify import works standalone**

```bash
docker compose exec -T backend python -c "from apps.reports.tests.factories import make_report; print('ok')"
```
Expected: `ok`.

- [ ] **Step 4: (No commit yet — se commitea junto con Task 2.3)**

### Task 2.3: Implement ReportBlock base + TextImageBlock

Primer subtipo end-to-end. Una vez validado, los otros 5 siguen el mismo pattern en Task 2.4.

**Files:**
- Create: `backend/apps/reports/models/__init__.py`
- Create: `backend/apps/reports/models/base.py`
- Create: `backend/apps/reports/models/blocks/__init__.py`
- Create: `backend/apps/reports/models/blocks/base_block.py`
- Create: `backend/apps/reports/models/blocks/text_image.py`
- Modify: legacy `backend/apps/reports/models.py` → rename a `_legacy.py`

> **P2 Single Responsibility + complexity budget**: el spec manda split en módulos.

- [ ] **Step 1: Rename legacy models.py → models_legacy.py**

```bash
mv backend/apps/reports/models.py backend/apps/reports/models_legacy.py
```

Esto rompe imports temporariamente. El Step 2 lo arregla.

- [ ] **Step 2: Create models/ package with __init__.py re-exporting legacy**

Create: `backend/apps/reports/models/__init__.py`

```python
"""Reports domain models — package post-DEV-116 (split por concern).

Durante la transición a bloques tipados, re-exportamos los modelos viejos
desde models_legacy y agregamos los nuevos a medida que existen.
"""
# Legacy (se van a eliminar al cerrar DEV-116):
from apps.reports.models_legacy import (  # noqa: F401
    Report,
    ReportMetric,
    TopContent,
    BrandFollowerSnapshot,
    OneLinkAttribution,
)

# Nuevos tipados (DEV-116):
from .blocks.base_block import ReportBlock  # noqa: F401
from .blocks.text_image import TextImageBlock  # noqa: F401
```

- [ ] **Step 3: Create base_block module**

Create: `backend/apps/reports/models/blocks/__init__.py`

```python
"""Bloques tipados — uno por archivo para mantener los archivos <150 líneas
(complexity budget spec dim 4)."""
```

Create: `backend/apps/reports/models/blocks/base_block.py`

```python
"""ReportBlock base polimórfico — DEV-116.

Cada subtipo hereda de ReportBlock y aporta sus campos tipados. La base
define lo compartido: FK a Report, order, metadata libre (instructions)
y timestamps. `polymorphic_ctype` lo inyecta django-polymorphic.
"""
from django.db import models
from polymorphic.models import PolymorphicModel


class ReportBlock(PolymorphicModel):
    report = models.ForeignKey(
        "reports.Report", on_delete=models.CASCADE, related_name="blocks",
    )
    order = models.PositiveIntegerField(db_index=True)
    instructions = models.TextField(
        blank=True,
        help_text=(
            "Texto libre para guiar al AI (Metricool auto-fill) o al "
            "operador humano. Ej: 'mostrar solo posts con ads, ignorar "
            "los orgánicos de la campaña Q4 vieja'. No se renderiza en "
            "el viewer público."
        ),
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["report", "order"]
        indexes = [models.Index(fields=["report", "order"])]
        constraints = [
            models.UniqueConstraint(
                fields=["report", "order"],
                name="uniq_block_order_per_report",
            ),
        ]

    def __str__(self):
        return f"{self.report_id} · {type(self).__name__} #{self.order}"
```

- [ ] **Step 4: Create TextImageBlock subtype**

Create: `backend/apps/reports/models/blocks/text_image.py`

```python
"""TextImageBlock: bloque narrativo con imagen opcional."""
from django.db import models

from apps.reports.validators import validate_image_mimetype, validate_image_size

from .base_block import ReportBlock


IMAGE_POSITIONS = [
    ("left", "Izquierda"),
    ("right", "Derecha"),
    ("top", "Arriba"),
]

COLUMNS_CHOICES = [(1, "1 columna"), (2, "2 columnas"), (3, "3 columnas")]


class TextImageBlock(ReportBlock):
    title = models.CharField(max_length=200, blank=True)
    body = models.TextField(blank=True)
    columns = models.PositiveSmallIntegerField(
        choices=COLUMNS_CHOICES, default=1,
    )
    image_position = models.CharField(
        max_length=10, choices=IMAGE_POSITIONS, default="top",
    )
    image_alt = models.CharField(max_length=300, blank=True)
    image = models.ImageField(
        upload_to="report_blocks/%Y/%m/",
        blank=True, null=True,
        validators=[validate_image_size, validate_image_mimetype],
    )

    class Meta:
        verbose_name = "Text + Image Block"
        verbose_name_plural = "Text + Image Blocks"
```

- [ ] **Step 5: Run tests to verify they still fail (migration not yet applied)**

```bash
docker compose exec -T backend pytest backend/tests/unit/blocks/test_report_block_base.py -v
```
Expected: FAIL con errores de DB (tablas nuevas no existen).

- [ ] **Step 6: Generate migration 0009**

```bash
docker compose exec -T backend python manage.py makemigrations reports --name typed_blocks
```
Expected: output como `Migrations for 'reports': reports/migrations/0009_typed_blocks.py` con las operaciones:
- `AddField ReportBlock.instructions`
- `AddField ReportBlock.polymorphic_ctype` (lo agrega django-polymorphic automáticamente)
- `CreateModel TextImageBlock`

- [ ] **Step 7: Inspect generated migration**

```bash
cat backend/apps/reports/migrations/0009_typed_blocks.py
```

Review manual: verificar que NO hay operaciones inesperadas (p. ej. drops de campos que todavía queremos preservar). Todavía NO borramos `ReportBlock.config/type/image` porque el models.py viejo los sigue declarando (via models_legacy.py re-export). Esos drops van en Task 2.5.

- [ ] **Step 8: Apply migration**

```bash
docker compose exec -T backend python manage.py migrate
```
Expected: `Applying reports.0009_typed_blocks... OK`.

- [ ] **Step 9a: Add observability logging to migration 0009 (dim 10)**

Editar `backend/apps/reports/migrations/0009_typed_blocks.py` — al final de la migración, agregar un `RunPython` no-destructivo que emita un log estructurado para que el deploy log en Hetzner tenga señal:

```python
from django.db import migrations


def _log_migration_applied(apps, schema_editor):
    import logging
    logger = logging.getLogger("reports.migrations")
    ReportBlock = apps.get_model("reports", "ReportBlock")
    logger.info(
        "typed_blocks_scaffold_applied",
        extra={"existing_blocks": ReportBlock.objects.count()},
    )


def _noop_reverse(apps, schema_editor):
    pass  # rollback doesn't need the log


class Migration(migrations.Migration):
    # ... dependencies, operations generadas automáticamente arriba ...

    operations = [
        # ... operations auto-generadas ...
        migrations.RunPython(_log_migration_applied, _noop_reverse),
    ]
```

Agregar el RunPython al final de `operations`. *(P8 Evidence Over Assumptions — el deploy log queda como evidencia de que la migración corrió.)*

- [ ] **Step 9: Run tests**

```bash
docker compose exec -T backend pytest backend/tests/unit/blocks/test_report_block_base.py -v
```
Expected: 3/5 pasan (los de estructura sí; los de `old_fields_gone` TODAVÍA fallan porque `config/type/image` siguen en el modelo via legacy).

Temporalmente skippear los que fallan:

```python
# En test_report_block_base.py, marcar con:
@pytest.mark.skip(reason="Old fields removal happens in Task 2.5")
def test_report_block_old_fields_gone():
    ...
```

Re-correr: expected 5 passed (1 skipped).

- [ ] **Step 10: Commit**

```bash
git add backend/apps/reports/models/ backend/apps/reports/models_legacy.py backend/apps/reports/tests/ backend/tests/unit/blocks/ backend/tests/conftest.py backend/apps/reports/migrations/0009_typed_blocks.py
git commit -m "feat(reports): scaffold ReportBlock polymorphic base + TextImageBlock

- ReportBlock now inherits from PolymorphicModel (django-polymorphic).
- Base fields: report FK, order (unique per report), instructions (free-text
  AI/operator hints), timestamps.
- TextImageBlock is the first typed subtype, feature-parity with the
  TEXT_IMAGE config JSON (columns, image_position, image_alt, image).
- Legacy models.py content moved to models_legacy.py; package re-exports
  via models/__init__.py.
- Migration 0009 adds new tables; old ReportBlock.config/type/image not
  yet dropped (that's Phase 2.5)."
```

### Task 2.4: Implement remaining 5 subtypes + 3 child tables

Siguiendo el mismo pattern de Task 2.3 (test fail → implement → migration → test pass), crear:

Para cada uno: (a) test file, (b) model module, (c) update models/__init__.py, (d) new migration.

- [ ] **Step 1: KpiGridBlock + KpiTile**

Create test: `backend/tests/unit/blocks/test_kpi_grid_block.py`

```python
import pytest


@pytest.mark.django_db
def test_kpi_grid_block_creates_with_tiles(report_factory):
    from apps.reports.models import KpiGridBlock, KpiTile
    report = report_factory()
    block = KpiGridBlock.objects.create(report=report, order=1, title="KPIs")
    KpiTile.objects.create(kpi_grid_block=block, label="Reach", value=1000, order=1)
    KpiTile.objects.create(
        kpi_grid_block=block, label="ER", value=4.5,
        period_comparison=0.3, order=2,
    )
    assert block.tiles.count() == 2
    assert block.tiles.first().label == "Reach"


@pytest.mark.django_db
def test_kpi_tile_unique_order_per_grid(report_factory):
    from django.db import IntegrityError
    from apps.reports.models import KpiGridBlock, KpiTile
    report = report_factory()
    block = KpiGridBlock.objects.create(report=report, order=1)
    KpiTile.objects.create(kpi_grid_block=block, label="A", value=1, order=1)
    with pytest.raises(IntegrityError):
        KpiTile.objects.create(kpi_grid_block=block, label="B", value=2, order=1)


@pytest.mark.django_db
def test_kpi_tile_cascade_on_block_delete(report_factory):
    from apps.reports.models import KpiGridBlock, KpiTile
    report = report_factory()
    block = KpiGridBlock.objects.create(report=report, order=1)
    KpiTile.objects.create(kpi_grid_block=block, label="A", value=1, order=1)
    block.delete()
    assert KpiTile.objects.count() == 0
```

Run: `docker compose exec -T backend pytest backend/tests/unit/blocks/test_kpi_grid_block.py -v` → expected FAIL.

Create: `backend/apps/reports/models/blocks/kpi_grid.py`

```python
"""KpiGridBlock + KpiTile — grid de tiles con label + valor."""
from django.db import models

from .base_block import ReportBlock


class KpiGridBlock(ReportBlock):
    title = models.CharField(max_length=200, blank=True)

    class Meta:
        verbose_name = "KPI Grid Block"
        verbose_name_plural = "KPI Grid Blocks"


class KpiTile(models.Model):
    kpi_grid_block = models.ForeignKey(
        KpiGridBlock, on_delete=models.CASCADE, related_name="tiles",
    )
    label = models.CharField(max_length=120)
    value = models.DecimalField(max_digits=16, decimal_places=4)
    period_comparison = models.DecimalField(
        max_digits=8, decimal_places=4, null=True, blank=True,
        help_text="Delta % vs periodo anterior. Opcional.",
    )
    order = models.PositiveIntegerField()

    class Meta:
        ordering = ["kpi_grid_block", "order"]
        constraints = [
            models.UniqueConstraint(
                fields=["kpi_grid_block", "order"],
                name="uniq_tile_order_per_kpi_grid",
            ),
        ]
```

Update `backend/apps/reports/models/__init__.py` — agregar:
```python
from .blocks.kpi_grid import KpiGridBlock, KpiTile  # noqa: F401
```

Migrate + re-run tests. Expected: 3 passed.

- [ ] **Step 2: MetricsTableBlock + MetricsTableRow**

Create test: `backend/tests/unit/blocks/test_metrics_table_block.py`

```python
import pytest


@pytest.mark.django_db
def test_metrics_table_accepts_valid_network(report_factory):
    from apps.reports.models import MetricsTableBlock
    from apps.reports.choices import Network
    report = report_factory()
    block = MetricsTableBlock.objects.create(
        report=report, order=1, network=Network.INSTAGRAM, title="IG",
    )
    assert block.network == "INSTAGRAM"


@pytest.mark.django_db
def test_metrics_table_allows_null_network(report_factory):
    from apps.reports.models import MetricsTableBlock
    report = report_factory()
    block = MetricsTableBlock.objects.create(
        report=report, order=1, title="Mes a mes",
    )
    assert block.network is None


@pytest.mark.django_db
def test_metrics_table_row_fields(report_factory):
    from apps.reports.models import MetricsTableBlock, MetricsTableRow
    from apps.reports.choices import Network, SourceType
    report = report_factory()
    block = MetricsTableBlock.objects.create(
        report=report, order=1, network=Network.INSTAGRAM,
    )
    row = MetricsTableRow.objects.create(
        metrics_table_block=block,
        metric_name="reach",
        value=500_000,
        source_type=SourceType.ORGANIC,
        period_comparison=5.2,
        order=1,
    )
    assert row.metric_name == "reach"
    assert block.rows.count() == 1


@pytest.mark.django_db
def test_metrics_table_row_source_type_nullable(report_factory):
    from apps.reports.models import MetricsTableBlock, MetricsTableRow
    report = report_factory()
    block = MetricsTableBlock.objects.create(report=report, order=1)
    row = MetricsTableRow.objects.create(
        metrics_table_block=block,
        metric_name="total_reach",
        value=1_000_000,
        order=1,
    )
    assert row.source_type is None
    assert row.period_comparison is None
```

Run: expected FAIL.

Create: `backend/apps/reports/models/blocks/metrics_table.py`

```python
"""MetricsTableBlock + MetricsTableRow — tabla de métricas (snapshot)."""
from django.db import models

from apps.reports.choices import Network, SourceType

from .base_block import ReportBlock


class MetricsTableBlock(ReportBlock):
    title = models.CharField(max_length=200, blank=True)
    network = models.CharField(
        max_length=16, choices=Network.choices,
        null=True, blank=True,
        help_text=(
            "Metadata hint: red de social para la cual se arma la tabla. "
            "Null = cross-network (ej. 'Mes a mes'). Consumida por el "
            "fetcher AI de Metricool para saber qué data traer."
        ),
    )

    class Meta:
        verbose_name = "Metrics Table Block"
        verbose_name_plural = "Metrics Table Blocks"


class MetricsTableRow(models.Model):
    metrics_table_block = models.ForeignKey(
        MetricsTableBlock, on_delete=models.CASCADE, related_name="rows",
    )
    metric_name = models.CharField(max_length=100)
    value = models.DecimalField(max_digits=16, decimal_places=4)
    source_type = models.CharField(
        max_length=16, choices=SourceType.choices,
        null=True, blank=True,
    )
    period_comparison = models.DecimalField(
        max_digits=8, decimal_places=4, null=True, blank=True,
    )
    order = models.PositiveIntegerField()

    class Meta:
        ordering = ["metrics_table_block", "order"]
        constraints = [
            models.UniqueConstraint(
                fields=["metrics_table_block", "order"],
                name="uniq_row_order_per_metrics_table",
            ),
        ]
```

Update `models/__init__.py` con los nuevos imports. Migrate. Tests → expected pass.

- [ ] **Step 3: TopContentBlock**

Create test: `backend/tests/unit/blocks/test_top_content_block.py`

```python
import pytest


@pytest.mark.django_db
def test_top_content_block_requires_kind(report_factory):
    from django.core.exceptions import ValidationError
    from apps.reports.models import TopContentBlock
    report = report_factory()
    block = TopContentBlock(report=report, order=1)  # kind missing
    with pytest.raises(ValidationError):
        block.full_clean()


@pytest.mark.django_db
def test_top_content_block_kind_choices(report_factory):
    from apps.reports.models import TopContentBlock
    report = report_factory()
    block = TopContentBlock.objects.create(report=report, order=1, kind="POST")
    assert block.kind == "POST"


@pytest.mark.django_db
def test_top_content_block_limit_default_and_validation(report_factory):
    from django.core.exceptions import ValidationError
    from apps.reports.models import TopContentBlock
    report = report_factory()
    block = TopContentBlock.objects.create(report=report, order=1, kind="CREATOR")
    assert block.limit == 6
    block.limit = 100
    with pytest.raises(ValidationError):
        block.full_clean()
```

Run: expected FAIL.

Create: `backend/apps/reports/models/blocks/top_content.py`

```python
"""TopContentBlock — lista de top posts o creators destacados."""
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from .base_block import ReportBlock


TOP_CONTENT_KINDS = [("POST", "Post destacado"), ("CREATOR", "Creator destacado")]


class TopContentBlock(ReportBlock):
    title = models.CharField(max_length=200, blank=True)
    kind = models.CharField(max_length=16, choices=TOP_CONTENT_KINDS)
    limit = models.PositiveSmallIntegerField(
        default=6,
        validators=[MinValueValidator(1), MaxValueValidator(20)],
    )

    class Meta:
        verbose_name = "Top Content Block"
        verbose_name_plural = "Top Content Blocks"
```

Update `models/__init__.py`. Migrate. Tests → expected pass.

- [ ] **Step 4: AttributionTableBlock**

Create test: `backend/tests/unit/blocks/test_attribution_table_block.py`

```python
import pytest


@pytest.mark.django_db
def test_attribution_table_block_show_total_default_true(report_factory):
    from apps.reports.models import AttributionTableBlock
    report = report_factory()
    block = AttributionTableBlock.objects.create(report=report, order=1)
    assert block.show_total is True


@pytest.mark.django_db
def test_attribution_table_block_show_total_toggleable(report_factory):
    from apps.reports.models import AttributionTableBlock
    report = report_factory()
    block = AttributionTableBlock.objects.create(
        report=report, order=1, show_total=False,
    )
    assert block.show_total is False
```

Run: expected FAIL.

Create: `backend/apps/reports/models/blocks/attribution.py`

```python
"""AttributionTableBlock — tabla de OneLink attributions."""
from django.db import models

from .base_block import ReportBlock


class AttributionTableBlock(ReportBlock):
    title = models.CharField(max_length=200, blank=True)
    show_total = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Attribution Table Block"
        verbose_name_plural = "Attribution Table Blocks"
```

Update `models/__init__.py`. Migrate. Tests → expected pass.

- [ ] **Step 5: ChartBlock + ChartDataPoint**

Create test: `backend/tests/unit/blocks/test_chart_block.py`

```python
import pytest


@pytest.mark.django_db
def test_chart_block_defaults(report_factory):
    from apps.reports.models import ChartBlock
    report = report_factory()
    block = ChartBlock.objects.create(report=report, order=1, title="Followers IG")
    assert block.chart_type == "bar"
    assert block.network is None


@pytest.mark.django_db
def test_chart_block_with_data_points(report_factory):
    from apps.reports.models import ChartBlock, ChartDataPoint
    from apps.reports.choices import Network
    report = report_factory()
    block = ChartBlock.objects.create(
        report=report, order=1, network=Network.INSTAGRAM,
    )
    ChartDataPoint.objects.create(chart_block=block, label="Ene", value=100, order=1)
    ChartDataPoint.objects.create(chart_block=block, label="Feb", value=150, order=2)
    ChartDataPoint.objects.create(chart_block=block, label="Mar", value=180, order=3)
    assert block.data_points.count() == 3
    assert list(block.data_points.values_list("label", flat=True)) == ["Ene", "Feb", "Mar"]


@pytest.mark.django_db
def test_chart_block_rejects_unknown_chart_type(report_factory):
    from django.core.exceptions import ValidationError
    from apps.reports.models import ChartBlock
    report = report_factory()
    block = ChartBlock(report=report, order=1, chart_type="pie")  # no soportado
    with pytest.raises(ValidationError):
        block.full_clean()
```

Run: expected FAIL.

Create: `backend/apps/reports/models/blocks/chart.py`

```python
"""ChartBlock + ChartDataPoint — gráfico snapshot con sus puntos."""
from django.db import models

from apps.reports.choices import Network

from .base_block import ReportBlock


CHART_TYPES = [("bar", "Bar")]  # extensible a future (line, area, etc.)


class ChartBlock(ReportBlock):
    title = models.CharField(max_length=200, blank=True)
    network = models.CharField(
        max_length=16, choices=Network.choices,
        null=True, blank=True,
        help_text="Metadata hint: red social que el chart representa.",
    )
    chart_type = models.CharField(
        max_length=16, choices=CHART_TYPES, default="bar",
    )

    class Meta:
        verbose_name = "Chart Block"
        verbose_name_plural = "Chart Blocks"


class ChartDataPoint(models.Model):
    chart_block = models.ForeignKey(
        ChartBlock, on_delete=models.CASCADE, related_name="data_points",
    )
    label = models.CharField(max_length=60)
    value = models.DecimalField(max_digits=16, decimal_places=4)
    order = models.PositiveIntegerField()

    class Meta:
        ordering = ["chart_block", "order"]
        constraints = [
            models.UniqueConstraint(
                fields=["chart_block", "order"],
                name="uniq_point_order_per_chart",
            ),
        ]
```

Update `models/__init__.py`. Migrate. Tests → expected pass.

- [ ] **Step 6: Run ALL new subtype tests**

```bash
docker compose exec -T backend pytest backend/tests/unit/blocks/ -v
```
Expected: todos pasan (5 files, ~15 tests).

- [ ] **Step 7: Commit**

```bash
git add backend/apps/reports/models/ backend/apps/reports/migrations/ backend/tests/unit/blocks/
git commit -m "feat(reports): add 5 typed block subtypes (KpiGrid, MetricsTable, TopContent, Attribution, Chart)

- KpiGridBlock + KpiTile child table.
- MetricsTableBlock + MetricsTableRow child table.
- TopContentBlock (items FK se actualiza en Phase 2.5).
- AttributionTableBlock (entries FK se actualiza en Phase 2.5).
- ChartBlock + ChartDataPoint child table.
- Unit tests por subtype: creation, constraints, cascades.
- Each file <150 lines (complexity budget P2 / spec dim 4)."
```

### Task 2.5: Migrate FK targets + drop legacy fields/models

**Files:**
- Modify: `backend/apps/reports/models_legacy.py` (eliminar `ReportMetric`, `ReportBlock.type/config/image`)
- Modify: `backend/apps/reports/models/__init__.py` (remove legacy re-exports que ya no existen)
- Modify: `backend/apps/reports/models_legacy.py` — `OneLinkAttribution.report` FK → `attribution_block` FK hacia `AttributionTableBlock`
- Modify: `backend/apps/reports/models_legacy.py` — `TopContent.block` FK target de `ReportBlock` a `TopContentBlock`
- Create: migration 0010 para estos cambios

- [ ] **Step 1: Un-skip test_report_block_old_fields_gone**

En `backend/tests/unit/blocks/test_report_block_base.py`, quitar el `@pytest.mark.skip` del test `test_report_block_old_fields_gone`.

Run: expected FAIL (campos todavía ahí).

- [ ] **Step 2: Write test for TopContent FK migration**

Modify: `backend/tests/unit/test_topcontent_block_fk.py` (existente, adaptar):

```python
"""Tests para verificar el FK de TopContent post-DEV-116."""
import pytest


@pytest.mark.django_db
def test_top_content_block_fk_is_top_content_block(report_factory):
    from apps.reports.models import TopContent, TopContentBlock
    report = report_factory()
    block = TopContentBlock.objects.create(report=report, order=1, kind="POST")
    # El FK target es TopContentBlock, no ReportBlock genérico.
    tc = TopContent.objects.create(
        block=block, kind="POST", network="INSTAGRAM",
        source_type="ORGANIC", rank=1,
    )
    assert tc.block_id == block.id
    assert isinstance(tc.block, TopContentBlock)


@pytest.mark.django_db
def test_top_content_report_fk_removed(report_factory):
    """El FK `report` de TopContent se eliminó — es derivable via block.report."""
    from apps.reports.models import TopContent
    fields = {f.name for f in TopContent._meta.get_fields()}
    assert "report" not in fields
```

Run: expected FAIL (FK todavía apunta al base y `report` FK todavía existe).

- [ ] **Step 3: Write test for OneLinkAttribution FK migration**

Create: `backend/tests/unit/test_onelink_attribution_block_fk.py`

```python
"""OneLinkAttribution FK ahora apunta a AttributionTableBlock."""
import pytest


@pytest.mark.django_db
def test_onelink_fk_is_attribution_block(report_factory):
    from apps.reports.models import OneLinkAttribution, AttributionTableBlock
    report = report_factory()
    block = AttributionTableBlock.objects.create(report=report, order=1)
    entry = OneLinkAttribution.objects.create(
        attribution_block=block,
        influencer_handle="@test",
        clicks=100, app_downloads=10,
    )
    assert entry.attribution_block_id == block.id


@pytest.mark.django_db
def test_onelink_report_fk_removed():
    from apps.reports.models import OneLinkAttribution
    fields = {f.name for f in OneLinkAttribution._meta.get_fields()}
    assert "report" not in fields
```

Run: expected FAIL.

- [ ] **Step 4: Write test for ReportMetric removal**

Create: `backend/tests/unit/blocks/test_legacy_models_gone.py`

```python
"""Los modelos legacy que el spec elimina no deberían ser importables."""
import pytest


def test_report_metric_gone():
    with pytest.raises(ImportError):
        from apps.reports.models import ReportMetric  # noqa: F401


def test_aggregations_gone():
    """build_yoy / build_q1_rollup / build_follower_snapshots se eliminan."""
    # Importlib porque pytest reporta pytest.ImportError distinto.
    import importlib
    with pytest.raises((ImportError, AttributeError)):
        mod = importlib.import_module("apps.reports.services.aggregations")
        mod.build_yoy  # no debería existir
```

Run: expected FAIL.

- [ ] **Step 5: Modify models_legacy.py — delete ReportMetric, drop ReportBlock fields, migrate FKs**

Modify `backend/apps/reports/models_legacy.py`:

1. Eliminar la clase completa `ReportMetric`.
2. En `ReportBlock` (la clase legacy si todavía existe allá — después del scaffold MTI, `ReportBlock` vive en `models/blocks/base_block.py`, así que `models_legacy.py` ya no debería declararlo. Si lo declara, eliminar esa definición).
3. En `TopContent`:
   - Eliminar el FK `report`.
   - Cambiar `block = ForeignKey("ReportBlock", ...)` a `block = ForeignKey("TopContentBlock", ...)`.
   - Ajustar el `save()` override si referencia `self.block.report_id`.
4. En `OneLinkAttribution`:
   - Eliminar el FK `report`.
   - Agregar `attribution_block = ForeignKey(AttributionTableBlock, on_delete=CASCADE, related_name="entries")`.

> **Importante**: el archivo se va a renombrar a `models/legacy_support.py` más adelante (Task 2.6). Por ahora, seguir editando `models_legacy.py`.

- [ ] **Step 6: Update models/__init__.py**

Remove `ReportMetric` from the re-exports list.

- [ ] **Step 7: Generate migration 0010**

```bash
docker compose exec -T backend python manage.py makemigrations reports --name drop_legacy_blocks
```
Expected operations:
- DeleteModel `ReportMetric`
- RemoveField `ReportBlock.type`, `ReportBlock.config`, `ReportBlock.image`
- RemoveField `TopContent.report`
- AlterField `TopContent.block` (target change)
- RemoveField `OneLinkAttribution.report`
- AddField `OneLinkAttribution.attribution_block`

- [ ] **Step 8: Inspect migration**

```bash
cat backend/apps/reports/migrations/0010_drop_legacy_blocks.py
```

Verificar que no hay operaciones no esperadas. Si aparece un `AlterField` que no queremos (por ejemplo Django sugiere preservar data vía `RunPython`), confirmar que es segura la variante destructiva (nada en prod).

- [ ] **Step 8b: Add observability logging to migration 0010 (dim 10)**

Igual que en Task 2.3 Step 9a, agregar al final de `0010_drop_legacy_blocks.py`:

```python
def _log_destructive_migration(apps, schema_editor):
    import logging
    logger = logging.getLogger("reports.migrations")
    logger.warning(
        "typed_blocks_destructive_migration_applied",
        extra={
            "dropped": ["ReportMetric", "ReportBlock.config", "ReportBlock.type",
                        "ReportBlock.image", "TopContent.report", "OneLinkAttribution.report"],
            "note": "no prod data at time of migration",
        },
    )


def _warn_rollback_unsafe(apps, schema_editor):
    """Rollback is not safe — destructive migration cannot restore deleted data."""
    raise RuntimeError(
        "Migration 0010 is destructive and cannot be reversed automatically. "
        "Restore from backup or re-run seed_demo."
    )


class Migration(migrations.Migration):
    # ... operations ...
    operations = [
        # ... auto-generated drop operations ...
        migrations.RunPython(_log_destructive_migration, _warn_rollback_unsafe),
    ]
```

*(P9 Fail Fast — rollback explícito con RuntimeError en vez de silencioso.)*

- [ ] **Step 9: Apply migration**

```bash
docker compose exec -T backend python manage.py migrate
```

Si la migración pide confirmación (ej. por data en TopContent huérfana), aceptar — nada está en prod.

- [ ] **Step 10: Run full blocks test suite**

```bash
docker compose exec -T backend pytest backend/tests/unit/blocks/ backend/tests/unit/test_topcontent_block_fk.py backend/tests/unit/test_onelink_attribution_block_fk.py -v
```
Expected: todos pasan.

- [ ] **Step 11: Run full backend suite (espera fails en tests que dependían de ReportMetric/config/aggregations)**

```bash
docker compose exec -T backend pytest backend/tests/unit/ -q 2>&1 | tail -30
```

Expected fails (se resuelven en Phase 3 al eliminar los archivos y tests obsoletos):
- `test_block_config_validation.py`
- `test_report_aggregations.py`
- `test_report_block_config.py`
- `test_report_detail_serializer.py` (depende del payload viejo)
- `test_report_nplus1.py`
- `test_report_serializer_blocks.py`
- `test_report_viewer_models.py`
- `test_seed_demo_blocks.py`
- `test_seed_demo_report_viewer.py`

- [ ] **Step 12: Commit**

```bash
git add backend/apps/reports/models_legacy.py backend/apps/reports/models/ backend/apps/reports/migrations/0010_drop_legacy_blocks.py backend/tests/unit/blocks/ backend/tests/unit/test_topcontent_block_fk.py backend/tests/unit/test_onelink_attribution_block_fk.py
git commit -m "refactor(reports): drop ReportMetric + legacy ReportBlock fields

- DELETE table ReportMetric (destructive migration 0010).
- DROP ReportBlock.type, config, image (replaced by MTI subtypes).
- MOVE TopContent.block FK from ReportBlock → TopContentBlock specifically.
- MOVE OneLinkAttribution FK from report → attribution_block (AttributionTableBlock).
- Still failing: tests for aggregations/registry/schemas — removed in Phase 3.

No prod data at time of merge; destructive migration is safe."
```

### Task 2.6: Reorganize models files into clean structure

Consolidar `models_legacy.py` en `models/` + eliminar el archivo temporal.

**Files:**
- Split `backend/apps/reports/models_legacy.py` into individual files under `backend/apps/reports/models/`.
- Delete `backend/apps/reports/models_legacy.py`.

- [ ] **Step 1: Create models/report.py**

Move `Report` class + `Meta`, `display_title`, `__str__` there. Keep imports minimal.

- [ ] **Step 2: Create models/top_content.py**

Move the `TopContent` model (with updated `block` FK → `TopContentBlock`) there. Keep the `save()` override.

- [ ] **Step 3: Create models/onelink_attribution.py**

Move `OneLinkAttribution` there.

- [ ] **Step 4: Create models/brand_follower_snapshot.py**

Move `BrandFollowerSnapshot` there.

- [ ] **Step 5: Update models/__init__.py**

```python
"""Reports domain models — package post-DEV-116."""
from .report import Report  # noqa: F401
from .top_content import TopContent  # noqa: F401
from .onelink_attribution import OneLinkAttribution  # noqa: F401
from .brand_follower_snapshot import BrandFollowerSnapshot  # noqa: F401

from .blocks.base_block import ReportBlock  # noqa: F401
from .blocks.text_image import TextImageBlock  # noqa: F401
from .blocks.kpi_grid import KpiGridBlock, KpiTile  # noqa: F401
from .blocks.metrics_table import MetricsTableBlock, MetricsTableRow  # noqa: F401
from .blocks.top_content import TopContentBlock  # noqa: F401
from .blocks.attribution import AttributionTableBlock  # noqa: F401
from .blocks.chart import ChartBlock, ChartDataPoint  # noqa: F401
```

- [ ] **Step 6: Delete models_legacy.py**

```bash
rm backend/apps/reports/models_legacy.py
```

- [ ] **Step 7: Verify each model file is <200 lines**

```bash
wc -l backend/apps/reports/models/*.py backend/apps/reports/models/blocks/*.py
```

All files should be <200 lines. If any file exceeds, split it.

- [ ] **Step 8: Run backend suite to verify no regression from the split**

```bash
docker compose exec -T backend pytest backend/tests/unit/ -q 2>&1 | tail -10
```
Expected: same failures as before Task 2.6 (registry/aggregations tests still failing). No NEW failures from the reorg.

- [ ] **Step 9: Commit**

```bash
git add backend/apps/reports/models/
git rm backend/apps/reports/models_legacy.py
git commit -m "refactor(reports): split models into per-concern modules

- models/__init__.py re-exports all models (public API unchanged).
- models/report.py, top_content.py, onelink_attribution.py,
  brand_follower_snapshot.py — one concern per file.
- models/blocks/ — one file per subtype + child tables.
- All files now <200 lines (spec dim 4 complexity budget)."
```

---

## Phase 3 — Admin polimórfica

**Goal:** `django-polymorphic` admin con un inline único en `ReportAdmin`, dropdown de subtypes, campos dinámicos.

### Task 3.1: Write admin smoke test

**Files:**
- Create: `backend/tests/unit/blocks/test_admin_polymorphic.py`

- [ ] **Step 1: Write test**

```python
"""Smoke del admin polimórfico — que un superuser pueda crear cada
subtipo de block desde el admin."""
import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse

User = get_user_model()


@pytest.fixture
def admin_client(client, db):
    admin = User.objects.create_superuser(
        email="admin@test.com", password="adminpass",
    )
    client.force_login(admin)
    return client


@pytest.mark.django_db
def test_admin_can_load_report_change_page(admin_client, report_factory):
    report = report_factory()
    url = reverse("admin:reports_report_change", args=[report.id])
    response = admin_client.get(url)
    assert response.status_code == 200


@pytest.mark.django_db
def test_admin_shows_polymorphic_add_block_dropdown(admin_client, report_factory):
    """En el change page del Report, debería aparecer un dropdown
    para agregar blocks con los 6 subtypes."""
    report = report_factory()
    url = reverse("admin:reports_report_change", args=[report.id])
    response = admin_client.get(url)
    html = response.content.decode()
    for subtype_verbose in [
        "Text + Image Block", "KPI Grid Block", "Metrics Table Block",
        "Top Content Block", "Attribution Table Block", "Chart Block",
    ]:
        assert subtype_verbose in html, f"Missing subtype in admin: {subtype_verbose}"


@pytest.mark.django_db
def test_admin_can_create_kpi_grid_block(admin_client, report_factory):
    """POST al admin crea un KpiGridBlock persistido."""
    from apps.reports.models import KpiGridBlock
    report = report_factory()
    # Este test exacto depende del shape del form polimórfico —
    # acá verificamos el path indirectamente con una creación directa
    # (el smoke HTML arriba ya cubre que el UI está).
    block = KpiGridBlock.objects.create(report=report, order=1, title="Test")
    assert block.instructions == ""  # campo heredado de la base
    assert KpiGridBlock.objects.filter(report=report).count() == 1
```

- [ ] **Step 2: Run to verify it fails**

```bash
docker compose exec -T backend pytest backend/tests/unit/blocks/test_admin_polymorphic.py -v
```
Expected: FAIL en `test_admin_shows_polymorphic_add_block_dropdown` — el admin actual no muestra el dropdown polimórfico.

### Task 3.2: Rewrite admin.py

**Files:**
- Modify: `backend/apps/reports/admin.py`

- [ ] **Step 1: Design target admin structure**

Usar `PolymorphicInlineSupportMixin` + `StackedPolymorphicInline` de `django-polymorphic`:

```python
from polymorphic.admin import (
    PolymorphicInlineSupportMixin,
    StackedPolymorphicInline,
)

class ReportBlockInline(StackedPolymorphicInline):
    class TextImageBlockInline(StackedPolymorphicInline.Child):
        model = TextImageBlock
    # ... 5 child clases más
    model = ReportBlock
    child_inlines = [TextImageBlockInline, KpiGridBlockInline, ...]


class ReportAdmin(PolymorphicInlineSupportMixin, admin.ModelAdmin):
    inlines = [ReportMetricInline,  # si todavía existe … eliminar
               ReportBlockInline]
```

- [ ] **Step 2: Rewrite admin.py**

Rewrite `backend/apps/reports/admin.py` con los 6 subtipos como Child inlines. Para cada subtipo con child rows (tiles, metric rows, etc.), agregar un TabularInline del child.

Ejemplo esquemático (adaptar al patrón exacto de `django-polymorphic`):

```python
from django.contrib import admin
from polymorphic.admin import (
    PolymorphicInlineSupportMixin,
    StackedPolymorphicInline,
    PolymorphicParentModelAdmin,
    PolymorphicChildModelAdmin,
)

from .models import (
    Report, ReportBlock,
    TextImageBlock, KpiGridBlock, KpiTile,
    MetricsTableBlock, MetricsTableRow,
    TopContentBlock, AttributionTableBlock, ChartBlock, ChartDataPoint,
    TopContent, OneLinkAttribution, BrandFollowerSnapshot,
)


class KpiTileInline(admin.TabularInline):
    model = KpiTile
    extra = 0


class MetricsTableRowInline(admin.TabularInline):
    model = MetricsTableRow
    extra = 0


class ChartDataPointInline(admin.TabularInline):
    model = ChartDataPoint
    extra = 0


class TopContentInline(admin.TabularInline):
    model = TopContent
    extra = 0
    fields = ("kind", "network", "source_type", "rank", "handle", "thumbnail")


class OneLinkAttributionInline(admin.TabularInline):
    model = OneLinkAttribution
    extra = 0


# -- Polymorphic inline for ReportBlock inside ReportAdmin --

class ReportBlockInline(StackedPolymorphicInline):
    class TextImageBlockInline(StackedPolymorphicInline.Child):
        model = TextImageBlock

    class KpiGridBlockInline(StackedPolymorphicInline.Child):
        model = KpiGridBlock

    class MetricsTableBlockInline(StackedPolymorphicInline.Child):
        model = MetricsTableBlock

    class TopContentBlockInline(StackedPolymorphicInline.Child):
        model = TopContentBlock

    class AttributionTableBlockInline(StackedPolymorphicInline.Child):
        model = AttributionTableBlock

    class ChartBlockInline(StackedPolymorphicInline.Child):
        model = ChartBlock

    model = ReportBlock
    child_inlines = [
        TextImageBlockInline, KpiGridBlockInline, MetricsTableBlockInline,
        TopContentBlockInline, AttributionTableBlockInline, ChartBlockInline,
    ]


@admin.register(Report)
class ReportAdmin(PolymorphicInlineSupportMixin, admin.ModelAdmin):
    list_display = ("display_title", "stage", "kind", "period_start", "status")
    list_filter = ("status", "kind", "stage__campaign__brand")
    search_fields = ("title",)
    inlines = [ReportBlockInline]
    fieldsets = (
        (None, {"fields": (
            "stage", "kind", "period_start", "period_end",
            "title", "status", "published_at",
            "intro_text", "conclusions_text", "original_pdf",
        )}),
    )


# -- Polymorphic parent/child admins for standalone ReportBlock browsing --

@admin.register(ReportBlock)
class ReportBlockAdmin(PolymorphicParentModelAdmin):
    child_models = (
        TextImageBlock, KpiGridBlock, MetricsTableBlock,
        TopContentBlock, AttributionTableBlock, ChartBlock,
    )
    list_display = ("report", "order", "polymorphic_ctype")
    list_filter = ("polymorphic_ctype",)


class _BlockChildAdminBase(PolymorphicChildModelAdmin):
    base_model = ReportBlock
    # fields specific to each subtype are declared per-child below via
    # Django's default introspection.


@admin.register(TextImageBlock)
class TextImageBlockAdmin(_BlockChildAdminBase):
    pass


@admin.register(KpiGridBlock)
class KpiGridBlockAdmin(_BlockChildAdminBase):
    inlines = [KpiTileInline]


@admin.register(MetricsTableBlock)
class MetricsTableBlockAdmin(_BlockChildAdminBase):
    inlines = [MetricsTableRowInline]


@admin.register(TopContentBlock)
class TopContentBlockAdmin(_BlockChildAdminBase):
    inlines = [TopContentInline]


@admin.register(AttributionTableBlock)
class AttributionTableBlockAdmin(_BlockChildAdminBase):
    inlines = [OneLinkAttributionInline]


@admin.register(ChartBlock)
class ChartBlockAdmin(_BlockChildAdminBase):
    inlines = [ChartDataPointInline]


# -- Standalone admins for child rows (debugging only) --

@admin.register(TopContent)
class TopContentAdmin(admin.ModelAdmin):
    list_display = ("block", "kind", "network", "rank", "handle")
    search_fields = ("handle",)


@admin.register(BrandFollowerSnapshot)
class BrandFollowerSnapshotAdmin(admin.ModelAdmin):
    list_display = ("brand", "network", "as_of", "followers_count")
    list_filter = ("brand", "network")


# ReportMetric admin (ya no existe) y ReportMetricInline se eliminan.
```

- [ ] **Step 3: Run admin tests**

```bash
docker compose exec -T backend pytest backend/tests/unit/blocks/test_admin_polymorphic.py -v
```
Expected: todos pasan.

- [ ] **Step 4: Manual smoke test (si hay tiempo)**

```bash
docker compose exec -T backend python manage.py createsuperuser --email admin@test.com
# (ingresar password interactivo)
```

Abrir `http://localhost:8000/admin/reports/report/` en el browser, click en un Report, verificar:
- Aparece sección "Report Blocks" con los existentes (vacío o post-seed).
- Click "Add another Report Block" → dropdown con los 6 subtypes.
- Click un subtype → form con sus campos + inline de children aparece.

- [ ] **Step 5: Commit**

```bash
git add backend/apps/reports/admin.py backend/tests/unit/blocks/test_admin_polymorphic.py
git commit -m "feat(reports-admin): polymorphic inline with per-subtype forms

- Single ReportBlockInline dispatches to 6 StackedPolymorphicInline.Child
  sub-inlines.
- Each subtype has its own ModelAdmin with nested inlines for child rows
  (KpiTile, MetricsTableRow, ChartDataPoint, TopContent, OneLinkAttribution).
- Drag-to-reorder via PolymorphicParentModelAdmin.
- UX: operator opens Report → Add block → picks subtype → typed form
  appears. No JSON editing."
```

---

## Phase 4 — Polymorphic serializers

**Goal:** `ReportDetailSerializer` devuelve `blocks` como lista polimórfica con shape tipado por subtipo. Agregados `yoy`, `q1_rollup`, `follower_snapshots` desaparecen.

### Task 4.1: Write polymorphic serializer tests

**Files:**
- Modify: `backend/tests/unit/test_report_detail_serializer.py` (rewrite)
- Create: `backend/tests/unit/blocks/test_polymorphic_serializer.py`
- Create: `backend/tests/unit/blocks/test_polymorphic_prefetch.py`

- [ ] **Step 1: Rewrite test_report_detail_serializer.py**

Replace content:

```python
"""ReportDetailSerializer post-DEV-116: blocks polimórficos, sin
metrics/yoy/q1_rollup/follower_snapshots."""
import pytest

from apps.reports.tests.factories import make_report


@pytest.mark.django_db
def test_payload_has_no_legacy_fields():
    from apps.reports.serializers import ReportDetailSerializer
    report = make_report()
    data = ReportDetailSerializer(report).data
    for gone in ["metrics", "yoy", "q1_rollup", "follower_snapshots", "onelink"]:
        assert gone not in data, f"legacy field still in payload: {gone}"


@pytest.mark.django_db
def test_payload_includes_blocks_as_list():
    from apps.reports.models import TextImageBlock
    from apps.reports.serializers import ReportDetailSerializer
    report = make_report()
    TextImageBlock.objects.create(
        report=report, order=1, title="Hello", body="world",
    )
    data = ReportDetailSerializer(report).data
    assert "blocks" in data
    assert len(data["blocks"]) == 1
    assert data["blocks"][0]["type"] == "TextImageBlock"
    assert data["blocks"][0]["title"] == "Hello"
```

- [ ] **Step 2: Write polymorphic serializer unit test**

Create: `backend/tests/unit/blocks/test_polymorphic_serializer.py`

```python
"""El ReportBlockSerializer despacha por subtipo correctamente."""
import pytest

from apps.reports.tests.factories import make_report


@pytest.mark.django_db
def test_serializer_dispatches_by_subtype():
    from apps.reports.models import (
        TextImageBlock, KpiGridBlock, KpiTile, MetricsTableBlock,
        ChartBlock, ChartDataPoint,
    )
    from apps.reports.serializers import ReportBlockSerializer

    report = make_report()
    ti = TextImageBlock.objects.create(report=report, order=1, title="X")
    kpi = KpiGridBlock.objects.create(report=report, order=2, title="KPIs")
    KpiTile.objects.create(kpi_grid_block=kpi, label="Reach", value=100, order=1)
    mt = MetricsTableBlock.objects.create(report=report, order=3, network="INSTAGRAM")
    cb = ChartBlock.objects.create(report=report, order=4, network="INSTAGRAM")
    ChartDataPoint.objects.create(chart_block=cb, label="Ene", value=100, order=1)

    from apps.reports.models import ReportBlock
    blocks = ReportBlock.objects.filter(report=report).order_by("order")
    serialized = ReportBlockSerializer(blocks, many=True).data

    assert len(serialized) == 4
    assert [b["type"] for b in serialized] == [
        "TextImageBlock", "KpiGridBlock", "MetricsTableBlock", "ChartBlock",
    ]
    # Nested children presentes
    assert serialized[1]["tiles"][0]["label"] == "Reach"
    assert serialized[3]["data_points"][0]["label"] == "Ene"
```

- [ ] **Step 3: Write prefetch / N+1 test**

Create: `backend/tests/unit/blocks/test_polymorphic_prefetch.py`

```python
"""El serializer polimórfico no genera N+1 al listar blocks."""
import pytest

from apps.reports.tests.factories import make_report
from django.test.utils import CaptureQueriesContext
from django.db import connection


@pytest.mark.django_db
def test_no_n_plus_1_on_mixed_block_types():
    from apps.reports.models import (
        ReportBlock, TextImageBlock, KpiGridBlock, KpiTile,
        MetricsTableBlock, MetricsTableRow, ChartBlock, ChartDataPoint,
    )
    from apps.reports.serializers import ReportDetailSerializer

    report = make_report()
    TextImageBlock.objects.create(report=report, order=1)
    kpi = KpiGridBlock.objects.create(report=report, order=2)
    for i in range(3):
        KpiTile.objects.create(kpi_grid_block=kpi, label=f"t{i}", value=i, order=i)
    mt = MetricsTableBlock.objects.create(report=report, order=3)
    for i in range(5):
        MetricsTableRow.objects.create(
            metrics_table_block=mt, metric_name=f"m{i}", value=i, order=i,
        )
    chart = ChartBlock.objects.create(report=report, order=4)
    for i in range(3):
        ChartDataPoint.objects.create(chart_block=chart, label=f"p{i}", value=i, order=i)

    with CaptureQueriesContext(connection) as ctx:
        data = ReportDetailSerializer(report).data
        _ = data["blocks"]  # force evaluation

    # Target: ≤8 queries (1 Report + 1 polymorphic blocks + 6 per-child
    # prefetches). Si empieza a crecer con N blocks, es N+1.
    assert len(ctx.captured_queries) <= 10, (
        f"Too many queries ({len(ctx.captured_queries)}):\n" +
        "\n".join(q["sql"][:100] for q in ctx.captured_queries)
    )
```

- [ ] **Step 4: Run tests — expected FAIL**

```bash
docker compose exec -T backend pytest backend/tests/unit/test_report_detail_serializer.py backend/tests/unit/blocks/test_polymorphic_serializer.py backend/tests/unit/blocks/test_polymorphic_prefetch.py -v
```
Expected: todos fallan — el serializer todavía es el viejo.

### Task 4.2: Rewrite serializers.py

**Files:**
- Modify: `backend/apps/reports/serializers.py`
- Modify: `backend/apps/reports/views.py` (ajustar prefetches)

- [ ] **Step 1: Rewrite serializers.py**

```python
"""Report serializers — post-DEV-116.

ReportBlockSerializer es polimórfico; despacha a un sub-serializer por
subtipo. Los campos agregados cross-report (yoy, q1_rollup, follower_snapshots)
se eliminaron porque dependían de ReportMetric, que ya no existe.
"""
from rest_framework import serializers
from rest_framework_polymorphic.serializers import PolymorphicSerializer

from .models import (
    Report, ReportBlock,
    TextImageBlock, KpiGridBlock, KpiTile,
    MetricsTableBlock, MetricsTableRow,
    TopContentBlock, AttributionTableBlock,
    ChartBlock, ChartDataPoint,
    TopContent, OneLinkAttribution,
)


# Child row serializers

class KpiTileSerializer(serializers.ModelSerializer):
    class Meta:
        model = KpiTile
        fields = ("label", "value", "period_comparison", "order")


class MetricsTableRowSerializer(serializers.ModelSerializer):
    class Meta:
        model = MetricsTableRow
        fields = ("metric_name", "value", "source_type", "period_comparison", "order")


class ChartDataPointSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChartDataPoint
        fields = ("label", "value", "order")


class TopContentItemSerializer(serializers.ModelSerializer):
    thumbnail_url = serializers.SerializerMethodField()

    class Meta:
        model = TopContent
        fields = (
            "kind", "network", "source_type", "rank", "handle",
            "caption", "thumbnail_url", "post_url", "metrics",
        )

    def get_thumbnail_url(self, obj):
        return obj.thumbnail.url if obj.thumbnail else None


class OneLinkEntrySerializer(serializers.ModelSerializer):
    class Meta:
        model = OneLinkAttribution
        fields = ("influencer_handle", "clicks", "app_downloads")


# Subtype block serializers

class _ReportBlockBaseFields(serializers.ModelSerializer):
    """Fields compartidos por todos los subtypes (heredados del base)."""
    class Meta:
        fields = ("id", "order", "instructions")


class TextImageBlockSerializer(serializers.ModelSerializer):
    image_url = serializers.SerializerMethodField()

    class Meta:
        model = TextImageBlock
        fields = (
            "id", "order", "instructions",
            "title", "body", "columns", "image_position", "image_alt",
            "image_url",
        )

    def get_image_url(self, obj):
        return obj.image.url if obj.image else None


class KpiGridBlockSerializer(serializers.ModelSerializer):
    tiles = KpiTileSerializer(many=True, read_only=True)

    class Meta:
        model = KpiGridBlock
        fields = ("id", "order", "instructions", "title", "tiles")


class MetricsTableBlockSerializer(serializers.ModelSerializer):
    rows = MetricsTableRowSerializer(many=True, read_only=True)

    class Meta:
        model = MetricsTableBlock
        fields = ("id", "order", "instructions", "title", "network", "rows")


class TopContentBlockSerializer(serializers.ModelSerializer):
    items = TopContentItemSerializer(many=True, read_only=True)

    class Meta:
        model = TopContentBlock
        fields = ("id", "order", "instructions", "title", "kind", "limit", "items")


class AttributionTableBlockSerializer(serializers.ModelSerializer):
    entries = OneLinkEntrySerializer(many=True, read_only=True)

    class Meta:
        model = AttributionTableBlock
        fields = ("id", "order", "instructions", "title", "show_total", "entries")


class ChartBlockSerializer(serializers.ModelSerializer):
    data_points = ChartDataPointSerializer(many=True, read_only=True)

    class Meta:
        model = ChartBlock
        fields = ("id", "order", "instructions", "title", "network", "chart_type", "data_points")


# Polymorphic dispatcher

class ReportBlockSerializer(PolymorphicSerializer):
    model_serializer_mapping = {
        TextImageBlock: TextImageBlockSerializer,
        KpiGridBlock: KpiGridBlockSerializer,
        MetricsTableBlock: MetricsTableBlockSerializer,
        TopContentBlock: TopContentBlockSerializer,
        AttributionTableBlock: AttributionTableBlockSerializer,
        ChartBlock: ChartBlockSerializer,
    }
    resource_type_field_name = "type"


# Top-level Report serializer

class ReportDetailSerializer(serializers.ModelSerializer):
    stage_name = serializers.CharField(source="stage.name", read_only=True)
    stage_id = serializers.IntegerField(source="stage.id", read_only=True)
    campaign_name = serializers.CharField(source="stage.campaign.name", read_only=True)
    campaign_id = serializers.IntegerField(source="stage.campaign.id", read_only=True)
    brand_name = serializers.CharField(source="stage.campaign.brand.name", read_only=True)
    display_title = serializers.CharField(read_only=True)
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
            "blocks", "original_pdf_url",
        )

    def get_original_pdf_url(self, obj):
        return obj.original_pdf.url if obj.original_pdf else None
```

> **Nota sobre `rest_framework_polymorphic`**: es un paquete complementario a `django-polymorphic` (`pip install drf-polymorphic`). Si no está, agregarlo al requirements en este step. Verificar versión compatible.

- [ ] **Step 2: Add drf-polymorphic to requirements (si falta)**

Add to `backend/requirements.txt`:
```
rest-framework-polymorphic==0.4.7  # complementary package for DRF + django-polymorphic
```

Si el paquete correcto es `drf-polymorphic` (algunos forks tienen nombre distinto), verificar con `pip search` o docs antes.

- [ ] **Step 3: Rebuild backend**

```bash
docker compose build backend && docker compose up -d backend
```

- [ ] **Step 4: Update views.py prefetches**

Modify `backend/apps/reports/views.py` — en `ReportDetailView` (o equivalent):

```python
from apps.reports.models import (
    TextImageBlock, KpiGridBlock, MetricsTableBlock,
    TopContentBlock, AttributionTableBlock, ChartBlock,
)
from django.db.models import Prefetch

# En el get_queryset:
return Report.objects.prefetch_related(
    "blocks",  # base polymorphic
    "blocks__kpigridblock__tiles",
    "blocks__metricstableblock__rows",
    "blocks__chartblock__data_points",
    "blocks__topcontentblock__items",
    "blocks__attributiontableblock__entries",
)
```

Adaptar a la estructura real del view existente.

- [ ] **Step 5: Run serializer tests**

```bash
docker compose exec -T backend pytest backend/tests/unit/test_report_detail_serializer.py backend/tests/unit/blocks/test_polymorphic_serializer.py backend/tests/unit/blocks/test_polymorphic_prefetch.py -v
```
Expected: todos pasan. Si el N+1 test falla por muchas queries, ajustar los prefetches.

- [ ] **Step 6: Commit**

```bash
git add backend/apps/reports/serializers.py backend/apps/reports/views.py backend/requirements.txt backend/tests/unit/test_report_detail_serializer.py backend/tests/unit/blocks/test_polymorphic_serializer.py backend/tests/unit/blocks/test_polymorphic_prefetch.py
git commit -m "feat(reports-api): polymorphic serializer for typed blocks

- ReportBlockSerializer dispatches by subtype (drf-polymorphic).
- Each subtype has nested serializers for child rows.
- Prefetch strategy declared in view to avoid N+1.
- ReportDetailSerializer no longer exposes metrics/yoy/q1_rollup/
  follower_snapshots — those are dead fields post-refactor."
```

### Task 4.3: Tenant scoping regression test (dim 7 — Security)

Verificar que el refactor no rompió el tenant scoping. Gotcha del repo (CLAUDE.md): scoping va en la view, no en middleware — el refactor no toca views, pero vale un integration test para confirmar.

**Files:**
- Create: `backend/tests/unit/blocks/test_tenant_scoping.py`

- [ ] **Step 1: Write test**

```python
"""Tenant scoping regression — un cliente no puede ver blocks de otro cliente.
Verifica el gotcha del repo documentado en CLAUDE.md."""
import pytest


@pytest.mark.django_db
def test_blocks_scoped_by_client_via_report():
    from apps.reports.models import KpiGridBlock
    from apps.reports.tests.factories import make_report, make_client, make_brand, make_campaign, make_stage

    # Setup: dos clientes con sus propios blocks
    client_a = make_client("Client A")
    brand_a = make_brand(client=client_a, name="Brand A")
    campaign_a = make_campaign(brand=brand_a, name="Campaign A")
    stage_a = make_stage(campaign=campaign_a, order=1, name="Stage A")
    report_a = make_report(stage=stage_a)
    KpiGridBlock.objects.create(report=report_a, order=1, title="KPIs A")

    client_b = make_client("Client B")
    brand_b = make_brand(client=client_b, name="Brand B")
    campaign_b = make_campaign(brand=brand_b, name="Campaign B")
    stage_b = make_stage(campaign=campaign_b, order=1, name="Stage B")
    report_b = make_report(stage=stage_b)
    KpiGridBlock.objects.create(report=report_b, order=1, title="KPIs B")

    # Query scoped by client_a — solo ve su block
    from apps.reports.models import ReportBlock
    scoped_a = ReportBlock.objects.filter(
        report__stage__campaign__brand__client=client_a,
    )
    assert scoped_a.count() == 1
    assert scoped_a.first().kpigridblock.title == "KPIs A"


@pytest.mark.django_db
def test_api_endpoint_scopes_by_authenticated_client(client):
    """Smoke del endpoint real con dos users de dos clients distintos."""
    from django.contrib.auth import get_user_model
    from apps.reports.tests.factories import make_report, make_client, make_brand, make_campaign, make_stage
    from apps.reports.models import KpiGridBlock

    User = get_user_model()

    # Setup client A + user A
    client_a = make_client("Client A")
    brand_a = make_brand(client=client_a)
    campaign_a = make_campaign(brand=brand_a)
    stage_a = make_stage(campaign=campaign_a)
    report_a = make_report(stage=stage_a)
    KpiGridBlock.objects.create(report=report_a, order=1, title="Grid A")
    user_a = User.objects.create_user(email="a@test.com", password="pw", client=client_a)

    # Setup client B + user B + report B
    client_b = make_client("Client B")
    brand_b = make_brand(client=client_b)
    campaign_b = make_campaign(brand=brand_b)
    stage_b = make_stage(campaign=campaign_b)
    report_b = make_report(stage=stage_b)

    # User A tries to access report_b → 404 (not 403, per repo scoping pattern)
    client.force_login(user_a)
    response = client.get(f"/api/reports/{report_b.id}/")
    assert response.status_code == 404

    # User A accessing their own report → 200
    response = client.get(f"/api/reports/{report_a.id}/")
    assert response.status_code == 200
```

- [ ] **Step 2: Run test (expected PASS — el scoping vive en la view y no fue tocado)**

```bash
docker compose exec -T backend pytest backend/tests/unit/blocks/test_tenant_scoping.py -v
```
Expected: 2 passed.

Si falla, stop y reportar — algo del refactor inadvertidamente rompió el scoping (probable: prefetches en la view que no filtran correctamente el polymorphic queryset).

- [ ] **Step 3: Commit**

```bash
git add backend/tests/unit/blocks/test_tenant_scoping.py
git commit -m "test(reports): regression test for tenant scoping with typed blocks

Verifies the CLAUDE.md gotcha that scoping lives in the view — the
typed blocks refactor preserves this invariant. Fails fast (P9) if
a future change accidentally leaks blocks across clients."
```

### Task 4.4: Delete registry + schemas + aggregations

**Files:**
- Delete: `backend/apps/reports/blocks/registry.py`
- Delete: `backend/apps/reports/blocks/schemas.py`
- Delete: `backend/apps/reports/blocks/__init__.py`
- Delete: `backend/apps/reports/services/aggregations.py`
- Delete: `backend/tests/unit/test_block_config_validation.py`
- Delete: `backend/tests/unit/test_report_aggregations.py`
- Delete: `backend/tests/unit/test_report_block_config.py`
- Delete: `backend/tests/unit/test_report_block_model.py` (reemplazado por tests/unit/blocks/)
- Delete: `backend/tests/unit/test_report_serializer_blocks.py` (reemplazado)

- [ ] **Step 1: Remove imports**

Buscar any imports de los modules a eliminar:
```bash
docker compose exec -T backend grep -r "from apps.reports.blocks" backend/apps backend/tests
docker compose exec -T backend grep -r "services.aggregations" backend/apps backend/tests
```

Si aparecen referencias fuera de los archivos a eliminar, modificarlas o eliminarlas.

- [ ] **Step 2: Delete files**

```bash
git rm backend/apps/reports/blocks/registry.py backend/apps/reports/blocks/schemas.py backend/apps/reports/blocks/__init__.py
rmdir backend/apps/reports/blocks
git rm backend/apps/reports/services/aggregations.py
# Tests:
git rm backend/tests/unit/test_block_config_validation.py backend/tests/unit/test_report_aggregations.py backend/tests/unit/test_report_block_config.py backend/tests/unit/test_report_block_model.py backend/tests/unit/test_report_serializer_blocks.py
```

- [ ] **Step 3: Run the legacy-gone test**

```bash
docker compose exec -T backend pytest backend/tests/unit/blocks/test_legacy_models_gone.py -v
```
Expected: pasan.

- [ ] **Step 4: Run full backend suite**

```bash
docker compose exec -T backend pytest backend/tests/unit/ -q 2>&1 | tail -20
```
Expected: todos pasan (o quedan sólo tests de seed/viewer que se arreglan en Phase 5).

- [ ] **Step 5: Commit**

```bash
git commit -m "chore(reports): delete registry, schemas, aggregations + obsolete tests

Post-DEV-116 these modules have no callers:
- blocks/registry.py + schemas.py: replaced by typed models with DB
  constraints and choices.
- services/aggregations.py: build_yoy / build_q1_rollup /
  build_follower_snapshots are dead; data lives in blocks as snapshots."
```

---

## Phase 5 — Seed rewrite

**Goal:** `seed_demo.py` crea reportes con los 11 blocks tipados. Tests de seed verifican el payload.

### Task 5.1: Rewrite seed tests

**Files:**
- Modify: `backend/tests/unit/test_seed_demo.py` (adapt or rewrite)
- Delete: `backend/tests/unit/test_seed_demo_blocks.py` (reemplazar)
- Delete: `backend/tests/unit/test_seed_demo_report_viewer.py`
- Modify: `backend/tests/unit/test_report_viewer_models.py` (reescribir)

- [ ] **Step 1: Rewrite seed_demo_blocks test**

Replace `backend/tests/unit/test_seed_demo_blocks.py` content (or rename to reflect new reality):

```python
"""Post-DEV-116: seed_demo crea bloques tipados, no configs JSON."""
import pytest
from django.core.management import call_command


@pytest.mark.django_db
def test_seed_demo_creates_typed_blocks():
    from apps.reports.models import (
        Report, TextImageBlock, KpiGridBlock, MetricsTableBlock,
        TopContentBlock, AttributionTableBlock, ChartBlock,
    )
    call_command("seed_demo")
    # Al menos un reporte con layout completo (Educación Marzo)
    full_report = (
        Report.objects.filter(
            stage__kind="EDUCATION",
            title__icontains="Marzo",
            kind=Report.Kind.GENERAL,
        )
        .first()
    )
    assert full_report is not None, "Expected an Educación Marzo General report"

    # 11 bloques esperados
    assert full_report.blocks.count() == 11

    # Cada subtipo está representado
    assert KpiGridBlock.objects.filter(report=full_report).exists()
    assert MetricsTableBlock.objects.filter(report=full_report).count() == 4  # 1 cross + IG + TikTok + X
    assert TopContentBlock.objects.filter(report=full_report).count() == 2  # POST + CREATOR
    assert AttributionTableBlock.objects.filter(report=full_report).exists()
    assert ChartBlock.objects.filter(report=full_report).count() == 3  # IG + TikTok + X


@pytest.mark.django_db
def test_seed_demo_instagram_metrics_table_has_typed_rows():
    from apps.reports.models import MetricsTableBlock, Report
    call_command("seed_demo")
    full_report = Report.objects.filter(
        stage__kind="EDUCATION", title__icontains="Marzo", kind="GENERAL",
    ).first()
    ig_table = MetricsTableBlock.objects.filter(
        report=full_report, network="INSTAGRAM",
    ).first()
    assert ig_table is not None
    assert ig_table.rows.count() > 0
    # Spot-check: existe un row de reach orgánico
    assert ig_table.rows.filter(
        metric_name="reach", source_type="ORGANIC",
    ).exists()
```

- [ ] **Step 2: Rewrite test_report_viewer_models.py similarly (o delete si ya no aplica)**

Check el archivo. Si testea el shape del payload viejo (`follower_snapshots`, etc.), reescribirlo alrededor de los typed blocks.

- [ ] **Step 3: Run (expected FAIL)**

```bash
docker compose exec -T backend pytest backend/tests/unit/test_seed_demo_blocks.py backend/tests/unit/test_seed_demo.py -v
```
Expected: tests fallan — seed_demo.py todavía crea blocks viejos.

### Task 5.2: Rewrite seed_demo.py

**Files:**
- Modify: `backend/apps/tenants/management/commands/seed_demo.py`

> **Nota:** `seed_demo.py` actual es ~480 líneas. Este task es grande. Dividirlo en sub-tasks si se hace dinámico.

- [ ] **Step 1: Refactor `_seed_reports` function**

En `seed_demo.py`, la función `_seed_reports` hoy crea `ReportMetric` rows + blocks via `_seed_blocks_for_full_report`. Reescribirla para crear bloques tipados directamente:

Ejemplo esquemático (reemplazar el bloque relevante):

```python
# ANTES: ReportMetric rows + blocks con config JSON
# DESPUÉS: directamente blocks tipados con sus children

def _seed_reports(self, stages):
    from apps.reports.models import (
        Report, TextImageBlock, KpiGridBlock, KpiTile,
        MetricsTableBlock, MetricsTableRow,
        TopContentBlock, AttributionTableBlock,
        ChartBlock, ChartDataPoint,
        TopContent, OneLinkAttribution,
    )
    # ... crear Report ...

    if is_full_layout_report:
        _seed_full_layout(report)
    # ... etc
```

- [ ] **Step 2: Write _seed_full_layout helper**

Agregar al final de `seed_demo.py`:

```python
def _seed_full_layout(report):
    """11 bloques tipados para un reporte completo."""
    from apps.reports.models import (
        KpiGridBlock, KpiTile, MetricsTableBlock, MetricsTableRow,
        TopContentBlock, AttributionTableBlock, OneLinkAttribution,
        ChartBlock, ChartDataPoint, TopContent,
    )
    from apps.reports.choices import Network, SourceType

    # Block 1: KPI grid
    kpi = KpiGridBlock.objects.create(
        report=report, order=1, title="KPIs del mes",
    )
    KpiTile.objects.create(kpi_grid_block=kpi, label="Reach total", value=2_840_000, order=1)
    KpiTile.objects.create(kpi_grid_block=kpi, label="Reach orgánico", value=412_000, period_comparison=6.1, order=2)
    KpiTile.objects.create(kpi_grid_block=kpi, label="Reach influencer", value=2_430_000, period_comparison=14.8, order=3)

    # Block 2: Mes a mes (cross-network)
    mes_a_mes = MetricsTableBlock.objects.create(
        report=report, order=2, title="Mes a mes",
    )
    MetricsTableRow.objects.create(
        metrics_table_block=mes_a_mes, metric_name="engagement_rate",
        value=4.8, source_type=SourceType.ORGANIC, period_comparison=0.3, order=1,
    )
    MetricsTableRow.objects.create(
        metrics_table_block=mes_a_mes, metric_name="followers_gained",
        value=18_400, source_type=SourceType.ORGANIC, period_comparison=24, order=2,
    )

    # Block 3: Instagram table
    ig = MetricsTableBlock.objects.create(
        report=report, order=3, title="Instagram", network=Network.INSTAGRAM,
    )
    for i, (st, mn, val, delta) in enumerate([
        (SourceType.ORGANIC, "reach", 284_000, 6.1),
        (SourceType.PAID, "reach", 512_000, None),
        (SourceType.INFLUENCER, "reach", 1_640_000, 14.8),
    ], 1):
        MetricsTableRow.objects.create(
            metrics_table_block=ig, metric_name=mn, value=val,
            source_type=st, period_comparison=delta, order=i,
        )

    # Block 4: TikTok table
    tt = MetricsTableBlock.objects.create(
        report=report, order=4, title="TikTok", network=Network.TIKTOK,
    )
    for i, (st, val) in enumerate([
        (SourceType.ORGANIC, 98_000),
        (SourceType.PAID, 180_000),
        (SourceType.INFLUENCER, 620_000),
    ], 1):
        MetricsTableRow.objects.create(
            metrics_table_block=tt, metric_name="reach", value=val,
            source_type=st, order=i,
        )

    # Block 5: X table
    x = MetricsTableBlock.objects.create(
        report=report, order=5, title="X / Twitter", network=Network.X,
    )
    for i, (st, val) in enumerate([
        (SourceType.ORGANIC, 30_000),
        (SourceType.PAID, 42_000),
        (SourceType.INFLUENCER, 170_000),
    ], 1):
        MetricsTableRow.objects.create(
            metrics_table_block=x, metric_name="reach", value=val,
            source_type=st, order=i,
        )

    # Block 6: Top posts
    posts = TopContentBlock.objects.create(
        report=report, order=6, title="Posts del mes", kind="POST", limit=6,
    )
    # TopContent items se crean en _seed_report_viewer_fixtures (existe ya)

    # Block 7: Top creators
    creators = TopContentBlock.objects.create(
        report=report, order=7, title="Creators del mes", kind="CREATOR", limit=6,
    )

    # Block 8: Attribution
    attr = AttributionTableBlock.objects.create(
        report=report, order=8, show_total=True,
    )
    # OneLinkAttribution entries se crean en _seed_report_viewer_fixtures

    # Blocks 9-11: Charts (IG, TikTok, X)
    for idx, (net, title_suffix) in enumerate([
        (Network.INSTAGRAM, "IG"),
        (Network.TIKTOK, "TikTok"),
        (Network.X, "X"),
    ], 9):
        chart = ChartBlock.objects.create(
            report=report, order=idx, title=f"Followers {title_suffix}",
            network=net, chart_type="bar",
        )
        for i, (month, val) in enumerate([
            ("Enero", 99_500), ("Febrero", 104_568), ("Marzo", 107_072),
        ], 1):
            ChartDataPoint.objects.create(
                chart_block=chart, label=month, value=val, order=i,
            )
```

- [ ] **Step 3: Refactor `_seed_report_viewer_fixtures`**

La función existente crea `TopContent` con FK a un block. Ajustarla para que el FK apunte al `TopContentBlock` del report, no a un block genérico.

- [ ] **Step 4: Delete all `ReportMetric` creation in seed**

Remover código que crea `ReportMetric` — ya no existe el modelo.

- [ ] **Step 5: Delete `_seed_blocks_for_full_report` y `_seed_blocks_minimal` (viejas)**

Reemplazadas por `_seed_full_layout`.

- [ ] **Step 6: Re-run seed in container**

```bash
docker compose exec -T backend python manage.py seed_demo
```
Expected: corre sin errores.

- [ ] **Step 7: Run seed tests**

```bash
docker compose exec -T backend pytest backend/tests/unit/test_seed_demo_blocks.py backend/tests/unit/test_seed_demo.py -v
```
Expected: pasan.

- [ ] **Step 8: Commit**

```bash
git add backend/apps/tenants/management/commands/seed_demo.py backend/tests/unit/test_seed_demo.py backend/tests/unit/test_seed_demo_blocks.py
# Delete tests obsolescent:
git rm backend/tests/unit/test_seed_demo_report_viewer.py backend/tests/unit/test_report_viewer_models.py 2>/dev/null || true
git commit -m "refactor(seed): typed blocks for demo data

- _seed_full_layout creates 11 typed blocks per full report.
- ReportMetric creation removed (model gone).
- TopContent + OneLinkAttribution linked to their typed block parents."
```

---

## Phase 6 — Frontend adaptation

**Goal:** DTOs tipados en `lib/api.ts`, renderers leen nuevos fields, typecheck limpio, E2E smoke verde.

### Task 6.1: Update ReportBlockDto to discriminated union

**Files:**
- Modify: `frontend/lib/api.ts`

- [ ] **Step 1: Inspect current ReportBlockDto**

```bash
grep -n "ReportBlockDto\|ReportBlockType" frontend/lib/api.ts
```

- [ ] **Step 2: Replace with discriminated union**

Locate the current `ReportBlockDto` definition and replace with:

```typescript
// -- Child row DTOs --

export type KpiTileDto = {
  label: string;
  value: string;
  period_comparison: string | null;
  order: number;
};

export type MetricsTableRowDto = {
  metric_name: string;
  value: string;
  source_type: "ORGANIC" | "INFLUENCER" | "PAID" | null;
  period_comparison: string | null;
  order: number;
};

export type ChartDataPointDto = {
  label: string;
  value: string;
  order: number;
};

export type TopContentItemDto = {
  kind: "POST" | "CREATOR";
  network: Network;
  source_type: SourceType;
  rank: number;
  handle: string;
  caption: string;
  thumbnail_url: string | null;
  post_url: string;
  metrics: Record<string, unknown>;
};

export type OneLinkEntryDto = {
  influencer_handle: string;
  clicks: number;
  app_downloads: number;
};

// -- Block subtype DTOs --

type BaseBlockFields = {
  id: number;
  order: number;
  instructions: string;
};

export type TextImageBlockDto = BaseBlockFields & {
  type: "TextImageBlock";
  title: string;
  body: string;
  columns: 1 | 2 | 3;
  image_position: "left" | "right" | "top";
  image_alt: string;
  image_url: string | null;
};

export type KpiGridBlockDto = BaseBlockFields & {
  type: "KpiGridBlock";
  title: string;
  tiles: KpiTileDto[];
};

export type MetricsTableBlockDto = BaseBlockFields & {
  type: "MetricsTableBlock";
  title: string;
  network: Network | null;
  rows: MetricsTableRowDto[];
};

export type TopContentBlockDto = BaseBlockFields & {
  type: "TopContentBlock";
  title: string;
  kind: "POST" | "CREATOR";
  limit: number;
  items: TopContentItemDto[];
};

export type AttributionTableBlockDto = BaseBlockFields & {
  type: "AttributionTableBlock";
  title: string;
  show_total: boolean;
  entries: OneLinkEntryDto[];
};

export type ChartBlockDto = BaseBlockFields & {
  type: "ChartBlock";
  title: string;
  network: Network | null;
  chart_type: "bar";
  data_points: ChartDataPointDto[];
};

export type ReportBlockDto =
  | TextImageBlockDto
  | KpiGridBlockDto
  | MetricsTableBlockDto
  | TopContentBlockDto
  | AttributionTableBlockDto
  | ChartBlockDto;
```

- [ ] **Step 3: Remove dead ReportDto fields**

En `ReportDto`, eliminar: `metrics`, `onelink`, `follower_snapshots`, `yoy`, `q1_rollup`.

- [ ] **Step 4: Run typecheck (expected fails en renderers)**

```bash
cd frontend && npm run typecheck
```
Expected: errors en los renderers que leen los fields viejos.

### Task 6.2: Update renderers to new field shapes

**Files:**
- Modify: `frontend/app/reports/[id]/blocks/MetricsTableBlock.tsx`
- Modify: `frontend/app/reports/[id]/blocks/KpiGridBlock.tsx`
- Modify: `frontend/app/reports/[id]/blocks/ChartBlock.tsx`
- Modify: `frontend/app/reports/[id]/blocks/AttributionTableBlock.tsx`
- Modify: `frontend/app/reports/[id]/blocks/TopContentBlock.tsx`
- Modify: `frontend/app/reports/[id]/blocks/TextImageBlock.tsx`
- Modify: `frontend/app/reports/[id]/blocks/BlockRenderer.tsx`

- [ ] **Step 1: Update BlockRenderer dispatcher**

`BlockRenderer.tsx` despacha por `type`. Ajustar las keys al nuevo naming:

```typescript
const BLOCK_COMPONENTS = {
  TextImageBlock: TextImageBlock,
  KpiGridBlock: KpiGridBlock,
  MetricsTableBlock: MetricsTableBlock,
  TopContentBlock: TopContentBlock,
  AttributionTableBlock: AttributionTableBlock,
  ChartBlock: ChartBlock,
} as const;
```

- [ ] **Step 2: MetricsTableBlock.tsx**

Reemplazar la lógica de `report.metrics.filter(...)` por `block.rows.map(...)`. El `network` ahora está en `block.network` (metadata tag).

Signature del componente cambia:
```typescript
export default function MetricsTableBlock({ block }: { block: MetricsTableBlockDto }) { ... }
```

Renderizar cada row directamente desde `block.rows`.

- [ ] **Step 3: KpiGridBlock.tsx**

Reemplazar cálculo de `reach_total` desde metrics por `block.tiles.map(...)`. Cada tile tiene `{label, value, period_comparison}` directo.

- [ ] **Step 4: ChartBlock.tsx**

Reemplazar `report.follower_snapshots[network]` por `block.data_points`. `block.network` y `block.chart_type` quedan como metadata.

- [ ] **Step 5: AttributionTableBlock.tsx**

Reemplazar `report.onelink` por `block.entries`.

- [ ] **Step 6: TopContentBlock.tsx**

Reemplazar `report.top_content` (o como esté leyendo items) por `block.items`.

- [ ] **Step 7: TextImageBlock.tsx**

Ya era mayormente config-driven; ahora los fields vienen directo en el block (`block.title`, `block.body`, `block.image_position`, `block.image_url`). Quitar el `config as unknown as ...` pattern.

- [ ] **Step 8: Run typecheck**

```bash
cd frontend && npm run typecheck
```
Expected: typecheck limpio.

- [ ] **Step 9: Manual smoke en browser**

```bash
docker compose restart frontend
```

Browser: `http://localhost:3000/reports/<id>` con seed demo. Verificar:
- Todos los block types se renderizan.
- Números reales en cada KPI, tabla, chart.
- Sin errores en la consola.

- [ ] **Step 10: Run E2E smoke**

```bash
cd frontend && npm run test:e2e:smoke
```
Expected: todos pasan (los specs verifican pills "KPIS", "MES A MES", "INSTAGRAM", "X / TWITTER", etc. — que vienen de los titles de los blocks seedeados).

- [ ] **Step 10a: Frontend quality checks (dim 11)**

Verificar que la edición mantiene los compromisos de frontend quality:

```bash
# Component size — ningún renderer debería pasar 200 líneas
wc -l frontend/app/reports/[id]/blocks/*.tsx
```
Expected: todos <200 líneas. Si alguno crece por la union tipada, considerar split (ej. helpers compartidos en `frontend/app/reports/[id]/blocks/_shared.tsx`).

```bash
# Design tokens — no hardcoded colors/spacing nuevos
grep -E "#[0-9a-fA-F]{3,6}|rgb\(" frontend/app/reports/[id]/blocks/*.tsx
```
Expected: sin matches (salvo CSS vars `var(--chirri-*)` que son OK).

```bash
# Accessibility preservada — los `<table>`, `scope`, `aria-*` que existían siguen presentes
grep -E "scope=|aria-" frontend/app/reports/[id]/blocks/*.tsx | wc -l
```
Expected: número similar o mayor al pre-edit (baseline count: anotar antes del Step 2 si se quiere ser estricto).

- [ ] **Step 11: Commit**

```bash
git add frontend/lib/api.ts frontend/app/reports/[id]/blocks/
git commit -m "feat(frontend): consume typed block DTOs with discriminated union

- ReportBlockDto is now a discriminated union (6 subtypes).
- Renderers read typed fields directly instead of config JSON.
- Dead ReportDto fields removed (metrics, onelink, follower_snapshots, yoy, q1_rollup).
- Typecheck clean, E2E smoke green."
```

---

## Phase 7 — Documentation + quality score

### Task 7.1: Update QUALITY_SCORE.md

**Files:**
- Modify: `docs/QUALITY_SCORE.md`

- [ ] **Step 1: Read current entry**

```bash
cat docs/QUALITY_SCORE.md 2>&1 | head -80
```

- [ ] **Step 2: Update reports domain grade**

Re-evaluar cada dimensión post-refactor y ajustar el grade. Expected: B → A (el refactor elimina complejidad: registry, schemas, aggregations, config JSON).

Agregar un breve changelog line:
```markdown
## Changelog

- 2026-04-22 — DEV-116: typed blocks refactor. Reports domain B → A.
  Removed ReportMetric, block config JSON, aggregations. Admin UX
  now typed without JSON editing.
```

- [ ] **Step 3: Commit**

```bash
git add docs/QUALITY_SCORE.md
git commit -m "docs(quality): reports domain B → A after typed blocks refactor"
```

### Task 7.2: Document destructive migration + rollback (dim 13)

**Files:**
- Create or modify: `docs/DEPLOY.md`

- [ ] **Step 1: Document migration 0010 as destructive**

Create `docs/DEPLOY.md` si no existe, o append si existe:

```markdown
# Deploy Notes

## 2026-04-22 — DEV-116 typed blocks refactor

### Destructive migrations

- **0009_typed_blocks**: adds new tables (non-destructive, forward-compatible).
- **0010_drop_legacy_blocks**: DROPS `ReportMetric` table, `ReportBlock.config/type/image` fields, `OneLinkAttribution.report` FK. **Irreversible** — rollback requires DB restore from backup or re-running `seed_demo`.

### Pre-deploy checklist

- [x] No production data at time of merge (confirmed 2026-04-22).
- [x] Staging deploy verified (Hetzner `development` branch → deploy.yml).
- [ ] After deploy, verify:
  - `docker compose exec backend python manage.py migrate` finished without error (check Hetzner deploy log).
  - `python manage.py seed_demo` re-runs cleanly.
  - Smoke: login with Balanz demo credentials, view Educación Marzo report, verify 11 blocks render.

### Rollback procedure

If issues appear post-deploy on a non-empty DB (not the case for DEV-116, but precedent):

1. Revert the deploy commit on `development`: `git revert <sha> && git push`.
2. This redeploys the previous Docker image (Hetzner pulls the revert commit).
3. **Data loss**: `ReportMetric` rows and `ReportBlock.config` values are gone if 0010 ran. Restore from Postgres backup if needed (Hetzner PG backups are TBD — confirm with infra).
4. If backup unavailable: re-run `seed_demo` to regenerate demo data. For real client data, escalate.
```

- [ ] **Step 2: Commit**

```bash
git add docs/DEPLOY.md
git commit -m "docs(deploy): document DEV-116 destructive migration + rollback path"
```

### Task 7.3: Update README if needed

**Files:**
- Modify: `README.md` (si menciona `ReportBlock.config` o bloques JSON)

- [ ] **Step 1: Check README**

```bash
grep -n "ReportBlock\|config\|JSON" README.md | head -20
```

- [ ] **Step 2: Update if needed**

Si el README describe el modelo de bloques como JSON-config, actualizarlo a typed blocks. Si no lo menciona, skippear este task.

- [ ] **Step 3: Commit (si hubo cambios)**

```bash
git add README.md
git commit -m "docs(readme): reflect typed block model post-DEV-116"
```

---

## Final verification

- [ ] **Step 1: Full backend suite with coverage (dim 1)**

```bash
docker compose exec -T backend pytest backend/tests/unit/ -q --cov=apps.reports --cov-report=term-missing
```
Expected: todos pasan. Coverage `apps.reports.models.blocks.*` ≥85%. Admin y serializers ≥80% (spec dim 1 target).

Si coverage bajo target, agregar tests para los paths faltantes antes de mergear.

- [ ] **Step 2: Frontend typecheck + lint**

```bash
cd frontend && npm run typecheck && npm run lint
```
Expected: sin errores.

- [ ] **Step 3: E2E smoke (full)**

```bash
cd frontend && npm run test:e2e:smoke
```
Expected: 15/16 passed, 1 skipped (expired cookie — pre-existente).

- [ ] **Step 4: Test battery (unified command)**

```bash
cd frontend && npm run test:battery
```
Expected: all green.

- [ ] **Step 5: Manual smoke in browser**

- Login con `belen.rizzo@balanz.com` / `balanz2026`.
- Navegá a un reporte completo (Educación Marzo).
- Verificar que los 11 bloques aparecen y renderizan correctamente.
- Admin de Django: `/admin/reports/report/<id>/change/` — verificar que el "Add another block" dropdown aparece con los 6 subtypes.

- [ ] **Step 6: Check file sizes (complexity budget)**

```bash
find backend/apps/reports/ -name "*.py" -exec wc -l {} + | sort -n | tail -10
```
Expected: todos <300 líneas.

- [ ] **Step 7: Verify CI passes (dim 13)**

```bash
git push -u origin dzacharias/dev-116-typed-blocks-refactor
```

Esperar a que `.github/workflows/test.yml` corra en GitHub Actions. Verificar:
- Job `backend`: pytest passes.
- Job `frontend`: typecheck + build pass.
- Job `e2e-smoke`: Playwright passes (depende de `backend` + `frontend`).

Si algún job falla:

```bash
gh run list --branch dzacharias/dev-116-typed-blocks-refactor --limit 5
gh run view <run-id> --log-failed
```

Arreglar antes de abrir PR.

- [ ] **Step 8: Push + PR**

```bash
git push -u origin dzacharias/dev-116-typed-blocks-refactor
gh pr create --title "DEV-116: typed blocks refactor (multi-table inheritance + django-polymorphic)" --body "$(cat <<'EOF'
## Summary

- Refactor `ReportBlock` from `type + config: JSONField` to multi-table inheritance with 6 typed subtypes.
- Eliminate `ReportMetric`, YoY, Q1 rollup, follower_snapshots aggregations.
- Admin editable by non-technical operators (Euge) via `django-polymorphic`.

## Spec / Plan

- Spec: `docs/superpowers/specs/2026-04-22-dev-116-typed-blocks-refactor-design.md`
- Plan: `docs/superpowers/plans/2026-04-22-dev-116-typed-blocks-refactor.md`

## Test Plan

- [x] Backend unit tests: `pytest backend/tests/unit/` — all green
- [x] Frontend typecheck: `npm run typecheck` — clean
- [x] E2E smoke: `npm run test:e2e:smoke` — 15/16 passed (1 skipped pre-existente)
- [x] Manual smoke admin + viewer

## Quality dimensions

See spec sections "Non-functional requirements" — covers security, observability, git strategy, docs updates, CI/CD.

QUALITY_SCORE.md updated: reports domain B → A.

🤖 Generated with [Claude Code](https://claude.com/claude-code)
EOF
)"
```

---

## Post-merge

- [ ] **Update DEV-111 scope** (Metricool mapper) en Linear: scope cambia de "determinístico" a "AI-mediado" ahora que los blocks son tipados.
- [ ] **DEV-117** sigue pendiente — arrancar discovery de reportes reales.
- [ ] **DEV-118** (Templates) — el clonado polimórfico es más fácil ahora.

## Coverage de entropy dimensions

- **Dim 1 (Test Coverage):** Phase 2 tests por subtipo, Phase 4 integration + prefetch, Phase 5 seed tests. Coverage target >85%.
- **Dim 2 (DRY):** Phase 1 extrae choices.py; Phase 2 mantiene child tables separadas (spec decisión #2).
- **Dim 3 (Boundaries):** Phase 4 serializer + view prefetches; API contract section del spec documentada.
- **Dim 4 (Docs/Complexity):** Phase 2.6 split en módulos <200 líneas; Phase 7.1 QUALITY_SCORE update.
- **Dim 5 (Principles):** Referencias a P2/P4/P10 en spec y plan.
- **Dim 6 (Design patterns):** MTI + PolymorphicSerializer son patterns estándar.
- **Dim 7 (Security):** Tenant scoping vía Report FK preservado; `full_clean()` en save.
- **Dim 8 (Git Health):** ~10 commits atómicos, mensajes estructurados.
- **Dim 9 (Testability):** Factories + fixtures; admin tests via Django Client.
- **Dim 10 (Observability):** Migración 0009 y 0010 logean; errors del serializer logean con context.
- **Dim 11 (Frontend Quality):** DTOs tipados, typecheck, renderers <200 líneas.
- **Dim 12 (Repo Hygiene):** Phase 7 QUALITY_SCORE + README; plan file queda archivado.
- **Dim 13 (CI/CD):** migrations corren en CI via pytest-django; deploy-on-push a development funciona sin cambios; rollback doc en spec.
