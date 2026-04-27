# Sections + Widgets Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reemplazar el actual modelo flat `Report → Block` por una jerarquía `Report → Section → Widget`, donde la **Section** es el contenedor de presentación con pill + layout, y el **Widget** es la unidad atómica de contenido (tabla, chart, imagen, etc.).

**Architecture:** Section es el contenedor (un pill, un `layout` de 3 valores: stack/columns_2/columns_3). Widget es polimórfico (igual patrón que `ReportBlock` actual, vía django-polymorphic) y vive bajo una Section. Los widgets son agnósticos al pill — el pill vive en la Section. Color rotation del pill se calcula desde `Section.order` (cycling mint → pink → yellow → white). El frontend separa render en dos niveles: `SectionRenderer` (pill + grid CSS por layout) → `WidgetRenderer` (dispatcher polimórfico por widget type). Reseed completo, sin data migration (no hay producción).

**Tech Stack:** Django 5 + django-polymorphic + DRF, PostgreSQL 15, Next.js 14 App Router, openpyxl, pytest, Playwright, docker-compose.

**Pre-condiciones confirmadas:**
- Reseed válido: `flush + migrate + seed_demo`. No hay data productiva.
- `ReportTemplate` NO existe en código todavía (solo está como memoria de DEV-118). No se toca en este plan; cuando se implemente DEV-118 partirá del nuevo modelo.

---

## Diseño final

**Section:**
| Campo | Tipo | Notas |
|---|---|---|
| `report` | FK Report | `related_name="sections"` |
| `order` | PositiveInt | unique-together con `report` |
| `title` | CharField(200, blank=True) | pill; `""` = sin pill |
| `layout` | CharField(choices=Layout) | default `stack` |
| `instructions` | TextField(blank=True) | AI hint a nivel section |
| `created_at` / `updated_at` | DateTime | auto |

`Section.Layout`:
- `stack` (default) — apilado vertical, cada widget 100% width.
- `columns_2` — grid 2 col; cada widget 50%, mobile collapsa a 100%.
- `columns_3` — grid 3 col; cada widget 33%, mobile collapsa a 100%.

**Widget (base polimórfico, mismo patrón que actual `ReportBlock`):**
| Campo | Tipo | Notas |
|---|---|---|
| `section` | FK Section | `related_name="widgets"` |
| `order` | PositiveInt | unique-together con `section` |
| `title` | CharField(200, blank=True) | subtítulo opcional dentro del widget |
| `instructions` | TextField(blank=True) | AI hint a nivel widget |
| `created_at` / `updated_at` | DateTime | auto |

**8 Widget subtypes:**

| Widget | Campos extra | Items hijos |
|---|---|---|
| `TextWidget` | `body: TextField` | — |
| `ImageWidget` | `image: ImageField`, `image_alt: Char(200)`, `caption: Text(blank)` | — |
| `TextImageWidget` | `body: TextField`, `columns: SmallInt(1\|2\|3)`, `image_position: Char(left\|right\|top)`, `image: ImageField(blank,null)`, `image_alt: Char(300)` | — |
| `KpiGridWidget` | — | `KpiTile` (label, value, unit, period_comparison, period_comparison_label, order) |
| `TableWidget` | `show_total: Bool` | `TableRow` (order, is_header, cells: JSON) |
| `ChartWidget` | `chart_type: Char(bar\|line)`, `network: Char(Network, null/blank)` | `ChartDataPoint` (label, value, order) |
| `TopContentsWidget` | `network: Char(Network, null/blank)`, `period_label: Char(60)` | `TopContentItem` (order, thumbnail, caption, post_url, source_type, views/likes/comments/shares/saves) |
| `TopCreatorsWidget` | `network: Char(Network, null/blank)`, `period_label: Char(60)` | `TopCreatorItem` (order, thumbnail, handle, post_url, views/likes/comments/shares) |

Notas:
- `TextWidget` es **nuevo** — antes los textos puros se hacían con `TextImageBlock` sin imagen.
- `ImageWidget`/`TextImageWidget` mantienen sus particularidades visuales (TextImage tiene su layout de columnas + image_position propios; Image renderea card simple). Se mantienen como widgets distintos porque su shape de render difiere.
- `TableWidget` ya no tiene `title` (subió al base) ni `network` (se elimina; era hint para fetcher AI, ahora vive en `Section.instructions` o se infiere del `Section.title`).
- `ChartWidget` ya no tiene `description` (era una frase descriptiva al lado del chart; reemplazable por un `TextWidget` previo en la misma section).
- `KpiGridWidget` ya no tiene `title` (subió al base).
- `TopContentsWidget`/`TopCreatorsWidget` ya no tienen `limit` (el operador setea `Section.instructions` con "traé los 6 más altos", o crea solo 6 items en seed/admin).
- `KpiTile`, `ChartDataPoint`, `TopContentItem`, `TopCreatorItem` se mantienen idénticos (solo cambia el FK al parent).
- `TableRow` se mantiene idéntico — solo cambia el FK de `table_block` a `widget` (apuntando al `TableWidget`). El campo se llama `widget` para consistencia (no `table_widget`).

**Color rotation del pill (FE):**
```ts
const PILL_COLORS = ["mint", "pink", "yellow", "white"];
const colorClass = PILL_COLORS[(section.order - 1) % PILL_COLORS.length];
```
Se aplica como `<span className={\`pill-title \${colorClass}\`}>` en el `SectionRenderer`. Asume `Section.order >= 1`.

**Importer Excel — schema nuevo:**
- Hoja `Sections`: `nombre`, `title`, `layout`, `order`, `instructions` (1 row por section).
- Hojas por widget type, todas referenciando `section_nombre` (no más `nombre` de bloque):
  - `Texts`, `Images`, `TextImages`, `KpiGrids`, `Tables`, `Charts`, `TopContents`, `TopCreators`.
- La hoja `Reporte` mantiene los KV (kind, fecha_inicio, fecha_fin, título, intro, conclusiones) pero **pierde el Layout** (que vivía como tabla orden→nombre). El orden de sections lo define la columna `order` en la hoja `Sections`.
- Nombre de section: mismo patrón `^[a-z0-9_-]{1,60}$`, único en el archivo.

---

## File Structure

**Crear (backend):**
- `backend/apps/reports/models/section.py` — `Section` model con choices `Layout`.
- `backend/apps/reports/models/widgets/__init__.py` — package docstring.
- `backend/apps/reports/models/widgets/base_widget.py` — `Widget` polymorphic base.
- `backend/apps/reports/models/widgets/text.py` — `TextWidget`.
- `backend/apps/reports/models/widgets/image.py` — `ImageWidget`.
- `backend/apps/reports/models/widgets/text_image.py` — `TextImageWidget`.
- `backend/apps/reports/models/widgets/kpi_grid.py` — `KpiGridWidget` + `KpiTile`.
- `backend/apps/reports/models/widgets/table.py` — `TableWidget` + `TableRow`.
- `backend/apps/reports/models/widgets/chart.py` — `ChartWidget` + `ChartDataPoint`.
- `backend/apps/reports/models/widgets/top_contents.py` — `TopContentsWidget` + `TopContentItem`.
- `backend/apps/reports/models/widgets/top_creators.py` — `TopCreatorsWidget` + `TopCreatorItem`.
- `backend/apps/reports/migrations/0022_sections_widgets.py` — auto-generada (CreateModel para Section, Widget base, 8 widget subtypes, 4 item models).
- `backend/apps/reports/migrations/0023_drop_blocks.py` — auto-generada (DeleteModel para los 8 blocks + 4 row/item models del modelo viejo).
- `backend/tests/unit/sections/__init__.py`
- `backend/tests/unit/sections/test_section_model.py` — Section creation, layout choices, ordering.
- `backend/tests/unit/sections/test_widget_polymorphic.py` — Widget polymorphic dispatch, ordering por section.
- `backend/tests/unit/sections/test_widget_serializers.py` — DRF dispatch por widget type.
- `backend/tests/unit/sections/test_seed_demo.py` — verifica que el seed produce sections con widgets esperados.

**Crear (frontend):**
- `frontend/app/reports/[id]/widgets/WidgetRenderer.tsx` — dispatcher polimórfico por widget type.
- `frontend/app/reports/[id]/widgets/TextWidget.tsx`
- `frontend/app/reports/[id]/widgets/ImageWidget.tsx`
- `frontend/app/reports/[id]/widgets/TextImageWidget.tsx`
- `frontend/app/reports/[id]/widgets/KpiGridWidget.tsx`
- `frontend/app/reports/[id]/widgets/TableWidget.tsx`
- `frontend/app/reports/[id]/widgets/ChartWidget.tsx`
- `frontend/app/reports/[id]/widgets/TopContentsWidget.tsx`
- `frontend/app/reports/[id]/widgets/TopCreatorsWidget.tsx`
- `frontend/app/reports/[id]/sections/SectionRenderer.tsx` — pill + grid layout + iter widgets.

**Modificar (backend):**
- `backend/apps/reports/models/__init__.py` — exportar Section + Widget + subtypes; sacar imports legacy.
- `backend/apps/reports/serializers.py` — reescribir: SectionSerializer + WidgetSerializer dispatcher + 8 widget serializers; sacar BlockSerializer dispatcher legacy.
- `backend/apps/reports/admin.py` — reescribir: SectionAdmin con WidgetInline polymorphic; standalone WidgetAdmin; sacar BlockAdmin legacy.
- `backend/apps/reports/views.py` — actualizar prefetch_related.
- `backend/apps/reports/importers/schema.py` — reescribir headers.
- `backend/apps/reports/importers/excel_parser.py` — reescribir parser.
- `backend/apps/reports/importers/excel_writer.py` — reescribir Instrucciones + skeleton.
- `backend/apps/reports/importers/excel_exporter.py` — reescribir populators.
- `backend/apps/reports/importers/builder.py` — reescribir builders.
- `backend/apps/reports/importers/parsed.py` — adaptar a Section+Widget si necesario.
- `backend/apps/tenants/management/commands/seed_demo.py` — reescribir todos los `_seed_blocks_*` para emitir Sections + Widgets.
- `frontend/lib/api.ts` — reescribir tipos: SectionDto + WidgetDto union + 8 widget DTOs.
- `frontend/app/reports/[id]/page.tsx` — iterar `report.sections` en vez de `report.blocks`.
- `backend/apps/llm/seed/parse_pdf_report.md` — actualizar el LLM seed prompt al nuevo schema.
- Tests existentes que asserten sobre `Block`/`block.type` — adaptar a `Widget`/`widget.type`.

**Borrar (backend):**
- `backend/apps/reports/models/blocks/` — directorio completo (8 archivos: base_block, text_image, image, kpi_grid, table, chart, top_contents, top_creators).
- `backend/tests/unit/blocks/` — directorio completo (test_*_block.py × 8 + test_admin_polymorphic.py + test_polymorphic_serializer.py + test_polymorphic_prefetch.py + test_report_block_base.py + test_legacy_models_gone.py + test_tenant_scoping.py).

**Borrar (frontend):**
- `frontend/app/reports/[id]/blocks/` — directorio completo (BlockRenderer + 7 *Block.tsx).

**Preservar:**
- `backend/apps/reports/models/report.py` — `Report` model intacto.
- `backend/apps/reports/models/follower_snapshot.py` — `BrandFollowerSnapshot`.
- `backend/apps/reports/models/attachments.py` — `ReportAttachment`.
- `backend/apps/reports/choices.py` — `Network`, `SourceType`. Siguen vivos (los usan widgets nuevos).
- `backend/apps/reports/validators.py` — `validate_image_size`, `validate_image_mimetype`.
- `frontend/app/reports/[id]/components/` — `BarChartMini`, `LineChartMini`, `KpiTile`, `ContentItemCard`, `CreatorItemCard` (componentes auxiliares; los nuevos widgets los importan).
- `frontend/app/reports/[id]/sections/HeaderSection.tsx` — el header del reporte (no es una "Section" del modelo, es header de la página).
- `frontend/app/reports/[id]/sections/ConclusionsSection.tsx` — conclusions section (idem).

---

## Task 1: Modelo `Section` + `Widget` base

**Files:**
- Create: `backend/apps/reports/models/section.py`
- Create: `backend/apps/reports/models/widgets/__init__.py`
- Create: `backend/apps/reports/models/widgets/base_widget.py`
- Modify: `backend/apps/reports/models/__init__.py`
- Test: `backend/tests/unit/sections/__init__.py` (empty)
- Test: `backend/tests/unit/sections/test_section_model.py`
- Migration: `backend/apps/reports/migrations/0022_sections_widgets.py` (auto, parcial — solo Section + Widget base)

- [ ] **Step 1: Crear `Section` model**

Crear `backend/apps/reports/models/section.py`:

```python
"""Section — contenedor de presentación de un Report.

Una Section tiene un pill (título visual) y un layout que define cómo
acomodar sus widgets. Color rotation del pill se calcula en frontend
desde `order` (mint → pink → yellow → white).
"""
from django.db import models


class Section(models.Model):
    class Layout(models.TextChoices):
        STACK = "stack", "Stack vertical"
        COLUMNS_2 = "columns_2", "2 columnas"
        COLUMNS_3 = "columns_3", "3 columnas"

    report = models.ForeignKey(
        "reports.Report", on_delete=models.CASCADE, related_name="sections",
    )
    order = models.PositiveIntegerField(db_index=True)
    title = models.CharField(
        max_length=200, blank=True,
        help_text="Pill title arriba de la sección. Vacío = sin pill.",
    )
    layout = models.CharField(
        max_length=16, choices=Layout.choices, default=Layout.STACK,
        help_text="Cómo acomoda sus widgets. Stack = vertical full-width. "
                  "Columns_2/3 = grid responsive (collapsa a 1 col en mobile).",
    )
    instructions = models.TextField(
        blank=True,
        help_text="Texto libre para guiar al AI o al operador. No se rendea.",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = "reports"
        ordering = ["report", "order"]
        indexes = [models.Index(fields=["report", "order"])]
        constraints = [
            models.UniqueConstraint(
                fields=["report", "order"],
                name="uniq_section_order_per_report",
            ),
        ]

    def __str__(self):
        return f"{self.report_id} · Section #{self.order}: {self.title or '(sin título)'}"
```

- [ ] **Step 2: Crear `Widget` polymorphic base**

Crear `backend/apps/reports/models/widgets/__init__.py`:

```python
"""Widgets — unidades atómicas de contenido dentro de una Section.

Polimórficos vía django-polymorphic. Cada subtipo aporta sus campos.
La base define lo compartido: section FK, order, title (subtítulo
opcional dentro del widget), instructions (AI hint), timestamps.
"""
```

Crear `backend/apps/reports/models/widgets/base_widget.py`:

```python
"""Widget polymorphic base."""
from django.db import models
from polymorphic.models import PolymorphicModel


class Widget(PolymorphicModel):
    section = models.ForeignKey(
        "reports.Section", on_delete=models.CASCADE, related_name="widgets",
    )
    order = models.PositiveIntegerField(db_index=True)
    title = models.CharField(
        max_length=200, blank=True,
        help_text="Subtítulo opcional dentro del widget (no es el pill — el "
                  "pill vive en la Section). Renderizado depende del widget.",
    )
    instructions = models.TextField(
        blank=True,
        help_text="Texto libre para guiar al AI o al operador. No se rendea.",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = "reports"
        ordering = ["section", "order"]
        indexes = [models.Index(fields=["section", "order"])]
        constraints = [
            models.UniqueConstraint(
                fields=["section", "order"],
                name="uniq_widget_order_per_section",
            ),
        ]

    def __str__(self):
        return f"{self.section_id} · {type(self).__name__} #{self.order}"
```

- [ ] **Step 3: Registrar en `models/__init__.py`**

Editar `backend/apps/reports/models/__init__.py`. AÑADIR (no remover nada todavía — los block legacy siguen hasta Task 8):

```python
from .section import Section  # noqa: F401
from .widgets.base_widget import Widget  # noqa: F401
```

- [ ] **Step 4: Escribir tests**

Crear `backend/tests/unit/sections/__init__.py` vacío.

Crear `backend/tests/unit/sections/test_section_model.py`:

```python
"""Tests del modelo Section."""
import pytest

from apps.reports.models import Section
from apps.reports.tests.factories import make_report


@pytest.mark.django_db
def test_section_can_be_created_with_pill_and_layout():
    report = make_report()
    s = Section.objects.create(
        report=report, order=1, title="KPIs del mes",
        layout=Section.Layout.STACK,
    )
    assert s.report_id == report.id
    assert s.title == "KPIs del mes"
    assert s.layout == "stack"


@pytest.mark.django_db
def test_section_default_layout_is_stack():
    report = make_report()
    s = Section.objects.create(report=report, order=1)
    assert s.layout == Section.Layout.STACK


@pytest.mark.django_db
def test_section_supports_columns_layouts():
    report = make_report()
    Section.objects.create(report=report, order=1, layout=Section.Layout.COLUMNS_2)
    Section.objects.create(report=report, order=2, layout=Section.Layout.COLUMNS_3)
    layouts = list(Section.objects.filter(report=report).values_list("layout", flat=True))
    assert "columns_2" in layouts
    assert "columns_3" in layouts


@pytest.mark.django_db
def test_section_order_is_unique_per_report():
    from django.db import IntegrityError, transaction
    report = make_report()
    Section.objects.create(report=report, order=1)
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            Section.objects.create(report=report, order=1)


@pytest.mark.django_db
def test_section_title_is_optional():
    report = make_report()
    s = Section.objects.create(report=report, order=1)  # sin title
    assert s.title == ""
```

- [ ] **Step 5: Generar migración**

Run: `docker compose exec backend python manage.py makemigrations reports --name sections_widgets`
Expected: crea `0022_sections_widgets.py` con `CreateModel(Section)` y `CreateModel(Widget)`.

- [ ] **Step 6: Aplicar migración**

Run: `docker compose exec backend python manage.py migrate reports`
Expected: `Applying reports.0022_sections_widgets... OK`

- [ ] **Step 7: Correr tests**

Run: `docker compose exec backend pytest backend/tests/unit/sections/test_section_model.py -v`
Expected: 5 passed.

- [ ] **Step 8: Commit**

```bash
git add backend/apps/reports/models/section.py \
        backend/apps/reports/models/widgets/__init__.py \
        backend/apps/reports/models/widgets/base_widget.py \
        backend/apps/reports/models/__init__.py \
        backend/apps/reports/migrations/0022_sections_widgets.py \
        backend/tests/unit/sections/__init__.py \
        backend/tests/unit/sections/test_section_model.py
git commit -m "feat(reports): add Section + Widget polymorphic base"
```

---

## Task 2: Widget subtypes — los 7 (Text, Image, TextImage, KpiGrid, Table, Chart, TopContents, TopCreators)

**Files:**
- Create: `backend/apps/reports/models/widgets/text.py`
- Create: `backend/apps/reports/models/widgets/image.py`
- Create: `backend/apps/reports/models/widgets/text_image.py`
- Create: `backend/apps/reports/models/widgets/kpi_grid.py`
- Create: `backend/apps/reports/models/widgets/table.py`
- Create: `backend/apps/reports/models/widgets/chart.py`
- Create: `backend/apps/reports/models/widgets/top_contents.py`
- Create: `backend/apps/reports/models/widgets/top_creators.py`
- Modify: `backend/apps/reports/models/__init__.py`
- Test: `backend/tests/unit/sections/test_widget_polymorphic.py`
- Migration: `backend/apps/reports/migrations/0022_sections_widgets.py` (regenerar incluyendo widgets) — o crear `0023_widget_subtypes.py` separada.

Decisión: regenerar `0022` para incluir todos los widgets en una sola migración. Es más limpio (un solo "schema add" en vez de dos).

- [ ] **Step 1: Crear `TextWidget`**

`backend/apps/reports/models/widgets/text.py`:

```python
"""TextWidget — bloque de texto puro (markdown)."""
from django.db import models

from .base_widget import Widget


class TextWidget(Widget):
    body = models.TextField(blank=True)

    class Meta:
        app_label = "reports"
        verbose_name = "Text Widget"
        verbose_name_plural = "Text Widgets"
```

- [ ] **Step 2: Crear `ImageWidget`**

`backend/apps/reports/models/widgets/image.py`:

```python
"""ImageWidget — imagen sola con alt + caption opcional."""
from django.db import models

from apps.reports.validators import validate_image_mimetype, validate_image_size

from .base_widget import Widget


class ImageWidget(Widget):
    image = models.ImageField(
        upload_to="image_widgets/%Y/%m/",
        validators=[validate_image_size, validate_image_mimetype],
    )
    image_alt = models.CharField(max_length=200, blank=True)
    caption = models.TextField(
        blank=True,
        help_text="Se renderea debajo de la imagen, separado por una línea. "
                  "Si está vacío, esa sección se oculta.",
    )

    class Meta:
        app_label = "reports"
        verbose_name = "Image Widget"
        verbose_name_plural = "Image Widgets"
```

- [ ] **Step 3: Crear `TextImageWidget`**

`backend/apps/reports/models/widgets/text_image.py`:

```python
"""TextImageWidget — combo integrado de texto + imagen con layout interno."""
from django.db import models

from apps.reports.validators import validate_image_mimetype, validate_image_size

from .base_widget import Widget


IMAGE_POSITIONS = [
    ("left", "Izquierda"),
    ("right", "Derecha"),
    ("top", "Arriba"),
]

COLUMNS_CHOICES = [(1, "1 columna"), (2, "2 columnas"), (3, "3 columnas")]


class TextImageWidget(Widget):
    body = models.TextField(blank=True)
    columns = models.PositiveSmallIntegerField(
        choices=COLUMNS_CHOICES, default=1,
    )
    image_position = models.CharField(
        max_length=10, choices=IMAGE_POSITIONS, default="top",
    )
    image_alt = models.CharField(max_length=300, blank=True)
    image = models.ImageField(
        upload_to="text_image_widgets/%Y/%m/",
        blank=True, null=True,
        validators=[validate_image_size, validate_image_mimetype],
    )

    class Meta:
        app_label = "reports"
        verbose_name = "Text + Image Widget"
        verbose_name_plural = "Text + Image Widgets"
```

- [ ] **Step 4: Crear `KpiGridWidget` + `KpiTile`**

`backend/apps/reports/models/widgets/kpi_grid.py`:

```python
"""KpiGridWidget + KpiTile — grilla de tiles label/valor."""
from django.db import models

from .base_widget import Widget


class KpiGridWidget(Widget):
    class Meta:
        app_label = "reports"
        verbose_name = "KPI Grid Widget"
        verbose_name_plural = "KPI Grid Widgets"


class KpiTile(models.Model):
    widget = models.ForeignKey(
        KpiGridWidget, on_delete=models.CASCADE, related_name="tiles",
    )
    label = models.CharField(max_length=120)
    value = models.DecimalField(max_digits=16, decimal_places=4)
    unit = models.CharField(
        max_length=10, blank=True,
        help_text="Unidad mostrada al lado del valor (ej. '%', 'm'). Opcional.",
    )
    period_comparison = models.DecimalField(
        max_digits=8, decimal_places=4, null=True, blank=True,
        help_text="Delta % vs periodo anterior. Opcional.",
    )
    period_comparison_label = models.CharField(
        max_length=30, blank=True,
        help_text="Etiqueta del período de comparación (ej. 'vs feb'). Opcional.",
    )
    order = models.PositiveIntegerField()

    class Meta:
        app_label = "reports"
        ordering = ["widget", "order"]
        constraints = [
            models.UniqueConstraint(
                fields=["widget", "order"],
                name="uniq_tile_order_per_kpi_grid_widget",
            ),
        ]
```

- [ ] **Step 5: Crear `TableWidget` + `TableRow`**

`backend/apps/reports/models/widgets/table.py`:

```python
"""TableWidget + TableRow — tabla genérica (PowerPoint)."""
from django.db import models

from .base_widget import Widget


class TableWidget(Widget):
    show_total = models.BooleanField(
        default=False,
        help_text=(
            "Si está activado, el frontend agrega una fila 'Total' al final "
            "sumando las columnas numéricas de las filas no-header."
        ),
    )

    class Meta:
        app_label = "reports"
        verbose_name = "Table Widget"
        verbose_name_plural = "Table Widgets"


class TableRow(models.Model):
    widget = models.ForeignKey(
        TableWidget, on_delete=models.CASCADE, related_name="rows",
    )
    order = models.PositiveIntegerField()
    is_header = models.BooleanField(
        default=False,
        help_text="Si está activado, la fila se renderea con estilo de header.",
    )
    cells = models.JSONField(
        default=list,
        help_text="Lista de strings, una por columna.",
    )

    class Meta:
        app_label = "reports"
        ordering = ["widget", "order"]
        constraints = [
            models.UniqueConstraint(
                fields=["widget", "order"],
                name="uniq_row_order_per_table_widget",
            ),
        ]

    def __str__(self):
        return f"{self.widget_id} #{self.order}: {self.cells}"
```

- [ ] **Step 6: Crear `ChartWidget` + `ChartDataPoint`**

`backend/apps/reports/models/widgets/chart.py`:

```python
"""ChartWidget + ChartDataPoint — gráfico bar/line con sus puntos."""
from django.db import models

from apps.reports.choices import Network

from .base_widget import Widget


CHART_TYPES = [("bar", "Bar"), ("line", "Line")]


class ChartWidget(Widget):
    network = models.CharField(
        max_length=16, choices=Network.choices,
        null=True, blank=True,
        help_text="Metadata hint: red social que el chart representa.",
    )
    chart_type = models.CharField(
        max_length=16, choices=CHART_TYPES, default="bar",
    )

    class Meta:
        app_label = "reports"
        verbose_name = "Chart Widget"
        verbose_name_plural = "Chart Widgets"


class ChartDataPoint(models.Model):
    widget = models.ForeignKey(
        ChartWidget, on_delete=models.CASCADE, related_name="data_points",
    )
    label = models.CharField(max_length=60)
    value = models.DecimalField(max_digits=16, decimal_places=4)
    order = models.PositiveIntegerField()

    class Meta:
        app_label = "reports"
        ordering = ["widget", "order"]
        constraints = [
            models.UniqueConstraint(
                fields=["widget", "order"],
                name="uniq_point_order_per_chart_widget",
            ),
        ]
```

- [ ] **Step 7: Crear `TopContentsWidget` + `TopContentItem`**

`backend/apps/reports/models/widgets/top_contents.py`:

```python
"""TopContentsWidget + TopContentItem — posts/contenidos destacados."""
from django.db import models

from apps.reports.choices import Network, SourceType
from apps.reports.validators import validate_image_mimetype, validate_image_size

from .base_widget import Widget


class TopContentsWidget(Widget):
    network = models.CharField(
        max_length=16, choices=Network.choices,
        null=True, blank=True,
        help_text="Red social de los contenidos destacados.",
    )
    period_label = models.CharField(
        max_length=60, blank=True,
        help_text="Etiqueta de período mostrada en la cabecera, ej. 'febrero'.",
    )

    class Meta:
        app_label = "reports"
        verbose_name = "Top Contenidos Widget"
        verbose_name_plural = "Top Contenidos Widgets"


class TopContentItem(models.Model):
    widget = models.ForeignKey(
        TopContentsWidget, on_delete=models.CASCADE, related_name="items",
    )
    order = models.PositiveIntegerField()
    thumbnail = models.ImageField(
        upload_to="top_content/%Y/%m/",
        blank=True,
        validators=[validate_image_size, validate_image_mimetype],
    )
    caption = models.TextField(blank=True)
    post_url = models.URLField(blank=True)
    source_type = models.CharField(
        max_length=16, choices=SourceType.choices, default=SourceType.ORGANIC,
    )
    views = models.PositiveIntegerField(null=True, blank=True)
    likes = models.PositiveIntegerField(null=True, blank=True)
    comments = models.PositiveIntegerField(null=True, blank=True)
    shares = models.PositiveIntegerField(null=True, blank=True)
    saves = models.PositiveIntegerField(null=True, blank=True)

    class Meta:
        app_label = "reports"
        ordering = ["widget", "order"]
        constraints = [
            models.UniqueConstraint(
                fields=["widget", "order"],
                name="uniq_item_order_per_top_contents_widget",
            ),
        ]
```

- [ ] **Step 8: Crear `TopCreatorsWidget` + `TopCreatorItem`**

`backend/apps/reports/models/widgets/top_creators.py`:

```python
"""TopCreatorsWidget + TopCreatorItem — creadores destacados."""
from django.db import models

from apps.reports.choices import Network
from apps.reports.validators import validate_image_mimetype, validate_image_size

from .base_widget import Widget


class TopCreatorsWidget(Widget):
    network = models.CharField(
        max_length=16, choices=Network.choices,
        null=True, blank=True,
        help_text="Red social de los creadores destacados.",
    )
    period_label = models.CharField(
        max_length=60, blank=True,
        help_text="Etiqueta de período mostrada en la cabecera, ej. 'enero'.",
    )

    class Meta:
        app_label = "reports"
        verbose_name = "Top Creadores Widget"
        verbose_name_plural = "Top Creadores Widgets"


class TopCreatorItem(models.Model):
    widget = models.ForeignKey(
        TopCreatorsWidget, on_delete=models.CASCADE, related_name="items",
    )
    order = models.PositiveIntegerField()
    thumbnail = models.ImageField(
        upload_to="top_creators/%Y/%m/",
        blank=True,
        validators=[validate_image_size, validate_image_mimetype],
    )
    handle = models.CharField(
        max_length=120,
        help_text="Handle del creator (ej. '@antoroncatti'). Obligatorio.",
    )
    post_url = models.URLField(blank=True)
    views = models.PositiveIntegerField(null=True, blank=True)
    likes = models.PositiveIntegerField(null=True, blank=True)
    comments = models.PositiveIntegerField(null=True, blank=True)
    shares = models.PositiveIntegerField(null=True, blank=True)

    class Meta:
        app_label = "reports"
        ordering = ["widget", "order"]
        constraints = [
            models.UniqueConstraint(
                fields=["widget", "order"],
                name="uniq_item_order_per_top_creators_widget",
            ),
        ]
```

- [ ] **Step 9: Registrar todos en `models/__init__.py`**

Editar `backend/apps/reports/models/__init__.py`. Añadir bloque de imports nuevos (ANTES del `# Attachments` actual):

```python
from .widgets.text import TextWidget  # noqa: F401
from .widgets.image import ImageWidget  # noqa: F401
from .widgets.text_image import TextImageWidget  # noqa: F401
from .widgets.kpi_grid import KpiGridWidget, KpiTile  # noqa: F401
from .widgets.table import TableWidget, TableRow  # noqa: F401
from .widgets.chart import ChartWidget, ChartDataPoint  # noqa: F401
from .widgets.top_contents import TopContentsWidget, TopContentItem  # noqa: F401
from .widgets.top_creators import TopCreatorsWidget, TopCreatorItem  # noqa: F401
```

Importante: los modelos legacy `KpiTile`, `TableRow`, etc. ya están exportados desde `blocks.*`. Va a haber colisión de nombres. Solución: dropear primero el legacy, o importar con alias.

Decisión: alias temporales. Renombrar los imports legacy en `__init__.py` con `as`:

```python
# Legacy (drop en Task 8):
from .blocks.kpi_grid import KpiGridBlock, KpiTile as _LegacyKpiTile  # noqa: F401
from .blocks.table import TableBlock, TableRow as _LegacyTableRow  # noqa: F401
from .blocks.chart import ChartBlock, ChartDataPoint as _LegacyChartDataPoint  # noqa: F401
from .blocks.top_contents import TopContentsBlock, TopContentItem as _LegacyTopContentItem  # noqa: F401
from .blocks.top_creators import TopCreatorsBlock, TopCreatorItem as _LegacyTopCreatorItem  # noqa: F401
```

Y los nuevos exports sí van con sus nombres canónicos (KpiTile, TableRow, ChartDataPoint, TopContentItem, TopCreatorItem). Cualquier código legacy que use `KpiTile` (legacy) ya rompía la compilación si no se aliasaba — pero como los tests de blocks legacy se borran en Task 8, esto es transitorio.

Alternativa más limpia: hacer Task 8 (drop legacy) ANTES que esta. Pero entonces las migrations 0022 vs 0023 se complican (drop primero crea schema vacío, luego add). Por simplicidad, vamos con los aliases.

- [ ] **Step 10: Generar migración (sobreescribir 0022)**

Borrar el archivo de migración generado en Task 1 (`0022_sections_widgets.py`):
```bash
rm backend/apps/reports/migrations/0022_sections_widgets.py
```

Hacer rollback de la migración aplicada:
```bash
docker compose exec backend python manage.py migrate reports 0021
```

Generar de nuevo:
```bash
docker compose exec backend python manage.py makemigrations reports --name sections_widgets
```

Expected: nueva `0022_sections_widgets.py` con CreateModel para Section, Widget, los 8 widget subtypes, y los 4 item models (KpiTile, TableRow, ChartDataPoint, TopContentItem, TopCreatorItem).

- [ ] **Step 11: Aplicar**

```bash
docker compose exec backend python manage.py migrate reports
```

- [ ] **Step 12: Escribir test del polymorphic dispatch**

`backend/tests/unit/sections/test_widget_polymorphic.py`:

```python
"""Tests del Widget polymorphic dispatch."""
import pytest
from decimal import Decimal

from apps.reports.models import (
    Section, Widget,
    TextWidget, ImageWidget, TextImageWidget,
    KpiGridWidget, KpiTile,
    TableWidget, TableRow,
    ChartWidget, ChartDataPoint,
    TopContentsWidget, TopContentItem,
    TopCreatorsWidget, TopCreatorItem,
)
from apps.reports.tests.factories import make_report


@pytest.fixture
def section():
    report = make_report()
    return Section.objects.create(report=report, order=1, title="Test")


@pytest.mark.django_db
def test_text_widget_can_be_created(section):
    w = TextWidget.objects.create(section=section, order=1, body="Hola")
    assert w.body == "Hola"
    assert w.title == ""


@pytest.mark.django_db
def test_table_widget_with_rows(section):
    w = TableWidget.objects.create(section=section, order=1, show_total=True)
    TableRow.objects.create(widget=w, order=1, is_header=True, cells=["A", "B"])
    TableRow.objects.create(widget=w, order=2, cells=["1", "2"])
    rows = list(w.rows.order_by("order"))
    assert len(rows) == 2
    assert rows[0].is_header is True
    assert rows[1].cells == ["1", "2"]


@pytest.mark.django_db
def test_kpi_grid_with_tiles(section):
    w = KpiGridWidget.objects.create(section=section, order=1, title="KPIs")
    KpiTile.objects.create(
        widget=w, order=1, label="Reach", value=Decimal("100"),
    )
    assert w.tiles.count() == 1
    assert w.tiles.first().label == "Reach"


@pytest.mark.django_db
def test_chart_widget_with_points(section):
    w = ChartWidget.objects.create(section=section, order=1, chart_type="line")
    ChartDataPoint.objects.create(widget=w, order=1, label="Ene", value=Decimal("10"))
    assert w.data_points.count() == 1


@pytest.mark.django_db
def test_top_contents_with_items(section):
    w = TopContentsWidget.objects.create(section=section, order=1, period_label="Marzo")
    TopContentItem.objects.create(widget=w, order=1, caption="Post 1")
    assert w.items.count() == 1


@pytest.mark.django_db
def test_top_creators_with_items(section):
    w = TopCreatorsWidget.objects.create(section=section, order=1, period_label="Marzo")
    TopCreatorItem.objects.create(widget=w, order=1, handle="@flor")
    assert w.items.count() == 1


@pytest.mark.django_db
def test_widget_polymorphic_returns_subtype(section):
    """django-polymorphic devuelve la instancia subtipo automáticamente."""
    TextWidget.objects.create(section=section, order=1, body="x")
    TableWidget.objects.create(section=section, order=2)
    KpiGridWidget.objects.create(section=section, order=3)
    fetched = list(Widget.objects.filter(section=section).order_by("order"))
    assert isinstance(fetched[0], TextWidget)
    assert isinstance(fetched[1], TableWidget)
    assert isinstance(fetched[2], KpiGridWidget)


@pytest.mark.django_db
def test_widget_order_is_unique_per_section(section):
    from django.db import IntegrityError, transaction
    TextWidget.objects.create(section=section, order=1, body="a")
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            TableWidget.objects.create(section=section, order=1)
```

- [ ] **Step 13: Correr tests**

```bash
docker compose exec backend pytest backend/tests/unit/sections/ -v
```
Expected: todos los nuevos tests passed.

- [ ] **Step 14: Commit**

```bash
git add backend/apps/reports/models/widgets/ \
        backend/apps/reports/models/__init__.py \
        backend/apps/reports/migrations/0022_sections_widgets.py \
        backend/tests/unit/sections/test_widget_polymorphic.py
git commit -m "feat(reports): add 8 widget subtypes (Text, Image, TextImage, KpiGrid, Table, Chart, TopContents, TopCreators)"
```

---

## Task 3: Serializers — `SectionSerializer` + `WidgetSerializer` polymorphic dispatcher

**Files:**
- Modify: `backend/apps/reports/serializers.py`
- Test: `backend/tests/unit/sections/test_widget_serializers.py`

- [ ] **Step 1: Escribir el test del dispatcher**

`backend/tests/unit/sections/test_widget_serializers.py`:

```python
"""Tests de la serialización polimórfica de Widgets + Section."""
import pytest
from decimal import Decimal

from apps.reports.models import (
    Section,
    TextWidget, KpiGridWidget, KpiTile,
    TableWidget, TableRow,
    ChartWidget, ChartDataPoint,
    TopContentsWidget, TopContentItem,
)
from apps.reports.serializers import WidgetSerializer, SectionSerializer
from apps.reports.tests.factories import make_report


@pytest.mark.django_db
def test_text_widget_serializes_with_type():
    report = make_report()
    s = Section.objects.create(report=report, order=1, title="Intro")
    w = TextWidget.objects.create(section=s, order=1, title="", body="Hola mundo")
    data = WidgetSerializer(w).data
    assert data["type"] == "TextWidget"
    assert data["body"] == "Hola mundo"
    assert data["title"] == ""


@pytest.mark.django_db
def test_table_widget_serializes_with_rows():
    report = make_report()
    s = Section.objects.create(report=report, order=1)
    w = TableWidget.objects.create(section=s, order=1, title="IG", show_total=True)
    TableRow.objects.create(widget=w, order=1, is_header=True, cells=["A", "B"])
    TableRow.objects.create(widget=w, order=2, cells=["1", "2"])
    data = WidgetSerializer(w).data
    assert data["type"] == "TableWidget"
    assert data["title"] == "IG"
    assert data["show_total"] is True
    assert len(data["rows"]) == 2
    assert data["rows"][0]["is_header"] is True
    assert data["rows"][1]["cells"] == ["1", "2"]


@pytest.mark.django_db
def test_kpi_grid_widget_serializes_with_tiles():
    report = make_report()
    s = Section.objects.create(report=report, order=1)
    w = KpiGridWidget.objects.create(section=s, order=1)
    KpiTile.objects.create(widget=w, order=1, label="Reach", value=Decimal("100"))
    data = WidgetSerializer(w).data
    assert data["type"] == "KpiGridWidget"
    assert len(data["tiles"]) == 1


@pytest.mark.django_db
def test_section_serializes_with_widgets():
    report = make_report()
    s = Section.objects.create(
        report=report, order=1, title="Análisis", layout=Section.Layout.STACK,
    )
    TextWidget.objects.create(section=s, order=1, body="Texto")
    TableWidget.objects.create(section=s, order=2)
    data = SectionSerializer(s).data
    assert data["title"] == "Análisis"
    assert data["layout"] == "stack"
    assert data["order"] == 1
    assert len(data["widgets"]) == 2
    assert data["widgets"][0]["type"] == "TextWidget"
    assert data["widgets"][1]["type"] == "TableWidget"
```

- [ ] **Step 2: Reescribir `backend/apps/reports/serializers.py`**

Read the current file (it has the legacy block serializers). Conservar solo lo que sigue siendo válido (`ReportAttachmentSerializer`) y reescribir el resto. La idea: dropear todo lo de blocks legacy ya que vamos a reemplazarlo. Los block serializers se siguen exportando hasta Task 8 para que otros módulos legacy compilen, pero NO se usan en el `ReportDetailSerializer` (que pasa a usar `sections` en lugar de `blocks`).

Decisión simplificadora: en este task **modificar** el archivo para AGREGAR los nuevos serializers + dispatcher Widget, AGREGAR `SectionSerializer`, y CAMBIAR `ReportDetailSerializer` para que use `sections` en vez de `blocks`. Los serializers de blocks legacy quedan exportados pero nadie los referencia. Task 8 los borra.

Reescribir `backend/apps/reports/serializers.py` completo:

```python
"""Report serializers — post Sections+Widgets refactor.

Estructura: Report → Section[] → Widget[] (polimórfico).
Block legacy serializers se borran en Task 8.
"""
from rest_framework import serializers

from .models import (
    Report, ReportAttachment, Section, Widget,
    TextWidget, ImageWidget, TextImageWidget,
    KpiGridWidget, KpiTile,
    TableWidget, TableRow,
    ChartWidget, ChartDataPoint,
    TopContentsWidget, TopContentItem,
    TopCreatorsWidget, TopCreatorItem,
)


# ---------- Child item / row serializers ----------

class KpiTileSerializer(serializers.ModelSerializer):
    class Meta:
        model = KpiTile
        fields = (
            "label", "value", "unit",
            "period_comparison", "period_comparison_label", "order",
        )


class TableRowSerializer(serializers.ModelSerializer):
    class Meta:
        model = TableRow
        fields = ("order", "is_header", "cells")


class ChartDataPointSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChartDataPoint
        fields = ("label", "value", "order")


class TopContentItemSerializer(serializers.ModelSerializer):
    thumbnail_url = serializers.SerializerMethodField()

    class Meta:
        model = TopContentItem
        fields = (
            "order", "thumbnail_url", "caption", "post_url", "source_type",
            "views", "likes", "comments", "shares", "saves",
        )

    def get_thumbnail_url(self, obj) -> str | None:
        return obj.thumbnail.url if obj.thumbnail else None


class TopCreatorItemSerializer(serializers.ModelSerializer):
    thumbnail_url = serializers.SerializerMethodField()

    class Meta:
        model = TopCreatorItem
        fields = (
            "order", "thumbnail_url", "handle", "post_url",
            "views", "likes", "comments", "shares",
        )

    def get_thumbnail_url(self, obj) -> str | None:
        return obj.thumbnail.url if obj.thumbnail else None


# ---------- Widget subtype serializers ----------

BASE_WIDGET_FIELDS = ("id", "order", "title", "instructions")


class TextWidgetSerializer(serializers.ModelSerializer):
    type = serializers.SerializerMethodField()

    class Meta:
        model = TextWidget
        fields = BASE_WIDGET_FIELDS + ("type", "body")

    def get_type(self, obj) -> str:
        return "TextWidget"


class ImageWidgetSerializer(serializers.ModelSerializer):
    type = serializers.SerializerMethodField()
    image_url = serializers.SerializerMethodField()

    class Meta:
        model = ImageWidget
        fields = BASE_WIDGET_FIELDS + ("type", "image_url", "image_alt", "caption")

    def get_type(self, obj) -> str:
        return "ImageWidget"

    def get_image_url(self, obj) -> str | None:
        return obj.image.url if obj.image else None


class TextImageWidgetSerializer(serializers.ModelSerializer):
    type = serializers.SerializerMethodField()
    image_url = serializers.SerializerMethodField()

    class Meta:
        model = TextImageWidget
        fields = BASE_WIDGET_FIELDS + (
            "type", "body", "columns", "image_position", "image_alt", "image_url",
        )

    def get_type(self, obj) -> str:
        return "TextImageWidget"

    def get_image_url(self, obj) -> str | None:
        return obj.image.url if obj.image else None


class KpiGridWidgetSerializer(serializers.ModelSerializer):
    type = serializers.SerializerMethodField()
    tiles = KpiTileSerializer(many=True, read_only=True)

    class Meta:
        model = KpiGridWidget
        fields = BASE_WIDGET_FIELDS + ("type", "tiles")

    def get_type(self, obj) -> str:
        return "KpiGridWidget"


class TableWidgetSerializer(serializers.ModelSerializer):
    type = serializers.SerializerMethodField()
    rows = TableRowSerializer(many=True, read_only=True)

    class Meta:
        model = TableWidget
        fields = BASE_WIDGET_FIELDS + ("type", "show_total", "rows")

    def get_type(self, obj) -> str:
        return "TableWidget"


class ChartWidgetSerializer(serializers.ModelSerializer):
    type = serializers.SerializerMethodField()
    data_points = ChartDataPointSerializer(many=True, read_only=True)

    class Meta:
        model = ChartWidget
        fields = BASE_WIDGET_FIELDS + ("type", "network", "chart_type", "data_points")

    def get_type(self, obj) -> str:
        return "ChartWidget"


class TopContentsWidgetSerializer(serializers.ModelSerializer):
    type = serializers.SerializerMethodField()
    items = TopContentItemSerializer(many=True, read_only=True)

    class Meta:
        model = TopContentsWidget
        fields = BASE_WIDGET_FIELDS + ("type", "network", "period_label", "items")

    def get_type(self, obj) -> str:
        return "TopContentsWidget"


class TopCreatorsWidgetSerializer(serializers.ModelSerializer):
    type = serializers.SerializerMethodField()
    items = TopCreatorItemSerializer(many=True, read_only=True)

    class Meta:
        model = TopCreatorsWidget
        fields = BASE_WIDGET_FIELDS + ("type", "network", "period_label", "items")

    def get_type(self, obj) -> str:
        return "TopCreatorsWidget"


# ---------- Polymorphic dispatcher ----------

_WIDGET_SERIALIZERS = {
    TextWidget: TextWidgetSerializer,
    ImageWidget: ImageWidgetSerializer,
    TextImageWidget: TextImageWidgetSerializer,
    KpiGridWidget: KpiGridWidgetSerializer,
    TableWidget: TableWidgetSerializer,
    ChartWidget: ChartWidgetSerializer,
    TopContentsWidget: TopContentsWidgetSerializer,
    TopCreatorsWidget: TopCreatorsWidgetSerializer,
}


class WidgetSerializer(serializers.Serializer):
    """Polymorphic dispatcher. django-polymorphic devuelve la instancia subtipo."""

    def to_representation(self, obj):
        serializer_class = _WIDGET_SERIALIZERS.get(type(obj))
        if serializer_class is None:
            return {"id": obj.id, "order": obj.order, "type": type(obj).__name__}
        return serializer_class(obj, context=self.context).data


# ---------- Section ----------

class SectionSerializer(serializers.ModelSerializer):
    widgets = WidgetSerializer(many=True, read_only=True)

    class Meta:
        model = Section
        fields = ("id", "order", "title", "layout", "instructions", "widgets")


# ---------- Top-level Report ----------

class ReportAttachmentSerializer(serializers.ModelSerializer):
    url = serializers.SerializerMethodField()

    class Meta:
        model = ReportAttachment
        fields = ("id", "title", "url", "mime_type", "size_bytes", "kind", "order")

    def get_url(self, obj) -> str | None:
        return obj.file.url if obj.file else None


class ReportDetailSerializer(serializers.ModelSerializer):
    stage_name = serializers.CharField(source="stage.name", read_only=True)
    stage_id = serializers.IntegerField(source="stage.id", read_only=True)
    campaign_name = serializers.CharField(source="stage.campaign.name", read_only=True)
    campaign_id = serializers.IntegerField(source="stage.campaign.id", read_only=True)
    brand_name = serializers.CharField(source="stage.campaign.brand.name", read_only=True)
    display_title = serializers.CharField(read_only=True)
    sections = SectionSerializer(many=True, read_only=True)
    attachments = ReportAttachmentSerializer(many=True, read_only=True)

    class Meta:
        model = Report
        fields = (
            "id", "kind", "period_start", "period_end",
            "title", "display_title", "status", "published_at",
            "intro_text", "conclusions_text",
            "stage_id", "stage_name",
            "campaign_id", "campaign_name", "brand_name",
            "sections", "attachments",
        )
```

- [ ] **Step 3: Correr tests**

```bash
docker compose exec backend pytest backend/tests/unit/sections/test_widget_serializers.py -v
```
Expected: 4 passed.

```bash
docker compose exec backend pytest backend/tests/unit/test_report_detail_serializer.py -v
```
Si falla porque tiene asserts sobre `blocks`, ajustar para que asserte sobre `sections`. Tests legacy de blocks polymorphic se borran en Task 8.

- [ ] **Step 4: Verificar API endpoint**

```bash
docker compose exec backend python manage.py check
```
Expected: 0 issues.

- [ ] **Step 5: Commit**

```bash
git add backend/apps/reports/serializers.py \
        backend/tests/unit/sections/test_widget_serializers.py
git commit -m "feat(reports): SectionSerializer + WidgetSerializer polymorphic dispatcher"
```

---

## Task 4: Admin — `SectionAdmin` + `WidgetAdmin` polymorphic

**Files:**
- Modify: `backend/apps/reports/admin.py`
- Modify: `backend/apps/reports/views.py` (prefetch_related)

- [ ] **Step 1: Reescribir `backend/apps/reports/admin.py`** (preservando lo no relacionado: import flow, attachments inline)

Leer el archivo primero. Luego reescribir todo lo relacionado a blocks → sections/widgets. Estructura objetivo:

- `KpiTileInline`, `TableRowInline`, `ChartDataPointInline`, `TopContentItemInline`, `TopCreatorItemInline` → SortableTabularInline para los nuevos child models con FK = `widget`.
- `WidgetInline` → StackedPolymorphicInline con 8 child inlines (uno por widget type), montado dentro de `SectionAdmin`.
- `SectionAdmin` → SortableAdminBase + PolymorphicInlineSupportMixin + admin.ModelAdmin; lista las sections de cada Report; tiene `WidgetInline` adentro; expone `report`, `order`, `title`, `layout`.
- `SectionInline` → admin.TabularInline para las sections dentro de `ReportAdmin`. Solo `order, title, layout` editables (los widgets se editan navegando a SectionAdmin). O si preferís mostrar tudo, usar StackedInline + nested django-nested-admin (no introducir nueva dep — TabularInline alcanza).
- `ReportAdmin` → mismo que hoy pero con `SectionInline` en vez de `ReportBlockInline`. Mantiene `ReportAttachmentInline`. Mantiene la lógica del importer.
- `WidgetAdmin` → PolymorphicParentModelAdmin standalone para debugging/búsqueda directa de widgets.
- 8 `*WidgetAdmin` standalone child admins, uno por subtype, con sus inline rows correspondientes.

Reescritura:

```python
"""Django admin — Sections + Widgets (post sections-widgets-redesign)."""
import logging

from adminsortable2.admin import SortableAdminBase, SortableTabularInline
from django.contrib import admin, messages
from django.http import HttpResponse, JsonResponse
from django.shortcuts import redirect, render
from django.urls import path, reverse
from polymorphic.admin import (
    PolymorphicInlineSupportMixin,
    PolymorphicParentModelAdmin,
    PolymorphicChildModelAdmin,
    StackedPolymorphicInline,
)

from .importers.excel_exporter import export as export_report_xlsx
from .importers.excel_writer import build_template
from .importers.forms import ImportReportForm
from .importers.import_flow import import_bytes

from .models import (
    Report, ReportAttachment, Section, Widget,
    TextWidget, ImageWidget, TextImageWidget,
    KpiGridWidget, KpiTile,
    TableWidget, TableRow,
    ChartWidget, ChartDataPoint,
    TopContentsWidget, TopContentItem,
    TopCreatorsWidget, TopCreatorItem,
    BrandFollowerSnapshot,
)

logger = logging.getLogger(__name__)


# ---------- Child item / row inlines ----------

class KpiTileInline(SortableTabularInline):
    model = KpiTile
    extra = 0
    fields = ("order", "label", "value", "unit", "period_comparison", "period_comparison_label")
    ordering = ("order",)


class TableRowInline(SortableTabularInline):
    model = TableRow
    extra = 0
    fields = ("order", "is_header", "cells")
    ordering = ("order",)


class ChartDataPointInline(SortableTabularInline):
    model = ChartDataPoint
    extra = 0
    fields = ("order", "label", "value")
    ordering = ("order",)


class TopContentItemInline(SortableTabularInline):
    model = TopContentItem
    extra = 0
    fields = (
        "order", "thumbnail", "caption", "source_type", "post_url",
        "views", "likes", "comments", "shares", "saves",
    )
    ordering = ("order",)


class TopCreatorItemInline(SortableTabularInline):
    model = TopCreatorItem
    extra = 0
    fields = (
        "order", "thumbnail", "handle", "post_url",
        "views", "likes", "comments", "shares",
    )
    ordering = ("order",)


class ReportAttachmentInline(SortableTabularInline):
    model = ReportAttachment
    extra = 0
    fields = ("order", "title", "file", "kind", "mime_type", "size_bytes")
    readonly_fields = ("mime_type", "size_bytes")
    ordering = ("order",)


# ---------- Polymorphic Widget inline (montado dentro de SectionAdmin) ----------

class WidgetInline(StackedPolymorphicInline):
    """Stacked polymorphic inline: el dropdown 'Add another' deja crear cualquier widget."""

    class TextWidgetInline(StackedPolymorphicInline.Child):
        model = TextWidget

    class ImageWidgetInline(StackedPolymorphicInline.Child):
        model = ImageWidget

    class TextImageWidgetInline(StackedPolymorphicInline.Child):
        model = TextImageWidget

    class KpiGridWidgetInline(StackedPolymorphicInline.Child):
        model = KpiGridWidget

    class TableWidgetInline(StackedPolymorphicInline.Child):
        model = TableWidget

    class ChartWidgetInline(StackedPolymorphicInline.Child):
        model = ChartWidget

    class TopContentsWidgetInline(StackedPolymorphicInline.Child):
        model = TopContentsWidget

    class TopCreatorsWidgetInline(StackedPolymorphicInline.Child):
        model = TopCreatorsWidget

    model = Widget
    child_inlines = (
        TextWidgetInline,
        ImageWidgetInline,
        TextImageWidgetInline,
        KpiGridWidgetInline,
        TableWidgetInline,
        ChartWidgetInline,
        TopContentsWidgetInline,
        TopCreatorsWidgetInline,
    )


# ---------- SectionAdmin ----------

@admin.register(Section)
class SectionAdmin(SortableAdminBase, PolymorphicInlineSupportMixin, admin.ModelAdmin):
    list_display = ("report", "order", "title", "layout")
    list_filter = ("layout",)
    search_fields = ("title", "report__title")
    inlines = [WidgetInline]
    fields = ("report", "order", "title", "layout", "instructions")


# ---------- Section inline para ReportAdmin (solo lista; los widgets se editan navegando) ----------

class SectionInline(SortableTabularInline):
    model = Section
    extra = 0
    fields = ("order", "title", "layout")
    ordering = ("order",)
    show_change_link = True  # link para abrir SectionAdmin y editar widgets


# ---------- ReportAdmin ----------

@admin.register(Report)
class ReportAdmin(SortableAdminBase, admin.ModelAdmin):
    list_display = (
        "display_title", "client_col", "brand_col", "campaign_col", "stage",
        "kind", "period_start", "period_end", "status", "published_at",
    )
    list_filter = (
        "status", "kind",
        "stage__campaign__brand__client",
        "stage__campaign__brand",
        "stage__campaign",
    )
    list_select_related = ("stage", "stage__campaign", "stage__campaign__brand", "stage__campaign__brand__client")
    search_fields = (
        "title", "stage__name", "stage__campaign__name",
        "stage__campaign__brand__name",
        "stage__campaign__brand__client__name",
    )

    @admin.display(description="Cliente", ordering="stage__campaign__brand__client__name")
    def client_col(self, obj):
        return obj.stage.campaign.brand.client.name

    @admin.display(description="Brand", ordering="stage__campaign__brand__name")
    def brand_col(self, obj):
        return obj.stage.campaign.brand.name

    @admin.display(description="Campaña", ordering="stage__campaign__name")
    def campaign_col(self, obj):
        return obj.stage.campaign.name

    inlines = [ReportAttachmentInline, SectionInline]
    fieldsets = (
        (None, {
            "fields": (
                "stage", "kind", "period_start", "period_end",
                "title", "status", "published_at",
                "intro_text", "conclusions_text",
            ),
        }),
    )
    actions = ["publish_reports"]

    @admin.action(description="Publicar reportes seleccionados")
    def publish_reports(self, request, queryset):
        from django.utils import timezone
        updated = queryset.filter(status=Report.Status.DRAFT).update(
            status=Report.Status.PUBLISHED, published_at=timezone.now(),
        )
        self.message_user(request, f"{updated} reporte(s) publicado(s).")

    # ---- Importer / Exporter (sin cambios estructurales en este task) ----
    def get_urls(self):
        urls = super().get_urls()
        custom = [
            path(
                "download-template/",
                self.admin_site.admin_view(self.download_template_view),
                name="reports_report_download_template",
            ),
            path(
                "download-example/<int:report_id>/",
                self.admin_site.admin_view(self.download_example_view),
                name="reports_report_download_example",
            ),
            path(
                "import/",
                self.admin_site.admin_view(self.import_view),
                name="reports_report_import",
            ),
            path(
                "import/cascade/<str:level>/",
                self.admin_site.admin_view(self.import_cascade_view),
                name="reports_report_import_cascade",
            ),
        ]
        return custom + urls

    def import_cascade_view(self, request, level: str):
        if not request.user.has_perm("reports.add_report"):
            return JsonResponse({"results": []}, status=403)
        parent = request.GET.get("parent")
        from apps.campaigns.models import Campaign, Stage
        from apps.tenants.models import Brand
        if level == "brand":
            qs = Brand.objects.filter(client_id=parent).order_by("name")
        elif level == "campaign":
            qs = Campaign.objects.filter(brand_id=parent).order_by("name")
        elif level == "stage":
            qs = Stage.objects.filter(campaign_id=parent).order_by("order")
        else:
            return JsonResponse({"results": []}, status=400)
        return JsonResponse({
            "results": [{"id": obj.pk, "text": str(obj)} for obj in qs],
        })

    def download_template_view(self, request):
        if not request.user.has_perm("reports.add_report"):
            return HttpResponse(status=403)
        buf = build_template()
        resp = HttpResponse(
            buf.getvalue(),
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        resp["Content-Disposition"] = 'attachment; filename="reporte-template.xlsx"'
        return resp

    def download_example_view(self, request, report_id: int):
        if not request.user.has_perm("reports.view_report"):
            return HttpResponse(status=403)
        try:
            report = Report.objects.get(pk=report_id)
        except Report.DoesNotExist:
            return HttpResponse(status=404)
        buf = export_report_xlsx(report)
        resp = HttpResponse(
            buf.getvalue(),
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        resp["Content-Disposition"] = (
            f'attachment; filename="reporte-{report.pk}-export.xlsx"'
        )
        return resp

    def import_view(self, request):
        if not request.user.has_perm("reports.add_report"):
            return HttpResponse(status=403)

        import_errors = []
        if request.method == "POST":
            form = ImportReportForm(request.POST, request.FILES, admin_site=self.admin_site)
            if form.is_valid():
                stage = form.cleaned_data["stage"]
                uploaded = form.cleaned_data["file"]
                logger.info(
                    "report_import_started",
                    extra={
                        "user_id": request.user.pk,
                        "stage_id": stage.pk,
                        "filename": uploaded.name,
                        "size": uploaded.size,
                    },
                )
                data = uploaded.read()
                report, import_errors = import_bytes(
                    data, filename=uploaded.name, stage_id=stage.pk,
                )
                if not import_errors and report is not None:
                    messages.success(
                        request,
                        f"Reporte importado como DRAFT (id={report.pk}, "
                        f"{report.sections.count()} sections).",
                    )
                    return redirect(reverse(
                        "admin:reports_report_change", args=[report.pk],
                    ))
                logger.warning(
                    "report_import_validation_failed",
                    extra={
                        "user_id": request.user.pk,
                        "stage_id": stage.pk,
                        "error_count": len(import_errors),
                    },
                )
        else:
            form = ImportReportForm(admin_site=self.admin_site)

        context = {
            **self.admin_site.each_context(request),
            "form": form,
            "import_errors": import_errors,
            "opts": self.model._meta,
        }
        return render(request, "admin/reports/report/import.html", context)


# ---------- Standalone polymorphic Widget admin (debug/búsqueda) ----------

@admin.register(Widget)
class WidgetParentAdmin(PolymorphicParentModelAdmin):
    base_model = Widget
    child_models = (
        TextWidget, ImageWidget, TextImageWidget,
        KpiGridWidget, TableWidget, ChartWidget,
        TopContentsWidget, TopCreatorsWidget,
    )
    list_display = ("section", "order", "title", "polymorphic_ctype")
    list_filter = ("polymorphic_ctype",)
    search_fields = ("title", "section__title", "section__report__title")


class _WidgetChildAdminBase(SortableAdminBase, PolymorphicChildModelAdmin):
    base_model = Widget


@admin.register(TextWidget)
class TextWidgetAdmin(_WidgetChildAdminBase):
    list_display = ("section", "order", "title")


@admin.register(ImageWidget)
class ImageWidgetAdmin(_WidgetChildAdminBase):
    list_display = ("section", "order", "title")


@admin.register(TextImageWidget)
class TextImageWidgetAdmin(_WidgetChildAdminBase):
    list_display = ("section", "order", "title")


@admin.register(KpiGridWidget)
class KpiGridWidgetAdmin(_WidgetChildAdminBase):
    inlines = [KpiTileInline]
    list_display = ("section", "order", "title")


@admin.register(TableWidget)
class TableWidgetAdmin(_WidgetChildAdminBase):
    inlines = [TableRowInline]
    list_display = ("section", "order", "title", "show_total")


@admin.register(ChartWidget)
class ChartWidgetAdmin(_WidgetChildAdminBase):
    inlines = [ChartDataPointInline]
    list_display = ("section", "order", "title", "network", "chart_type")
    list_filter = ("network", "chart_type")


@admin.register(TopContentsWidget)
class TopContentsWidgetAdmin(_WidgetChildAdminBase):
    inlines = [TopContentItemInline]
    list_display = ("section", "order", "title", "network")
    list_filter = ("network",)


@admin.register(TopCreatorsWidget)
class TopCreatorsWidgetAdmin(_WidgetChildAdminBase):
    inlines = [TopCreatorItemInline]
    list_display = ("section", "order", "title", "network")
    list_filter = ("network",)


# ---------- Standalone admins for debugging ----------

@admin.register(BrandFollowerSnapshot)
class BrandFollowerSnapshotAdmin(admin.ModelAdmin):
    list_display = ("brand", "network", "as_of", "followers_count")
    list_filter = ("brand", "network")
    date_hierarchy = "as_of"
```

NOTA: este admin DROPEA todas las registraciones legacy de blocks (`ReportBlockAdmin`, `MetricsTableBlockAdmin`, `TableBlockAdmin`, `ChartBlockAdmin`, etc.). Pero los modelos legacy todavía existen hasta Task 8. Eso significa que el admin va a estar "ciego" a los blocks legacy entre este task y Task 8 — no son visibles en el admin ni se pueden editar. Eso es OK porque seed_demo (Task 6) los va a parar de crear en el mismo task que reseed.

Wait — orden importante. Si SectionAdmin se monta sin que existan Sections en la DB (porque seed sigue creando blocks legacy hasta Task 6), el admin ReportAdmin va a mostrar sections vacías en cada report. Eso es feo pero no rompe.

Decisión: **dejar este Task 4 con el admin nuevo + commit**. La incongruencia visual (admin sin blocks legacy) dura ~1-2 commits. En Task 6 (seed reescrito) y Task 8 (drop legacy) se restablece la coherencia total.

- [ ] **Step 2: Actualizar `views.py` — prefetch_related**

Leer `backend/apps/reports/views.py`. Actualizar el ReportDetailView (o equivalente) para que el prefetch use `sections__widgets__...` en vez de `blocks__...`.

Buscar la query que carga el report con todos sus children. Reemplazar el `prefetch_related` viejo por:

```python
from django.db.models import Prefetch
...
queryset = (
    Report.objects.select_related(
        "stage", "stage__campaign", "stage__campaign__brand",
    ).prefetch_related(
        "attachments",
        Prefetch(
            "sections",
            queryset=Section.objects.prefetch_related(
                # Polymorphic prefetch — django-polymorphic auto-detecta subtypes.
                # Para los widgets con items hijos, agregar prefetch específicos.
                "widgets",
                "widgets__kpigridwidget__tiles",
                "widgets__tablewidget__rows",
                "widgets__chartwidget__data_points",
                "widgets__topcontentswidget__items",
                "widgets__topcreatorswidget__items",
            ).order_by("order"),
        ),
    )
)
```

Si el `Prefetch` con polymorphic no termina de andar, alternativa: usar `.prefetch_related("sections__widgets")` plain y dejar que `WidgetSerializer` haga las queries. Suficiente para empezar; optimizar después.

- [ ] **Step 3: Verificar que el admin abre**

```bash
docker compose exec backend python manage.py check
docker compose exec backend python manage.py runserver 0.0.0.0:8000 &
```

Abrir `http://localhost:8000/admin/` y navegar a Sections (debe estar vacío todavía) y Reports (debe aparecer el SectionInline en cada report).

```bash
# Detener el server
kill %1
```

- [ ] **Step 4: Commit**

```bash
git add backend/apps/reports/admin.py backend/apps/reports/views.py
git commit -m "feat(reports): SectionAdmin + WidgetAdmin polymorphic + ReportAdmin uses SectionInline"
```

---

## Task 5: Frontend — types + widget components + SectionRenderer + page.tsx

**Files:**
- Modify: `frontend/lib/api.ts`
- Create: `frontend/app/reports/[id]/widgets/` (directorio nuevo)
  - `WidgetRenderer.tsx`
  - `TextWidget.tsx`
  - `ImageWidget.tsx`
  - `TextImageWidget.tsx`
  - `KpiGridWidget.tsx`
  - `TableWidget.tsx`
  - `ChartWidget.tsx`
  - `TopContentsWidget.tsx`
  - `TopCreatorsWidget.tsx`
- Create: `frontend/app/reports/[id]/sections/SectionRenderer.tsx`
- Modify: `frontend/app/reports/[id]/page.tsx`

- [ ] **Step 1: Reescribir `frontend/lib/api.ts` (sección de blocks → sections+widgets)**

Leer el archivo. Localizar la zona de `// -- Block subtype DTOs --` y `ReportBlockDto` union. Reemplazar TODO eso (incluyendo los child DTOs como `KpiTileDto`, `TableRowDto`, etc.) por:

```typescript
// -- Child DTOs --

export type KpiTileDto = {
  label: string;
  value: string;
  unit: string;
  period_comparison: string | null;
  period_comparison_label: string;
  order: number;
};

export type TableRowDto = {
  order: number;
  is_header: boolean;
  cells: string[];
};

export type ChartDataPointDto = {
  label: string;
  value: string;
  order: number;
};

export type TopContentItemDto = {
  order: number;
  thumbnail_url: string | null;
  caption: string;
  post_url: string;
  source_type: SourceType;
  views: number | null;
  likes: number | null;
  comments: number | null;
  shares: number | null;
  saves: number | null;
};

export type TopCreatorItemDto = {
  order: number;
  thumbnail_url: string | null;
  handle: string;
  post_url: string;
  views: number | null;
  likes: number | null;
  comments: number | null;
  shares: number | null;
};

// -- Widget subtype DTOs (discriminated union on `type`) --

type BaseWidgetFields = {
  id: number;
  order: number;
  title: string;
  instructions: string;
};

export type TextWidgetDto = BaseWidgetFields & {
  type: "TextWidget";
  body: string;
};

export type ImageWidgetDto = BaseWidgetFields & {
  type: "ImageWidget";
  image_url: string | null;
  image_alt: string;
  caption: string;
};

export type TextImageWidgetDto = BaseWidgetFields & {
  type: "TextImageWidget";
  body: string;
  columns: 1 | 2 | 3;
  image_position: "left" | "right" | "top";
  image_alt: string;
  image_url: string | null;
};

export type KpiGridWidgetDto = BaseWidgetFields & {
  type: "KpiGridWidget";
  tiles: KpiTileDto[];
};

export type TableWidgetDto = BaseWidgetFields & {
  type: "TableWidget";
  show_total: boolean;
  rows: TableRowDto[];
};

export type ChartWidgetDto = BaseWidgetFields & {
  type: "ChartWidget";
  network: Network | null;
  chart_type: "bar" | "line";
  data_points: ChartDataPointDto[];
};

export type TopContentsWidgetDto = BaseWidgetFields & {
  type: "TopContentsWidget";
  network: Network | null;
  period_label: string;
  items: TopContentItemDto[];
};

export type TopCreatorsWidgetDto = BaseWidgetFields & {
  type: "TopCreatorsWidget";
  network: Network | null;
  period_label: string;
  items: TopCreatorItemDto[];
};

export type WidgetDto =
  | TextWidgetDto
  | ImageWidgetDto
  | TextImageWidgetDto
  | KpiGridWidgetDto
  | TableWidgetDto
  | ChartWidgetDto
  | TopContentsWidgetDto
  | TopCreatorsWidgetDto;

// -- Section --

export type SectionLayout = "stack" | "columns_2" | "columns_3";

export type SectionDto = {
  id: number;
  order: number;
  title: string;
  layout: SectionLayout;
  instructions: string;
  widgets: WidgetDto[];
};
```

Y en `ReportDto`, reemplazar el campo `blocks: ReportBlockDto[]` por `sections: SectionDto[]`. Buscar el `export type ReportDto` y modificar ese campo.

Mantener legacy `ReportBlockDto` y subtypes block en el archivo HASTA Task 8 si algún componente los referencia. Si no hay referencias (después de borrar `BlockRenderer.tsx` y los `*Block.tsx`), borrarlos en este Task. Para empezar prudente: dejarlos un commit más, eliminarlos en Task 8.

Decisión: BORRAR todos los `*BlockDto` y `ReportBlockDto` en este task. La consecuencia es que `BlockRenderer.tsx` y `*Block.tsx` (en `frontend/app/reports/[id]/blocks/`) NO compilarán hasta que se borren en Task 8. Pero como `page.tsx` se actualiza en este task para no usarlos, el bundle no los importa y Next.js no compila esos archivos huérfanos.

Procedimiento: borrar bloque legacy de `api.ts`. Los archivos huérfanos en `blocks/` quedan rotos pero como nadie los importa, el dev server los ignora. Task 8 los borra explícitamente.

- [ ] **Step 2: Crear `WidgetRenderer.tsx`**

`frontend/app/reports/[id]/widgets/WidgetRenderer.tsx`:

```tsx
import type { WidgetDto } from "@/lib/api";
import TextWidget from "./TextWidget";
import ImageWidget from "./ImageWidget";
import TextImageWidget from "./TextImageWidget";
import KpiGridWidget from "./KpiGridWidget";
import TableWidget from "./TableWidget";
import ChartWidget from "./ChartWidget";
import TopContentsWidget from "./TopContentsWidget";
import TopCreatorsWidget from "./TopCreatorsWidget";

export default function WidgetRenderer({ widget }: { widget: WidgetDto }) {
  switch (widget.type) {
    case "TextWidget":
      return <TextWidget widget={widget} />;
    case "ImageWidget":
      return <ImageWidget widget={widget} />;
    case "TextImageWidget":
      return <TextImageWidget widget={widget} />;
    case "KpiGridWidget":
      return <KpiGridWidget widget={widget} />;
    case "TableWidget":
      return <TableWidget widget={widget} />;
    case "ChartWidget":
      return <ChartWidget widget={widget} />;
    case "TopContentsWidget":
      return <TopContentsWidget widget={widget} />;
    case "TopCreatorsWidget":
      return <TopCreatorsWidget widget={widget} />;
    default: {
      const _exhaustive: never = widget;
      console.warn("unknown_widget_type", (_exhaustive as { type: string }).type);
      return null;
    }
  }
}
```

- [ ] **Step 3: Crear `TextWidget.tsx`**

```tsx
import type { TextWidgetDto } from "@/lib/api";

export default function TextWidget({ widget }: { widget: TextWidgetDto }) {
  if (!widget.body.trim()) return null;
  return (
    <div className="card" style={{ padding: 24, background: "#fff" }}>
      {widget.title && (
        <h3 style={{ margin: 0, marginBottom: 12, fontSize: 18 }}>
          {widget.title}
        </h3>
      )}
      <div style={{ whiteSpace: "pre-wrap", lineHeight: 1.5 }}>{widget.body}</div>
    </div>
  );
}
```

- [ ] **Step 4: Crear `ImageWidget.tsx`** (port desde `blocks/ImageBlock.tsx`, sin pill — el title queda como subtítulo opcional)

`frontend/app/reports/[id]/widgets/ImageWidget.tsx`:

```tsx
import type { ImageWidgetDto } from "@/lib/api";

export default function ImageWidget({ widget }: { widget: ImageWidgetDto }) {
  if (!widget.image_url) return null;
  return (
    <div className="card" style={{ padding: 0, overflow: "hidden", background: "#fff" }}>
      {widget.title && (
        <h3 style={{ margin: 0, padding: "16px 24px 0", fontSize: 18 }}>
          {widget.title}
        </h3>
      )}
      <img
        src={widget.image_url}
        alt={widget.image_alt}
        style={{ width: "100%", display: "block" }}
      />
      {widget.caption && (
        <div style={{ padding: "12px 24px", borderTop: "1px solid rgba(0,0,0,0.08)", fontSize: 14, color: "rgba(0,0,0,0.7)" }}>
          {widget.caption}
        </div>
      )}
    </div>
  );
}
```

- [ ] **Step 5: Crear `TextImageWidget.tsx`** (port desde `blocks/TextImageBlock.tsx`, sin pill arriba)

`frontend/app/reports/[id]/widgets/TextImageWidget.tsx`:

Leer `frontend/app/reports/[id]/blocks/TextImageBlock.tsx` y portarlo. Cambios:
- `block: TextImageBlockDto` → `widget: TextImageWidgetDto`.
- Borrar `{block.title && <span className="pill-title">...}` (pill ya no se rendea acá; vive en SectionRenderer).
- Si `widget.title` no es vacío, renderizar como `<h3>` opcional dentro del card.
- Mantener el layout interno de `image_position` y `columns`.

Plantilla:

```tsx
import type { TextImageWidgetDto } from "@/lib/api";

export default function TextImageWidget({ widget }: { widget: TextImageWidgetDto }) {
  const hasImage = Boolean(widget.image_url);
  const hasBody = widget.body.trim().length > 0;
  if (!hasImage && !hasBody) return null;

  // Layout interno: si hay imagen, posicionarla según image_position.
  // Si no hay imagen, sólo body (multi-columna si columns > 1).
  const flexDirection =
    widget.image_position === "left" ? "row" :
    widget.image_position === "right" ? "row-reverse" : "column";

  return (
    <div className="card" style={{ padding: 24, background: "var(--chirri-paper, #fffbe9)" }}>
      {widget.title && (
        <h3 style={{ margin: 0, marginBottom: 12, fontSize: 18 }}>
          {widget.title}
        </h3>
      )}
      {hasImage ? (
        <div style={{ display: "flex", flexDirection, gap: 24, alignItems: "stretch" }}>
          {hasBody && (
            <div
              style={{
                flex: 1,
                columnCount: widget.columns,
                columnGap: 24,
                whiteSpace: "pre-wrap",
                lineHeight: 1.5,
              }}
            >
              {widget.body}
            </div>
          )}
          <img
            src={widget.image_url!}
            alt={widget.image_alt}
            style={{ flex: 1, objectFit: "cover", borderRadius: 8, maxWidth: "50%" }}
          />
        </div>
      ) : (
        <div
          style={{
            columnCount: widget.columns,
            columnGap: 24,
            whiteSpace: "pre-wrap",
            lineHeight: 1.5,
          }}
        >
          {widget.body}
        </div>
      )}
    </div>
  );
}
```

- [ ] **Step 6: Crear `KpiGridWidget.tsx`** (port desde `blocks/KpiGridBlock.tsx`)

Leer `frontend/app/reports/[id]/blocks/KpiGridBlock.tsx`. Reemplazar `block` por `widget`, sacar el pill (el title ahora vive en Section), y si `widget.title` no vacío, mostrarlo como `<h3>` opcional. La grilla interna de tiles (que importa `KpiTile.tsx` de `components/`) queda igual.

Plantilla:

```tsx
import type { KpiGridWidgetDto } from "@/lib/api";
import KpiTile from "../components/KpiTile";

export default function KpiGridWidget({ widget }: { widget: KpiGridWidgetDto }) {
  const tiles = [...widget.tiles].sort((a, b) => a.order - b.order);
  if (tiles.length === 0) return null;
  return (
    <div>
      {widget.title && (
        <h3 style={{ margin: 0, marginBottom: 12, fontSize: 18 }}>
          {widget.title}
        </h3>
      )}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))", gap: 16 }}>
        {tiles.map((tile) => <KpiTile key={tile.order} tile={tile} />)}
      </div>
    </div>
  );
}
```

(El grid interno de KpiTiles mantiene side-by-side responsive sin que la Section necesite saberlo.)

- [ ] **Step 7: Portar `TableBlock.tsx` → `TableWidget.tsx`**

Copiar `frontend/app/reports/[id]/blocks/TableBlock.tsx` a `frontend/app/reports/[id]/widgets/TableWidget.tsx`. Cambios mínimos:
- Renombrar import: `TableBlockDto` → `TableWidgetDto`.
- Renombrar parámetro: `block: TableBlockDto` → `widget: TableWidgetDto`.
- Borrar el `<span className="pill-title">{title.toUpperCase()}</span>` y la lógica de `marginTop` asociada al pill (el pill vive en Section ahora).
- Si `widget.title` no es vacío, mostrarlo como `<h3>` arriba de la tabla (subtítulo).
- El resto (auto-format de números/deltas, computeTotals, etc.) queda igual.

- [ ] **Step 8: Portar `ChartBlock.tsx` → `ChartWidget.tsx`**

Copiar `frontend/app/reports/[id]/blocks/ChartBlock.tsx` a `frontend/app/reports/[id]/widgets/ChartWidget.tsx`. Cambios:
- DTO: `ChartBlockDto` → `ChartWidgetDto`.
- Borrar el pill.
- DROPEAR el `description` (ya no existe en el DTO).
- Si `widget.title` no vacío, renderizarlo como `<h3>` arriba del chart.
- El render del chart (BarChartMini / LineChartMini) queda igual.

- [ ] **Step 9: Portar `TopContentsBlock.tsx` → `TopContentsWidget.tsx`**

Copiar y adaptar:
- DTO: `TopContentsBlockDto` → `TopContentsWidgetDto`.
- Borrar el pill (estaba arriba).
- DROPEAR cualquier referencia a `block.limit`.
- Title del widget como `<h3>` opcional.
- El grid de cards (que importa `ContentItemCard.tsx`) queda igual.

- [ ] **Step 10: Portar `TopCreatorsBlock.tsx` → `TopCreatorsWidget.tsx`**

Igual al anterior pero para creators. DTO `TopCreatorsBlockDto` → `TopCreatorsWidgetDto`. Borrar pill + limit.

- [ ] **Step 11: Crear `SectionRenderer.tsx`**

`frontend/app/reports/[id]/sections/SectionRenderer.tsx`:

```tsx
import type { SectionDto } from "@/lib/api";
import WidgetRenderer from "../widgets/WidgetRenderer";

const PILL_COLORS = ["mint", "pink", "yellow", "white"] as const;

function pillColorFor(order: number): string {
  return PILL_COLORS[(order - 1) % PILL_COLORS.length];
}

const LAYOUT_GRID: Record<SectionDto["layout"], React.CSSProperties> = {
  stack: {
    display: "flex",
    flexDirection: "column",
    gap: 24,
  },
  columns_2: {
    display: "grid",
    gridTemplateColumns: "repeat(auto-fit, minmax(360px, 1fr))",
    gap: 24,
  },
  columns_3: {
    display: "grid",
    gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))",
    gap: 16,
  },
};

export default function SectionRenderer({ section }: { section: SectionDto }) {
  const sortedWidgets = [...section.widgets].sort((a, b) => a.order - b.order);
  if (sortedWidgets.length === 0) return null;

  const colorClass = pillColorFor(section.order);

  return (
    <section style={{ marginBottom: 48 }}>
      {section.title && (
        <span className={`pill-title ${colorClass}`}>
          {section.title.toUpperCase()}
        </span>
      )}
      <div
        style={{
          ...LAYOUT_GRID[section.layout],
          marginTop: section.title ? 16 : 0,
        }}
      >
        {sortedWidgets.map((w) => (
          <WidgetRenderer key={w.id} widget={w} />
        ))}
      </div>
    </section>
  );
}
```

- [ ] **Step 12: Actualizar `page.tsx`**

`frontend/app/reports/[id]/page.tsx` — reemplazar la lógica que itera `report.blocks`. Cambios:

1. Cambiar `import BlockRenderer from "./blocks/BlockRenderer";` por `import SectionRenderer from "./sections/SectionRenderer";`.
2. Reemplazar `const kpiIdx = report.blocks.findIndex(...)` y todo el JSX que itera blocks por:

```tsx
{report.sections.length === 0 ? (
  <>
    <ConclusionsSection report={report} />
    <section
      data-testid="report-empty-state"
      style={{
        marginBottom: 48,
        padding: 24,
        border: "2px dashed rgba(0,0,0,0.25)",
        borderRadius: 12,
        color: "rgba(0,0,0,0.65)",
        textAlign: "center",
      }}
    >
      Este reporte aún no tiene contenido cargado.
    </section>
  </>
) : (
  (() => {
    const kpiIdx = report.sections.findIndex((s) =>
      s.widgets.some((w) => w.type === "KpiGridWidget"),
    );
    return (
      <>
        {kpiIdx === -1 && <ConclusionsSection report={report} />}
        {report.sections.map((section, i) => (
          <Fragment key={section.id}>
            <SectionRenderer section={section} />
            {i === kpiIdx && <ConclusionsSection report={report} />}
          </Fragment>
        ))}
      </>
    );
  })()
)}
```

- [ ] **Step 13: Type-check + visual smoke**

```bash
docker compose exec frontend npx tsc --noEmit
```

Pre-existing errors en tests pueden continuar, pero no deben aparecer errores nuevos en `app/reports/[id]/`.

NOTA: el dev server va a fallar si los archivos de `blocks/` siguen importando tipos que dropeamos (`ReportBlockDto`, `MetricsTableBlockDto`, etc.). Como hicimos drop en api.ts, esos archivos están rotos. Para evitar errores de compilación, hacer el cleanup ahora también:

```bash
rm "frontend/app/reports/[id]/blocks/BlockRenderer.tsx"
rm "frontend/app/reports/[id]/blocks/TextImageBlock.tsx"
rm "frontend/app/reports/[id]/blocks/ImageBlock.tsx"
rm "frontend/app/reports/[id]/blocks/KpiGridBlock.tsx"
rm "frontend/app/reports/[id]/blocks/TableBlock.tsx"
rm "frontend/app/reports/[id]/blocks/ChartBlock.tsx"
rm "frontend/app/reports/[id]/blocks/TopContentsBlock.tsx"
rm "frontend/app/reports/[id]/blocks/TopCreatorsBlock.tsx"
rmdir "frontend/app/reports/[id]/blocks"
```

(Si el directorio no está vacío, `rmdir` falla y los archivos restantes hay que mirar.)

- [ ] **Step 14: Commit**

```bash
git add frontend/lib/api.ts \
        "frontend/app/reports/[id]/widgets/" \
        "frontend/app/reports/[id]/sections/SectionRenderer.tsx" \
        "frontend/app/reports/[id]/page.tsx" \
        -- ":(exclude)frontend/app/reports/[id]/blocks/"
git rm -r "frontend/app/reports/[id]/blocks/"
git commit -m "feat(reports): frontend Section + Widget renderers; drop legacy block components"
```

---

## Task 6: Reescribir `seed_demo` para emitir Sections + Widgets

**Files:**
- Modify: `backend/apps/tenants/management/commands/seed_demo.py`
- Modify: `backend/tests/unit/test_seed_demo.py` (ajustar asserts)

**Goal:** Tras este task, el seed produce `Report → Section[] → Widget[]` en lugar de `Report → Block[]`. Visualmente debe verse igual (mismos pills, mismas tablas, mismos KPIs) pero con un nivel adicional de jerarquía.

**Mapeo:**

Cada `Section` corresponde 1:1 con un block legacy actual (mismo title, mismo order). Cada Section contiene UN widget (= equivalente del block actual). Excepción: la section "Contexto del mes" del abril seeder, que era TextImageBlock con título "Contexto del mes" — sigue siendo 1 section + 1 TextImageWidget.

Para el reporte abril (seeder `_seed_all_blocks_layout`):
| order | Section.title | Widget |
|---|---|---|
| 1 | Contexto del mes | TextImageWidget (body + image) |
| 2 | KPIs del mes | KpiGridWidget (4 tiles: reach total, engagement, downloads, click-download) |
| 3 | Mes a mes | TableWidget (header + 3 rows) |
| 4 | Instagram | TableWidget (header + 3 rows) |
| 5 | Posts del mes | TopContentsWidget |
| 6 | Creators del mes | TopCreatorsWidget |
| 7 | Atribución OneLink | TableWidget (header + 3 rows + total) |
| 8 | Followers | ChartWidget (bar) |
| 9 | Engagement rate | ChartWidget (line) |

(Verificar el seed actual y replicar el orden exacto.)

Para el reporte marzo (seeder `_seed_full_layout`): mismo mapping ajustado a las sections que tenga.

- [ ] **Step 1: Leer el seed actual**

```bash
grep -n "MetricsTableBlock\|AttributionTableBlock\|KpiGridBlock\|TableBlock\|ChartBlock\|TextImageBlock\|TopContentsBlock\|TopCreatorsBlock\|ImageBlock" backend/apps/tenants/management/commands/seed_demo.py | head -50
```

Identificar las 2 funciones grandes: `_seed_full_layout` (marzo) y `_seed_all_blocks_layout` (abril).

- [ ] **Step 2: Reemplazar imports**

Editar `backend/apps/tenants/management/commands/seed_demo.py`. En el `from apps.reports.models import (...)`:

REMOVER: `ChartBlock, ChartDataPoint, ImageBlock, KpiGridBlock, KpiTile, TableBlock, TableRow, TextImageBlock, TopContentsBlock, TopContentItem, TopCreatorsBlock, TopCreatorItem`.

AGREGAR:

```python
from apps.reports.models import (
    BrandFollowerSnapshot,
    ChartWidget, ChartDataPoint,
    ImageWidget,
    KpiGridWidget, KpiTile,
    Report, ReportAttachment,
    Section,
    TableWidget, TableRow,
    TextWidget,
    TextImageWidget,
    TopContentsWidget, TopContentItem,
    TopCreatorsWidget, TopCreatorItem,
)
```

- [ ] **Step 3: Reescribir `_seed_full_layout` (marzo)**

Encontrar la función (~línea 569 según grep histórico) y reescribir cada bloque.

Patrón general — reemplazar:

```python
kpi = KpiGridBlock.objects.create(report=report, order=1, title="KPIs del mes")
KpiTile.objects.bulk_create([...])
```

Por:

```python
sec = Section.objects.create(report=report, order=1, title="KPIs del mes", layout=Section.Layout.STACK)
w = KpiGridWidget.objects.create(section=sec, order=1)
KpiTile.objects.bulk_create([
    KpiTile(widget=w, order=1, label="...", value=...),
    ...
])
```

(Notá: `KpiTile.kpi_grid_block` → `KpiTile.widget`. Es el FK renombrado en Task 2.)

Aplicar el mismo patrón a las 4 secciones de tablas:

```python
mtm = TableBlock.objects.create(report=report, order=2, title="Mes a mes")
TableRow.objects.bulk_create([
    TableRow(table_block=mtm, order=1, is_header=True, cells=["Métrica", "Valor", "Δ"]),
    ...
])
```

→

```python
sec = Section.objects.create(report=report, order=2, title="Mes a mes", layout=Section.Layout.STACK)
w = TableWidget.objects.create(section=sec, order=1, show_total=False)
TableRow.objects.bulk_create([
    TableRow(widget=w, order=1, is_header=True, cells=["Métrica", "Valor", "Δ"]),
    ...
])
```

(`TableRow.table_block` → `TableRow.widget`.)

Para Top Contenidos:

```python
tc = TopContentsBlock.objects.create(report=report, order=6, title="Posts del mes", network=Network.INSTAGRAM, period_label="Marzo", limit=6)
```

→

```python
sec = Section.objects.create(report=report, order=6, title="Posts del mes", layout=Section.Layout.STACK)
w = TopContentsWidget.objects.create(section=sec, order=1, network=Network.INSTAGRAM, period_label="Marzo")
```

(Sin `limit`, sin `title` en el widget — el title sube a la Section.)

Para AttributionTable:

```python
attr = AttributionTableBlock.objects.create(report=report, order=8, title="Atribución OneLink", show_total=True)
```

→

```python
sec = Section.objects.create(report=report, order=8, title="Atribución OneLink", layout=Section.Layout.STACK)
TableWidget.objects.create(section=sec, order=1, show_total=True)
# Las rows se cargan en _seed_demo_data, igual que hoy.
```

Para los 3 ChartBlocks (Followers IG line, TikTok bar, X bar):

```python
ig_chart = ChartBlock.objects.create(report=report, order=9, title="Followers", network=Network.INSTAGRAM, chart_type="line", description="...")
ChartDataPoint.objects.bulk_create([...])
```

→

```python
sec = Section.objects.create(report=report, order=9, title="Followers", layout=Section.Layout.STACK)
w = ChartWidget.objects.create(section=sec, order=1, network=Network.INSTAGRAM, chart_type="line")
ChartDataPoint.objects.bulk_create([
    ChartDataPoint(widget=w, order=1, label="ene", value=...),
    ...
])
```

(`ChartDataPoint.chart_block` → `ChartDataPoint.widget`.)

- [ ] **Step 4: Reescribir `_seed_all_blocks_layout` (abril)**

Mismo patrón. Adicionalmente, el primer "TextImageBlock" (Contexto del mes) se vuelve:

```python
sec = Section.objects.create(report=report, order=1, title="Contexto del mes", layout=Section.Layout.STACK)
w = TextImageWidget(
    section=sec, order=1,
    body="Abril fue la primera bajada real...",
    columns=1, image_position="left",
    image_alt="Creator Flor Sosa grabando el reel de abril",
)
source = _pick_image("post")
stable_name = f"textimage-{w.id or 'tmp'}-1{source.suffix}"
with open(source, "rb") as fh:
    w.image.save(stable_name, File(fh), save=False)
w.save()
```

(El stable_name puede usar `w.id` si lo guardás dos veces — primero `w.save()` para tener id, luego `w.image.save(...)` con el id real, luego otro `w.save()`. Patrón actual del seed para imágenes.)

- [ ] **Step 5: Reescribir `_seed_demo_data` para que las rows OneLink se carguen al `TableWidget` correspondiente**

Encontrar el código que hoy dice:

```python
attribution_block = AttributionTableBlock.objects.filter(report=report).first()
...
onelink_block = TableBlock.objects.filter(report=report, title="Atribución OneLink").first()
```

Reemplazar por:

```python
onelink_widget = TableWidget.objects.filter(
    section__report=report,
    section__title="Atribución OneLink",
).first()
if onelink_widget is not None:
    onelink_widget.rows.all().delete()
    TableRow.objects.bulk_create([
        TableRow(widget=onelink_widget, order=1, is_header=True,
                 cells=["Influencer", "Clicks", "Descargas"]),
        *[
            TableRow(
                widget=onelink_widget,
                order=i + 2,
                cells=[handle, str(clicks), str(downloads)],
            )
            for i, (handle, clicks, downloads) in enumerate(onelink_specs)
        ],
    ])
```

Mismo patrón para `contents_block` (TopContents) y `creators_block` (TopCreators):

```python
contents_widget = TopContentsWidget.objects.filter(section__report=report).first()
creators_widget = TopCreatorsWidget.objects.filter(section__report=report).first()
```

(Los items con thumbnails siguen el mismo flujo: `TopContentItem.widget = contents_widget` en lugar de `block`.)

- [ ] **Step 6: Reseed completo**

```bash
docker compose exec backend python manage.py flush --no-input
docker compose exec backend python manage.py migrate
docker compose exec backend python manage.py seed_demo
```

Expected: completa sin errores. Verificar:

```bash
docker compose exec backend python manage.py shell -c "
from apps.reports.models import Report
r = Report.objects.first()
print('sections:', r.sections.count())
for s in r.sections.all().order_by('order'):
    print(f'  {s.order}: {s.title} [{s.layout}] -> {s.widgets.count()} widgets')
    for w in s.widgets.all().order_by('order'):
        print(f'    {w.order}: {type(w).__name__} title={w.title!r}')
"
```

- [ ] **Step 7: Ajustar `test_seed_demo.py`**

Leer `backend/tests/unit/test_seed_demo.py`. Cualquier assert sobre `report.blocks` → `report.sections`. Cualquier creación o assert de `MetricsTableBlock`, `AttributionTableBlock`, `KpiGridBlock`, etc. → equivalente Section + Widget.

```bash
docker compose exec backend pytest backend/tests/unit/test_seed_demo.py -v
```
Expected: PASS.

- [ ] **Step 8: Smoke test del viewer**

Levantar dev stack si no está:
```bash
docker compose up -d
```

Browser: `http://localhost:3000/login` → demo@chirripeppers.com / demo2026 → navegar a un reporte. Verificar:
- Pills aparecen con los títulos correctos.
- Color rotation: el primer pill es mint, el segundo pink, etc.
- KPIs side-by-side dentro del KpiGridWidget.
- Tablas con auto-format y deltas verde/rojo.
- Posts del mes y Creators del mes con sus cards.
- Atribución OneLink con fila Total.

Si algo se ve mal, fix antes de continuar.

- [ ] **Step 9: Commit**

```bash
git add backend/apps/tenants/management/commands/seed_demo.py \
        backend/tests/unit/test_seed_demo.py
git commit -m "feat(reports): seed_demo emits Sections + Widgets"
```

---

## Task 7: Importer — schema + parser + builder + exporter + writer

**Files:**
- Modify: `backend/apps/reports/importers/schema.py`
- Modify: `backend/apps/reports/importers/excel_parser.py`
- Modify: `backend/apps/reports/importers/builder.py`
- Modify: `backend/apps/reports/importers/excel_exporter.py`
- Modify: `backend/apps/reports/importers/excel_writer.py`
- Modify: `backend/apps/reports/importers/parsed.py`
- Modify: `backend/tests/unit/test_excel_writer.py`
- Modify: `backend/tests/unit/test_excel_parser.py`

**Diseño nuevo del XLSX:**

10 hojas:

1. `Instrucciones` — texto explicativo (igual que hoy, actualizado).
2. `Reporte` — KV: tipo, fecha_inicio, fecha_fin, título, intro, conclusiones. SIN tabla Layout (las sections traen su propio order).
3. `Sections` — `nombre`, `title`, `layout`, `order`, `instructions`. Una row por section.
4. `Texts` — `section_nombre`, `widget_orden`, `widget_title`, `body`.
5. `Images` — `section_nombre`, `widget_orden`, `widget_title`, `imagen`, `image_alt`, `caption`.
6. `TextImages` — `section_nombre`, `widget_orden`, `widget_title`, `body`, `imagen`, `image_alt`, `image_position`, `columns`.
7. `KpiGrids` — `section_nombre`, `widget_orden`, `widget_title`, `tile_orden`, `label`, `value`, `unit`, `period_comparison`, `period_comparison_label`.
8. `Tables` — `section_nombre`, `widget_orden`, `widget_title`, `widget_show_total`, `row_orden`, `is_header`, `cell_1` … `cell_8`.
9. `Charts` — `section_nombre`, `widget_orden`, `widget_title`, `widget_network`, `chart_type`, `point_orden`, `point_label`, `point_value`.
10. `TopContents` — `section_nombre`, `widget_orden`, `widget_title`, `widget_network`, `widget_period_label`, `item_orden`, `imagen`, `caption`, `post_url`, `source_type`, `views`, `likes`, `comments`, `shares`, `saves`.
11. `TopCreators` — `section_nombre`, `widget_orden`, `widget_title`, `widget_network`, `widget_period_label`, `item_orden`, `imagen`, `handle`, `post_url`, `views`, `likes`, `comments`, `shares`.

Identificadores:
- `nombre` de section: único en el archivo (`^[a-z0-9_-]{1,60}$`).
- Cada widget pertenece a una `section_nombre` + un `widget_orden` (entero ≥ 1, único dentro de la section).
- Cada item/row pertenece a un widget identificado por `(section_nombre, widget_orden)` + su propio `*_orden`.

- [ ] **Step 1: Reescribir `schema.py`**

Reemplazar todo el contenido por:

```python
"""Schema centralizado del importer/exporter xlsx (post sections-widgets-redesign)."""
from __future__ import annotations

# Sheet names — orden fijo
SHEET_INSTRUCCIONES = "Instrucciones"
SHEET_REPORTE = "Reporte"
SHEET_SECTIONS = "Sections"
SHEET_TEXTS = "Texts"
SHEET_IMAGES = "Images"
SHEET_TEXTIMAGES = "TextImages"
SHEET_KPIGRIDS = "KpiGrids"
SHEET_TABLES = "Tables"
SHEET_CHARTS = "Charts"
SHEET_TOPCONTENTS = "TopContents"
SHEET_TOPCREATORS = "TopCreators"

SHEETS_IN_ORDER = [
    SHEET_INSTRUCCIONES,
    SHEET_REPORTE,
    SHEET_SECTIONS,
    SHEET_TEXTS,
    SHEET_IMAGES,
    SHEET_TEXTIMAGES,
    SHEET_KPIGRIDS,
    SHEET_TABLES,
    SHEET_CHARTS,
    SHEET_TOPCONTENTS,
    SHEET_TOPCREATORS,
]

WIDGET_SHEETS = [
    SHEET_TEXTS, SHEET_IMAGES, SHEET_TEXTIMAGES, SHEET_KPIGRIDS,
    SHEET_TABLES, SHEET_CHARTS, SHEET_TOPCONTENTS, SHEET_TOPCREATORS,
]

# Layout choices
LAYOUT_VALUES = ["stack", "columns_2", "columns_3"]

# Choice label maps (igual que hoy)
KIND_LABELS = {
    "INFLUENCER": "Influencer",
    "GENERAL": "General",
    "QUINCENAL": "Quincenal",
    "MENSUAL": "Mensual",
    "CIERRE_ETAPA": "Cierre de etapa",
}
KIND_FROM_LABEL = {v: k for k, v in KIND_LABELS.items()}

NETWORK_LABELS = {
    "INSTAGRAM": "Instagram",
    "TIKTOK": "TikTok",
    "X": "X",
}
NETWORK_FROM_LABEL = {v: k for k, v in NETWORK_LABELS.items()}

SOURCE_TYPE_LABELS = {
    "ORGANIC": "Orgánico",
    "INFLUENCER": "Influencer",
    "PAID": "Pauta",
}
SOURCE_TYPE_FROM_LABEL = {v: k for k, v in SOURCE_TYPE_LABELS.items()}

IMAGE_POSITION_VALUES = ["left", "right", "top"]
CHART_TYPE_VALUES = ["bar", "line"]
COLUMNS_VALUES = ["1", "2", "3"]
BOOL_VALUES = ["TRUE", "FALSE"]

# REPORTE KV (sin la tabla Layout — eliminada porque las sections traen order)
REPORTE_KV_ROWS = [
    ("tipo", "enum", True, "Mensual"),
    ("fecha_inicio", "date", True, "01/04/2026"),
    ("fecha_fin", "date", True, "30/04/2026"),
    ("titulo", "text", False, "Reporte general · Abril"),
    ("intro", "text", False, "Abril fue el mes…"),
    ("conclusiones", "text", False, "El ratio click→download…"),
]

# Headers por hoja
SECTIONS_HEADERS = ["nombre", "title", "layout", "order", "instructions"]

TEXTS_HEADERS = ["section_nombre", "widget_orden", "widget_title", "body"]

IMAGES_HEADERS = [
    "section_nombre", "widget_orden", "widget_title",
    "imagen", "image_alt", "caption",
]

TEXTIMAGES_HEADERS = [
    "section_nombre", "widget_orden", "widget_title",
    "body", "imagen", "image_alt", "image_position", "columns",
]

KPIGRIDS_HEADERS = [
    "section_nombre", "widget_orden", "widget_title",
    "tile_orden", "label", "value", "unit",
    "period_comparison", "period_comparison_label",
]

TABLES_HEADERS = [
    "section_nombre", "widget_orden", "widget_title", "widget_show_total",
    "row_orden", "is_header",
    "cell_1", "cell_2", "cell_3", "cell_4",
    "cell_5", "cell_6", "cell_7", "cell_8",
]

TABLE_CELL_COLS = [f"cell_{i}" for i in range(1, 9)]

CHARTS_HEADERS = [
    "section_nombre", "widget_orden", "widget_title",
    "widget_network", "chart_type",
    "point_orden", "point_label", "point_value",
]

TOPCONTENTS_HEADERS = [
    "section_nombre", "widget_orden", "widget_title",
    "widget_network", "widget_period_label",
    "item_orden", "imagen", "caption", "post_url", "source_type",
    "views", "likes", "comments", "shares", "saves",
]

TOPCREATORS_HEADERS = [
    "section_nombre", "widget_orden", "widget_title",
    "widget_network", "widget_period_label",
    "item_orden", "imagen", "handle", "post_url",
    "views", "likes", "comments", "shares",
]

SHEET_HEADERS = {
    SHEET_SECTIONS: SECTIONS_HEADERS,
    SHEET_TEXTS: TEXTS_HEADERS,
    SHEET_IMAGES: IMAGES_HEADERS,
    SHEET_TEXTIMAGES: TEXTIMAGES_HEADERS,
    SHEET_KPIGRIDS: KPIGRIDS_HEADERS,
    SHEET_TABLES: TABLES_HEADERS,
    SHEET_CHARTS: CHARTS_HEADERS,
    SHEET_TOPCONTENTS: TOPCONTENTS_HEADERS,
    SHEET_TOPCREATORS: TOPCREATORS_HEADERS,
}

_NETWORK_BLANK = [""] + list(NETWORK_LABELS.values())
_SOURCE_BLANK = [""] + list(SOURCE_TYPE_LABELS.values())

DROPDOWNS = {
    (SHEET_REPORTE, "tipo"): list(KIND_LABELS.values()),
    (SHEET_SECTIONS, "layout"): LAYOUT_VALUES,
    (SHEET_TEXTIMAGES, "image_position"): IMAGE_POSITION_VALUES,
    (SHEET_TEXTIMAGES, "columns"): COLUMNS_VALUES,
    (SHEET_TABLES, "widget_show_total"): BOOL_VALUES,
    (SHEET_TABLES, "is_header"): BOOL_VALUES,
    (SHEET_CHARTS, "widget_network"): _NETWORK_BLANK,
    (SHEET_CHARTS, "chart_type"): CHART_TYPE_VALUES,
    (SHEET_TOPCONTENTS, "widget_network"): _NETWORK_BLANK,
    (SHEET_TOPCONTENTS, "source_type"): _SOURCE_BLANK,
    (SHEET_TOPCREATORS, "widget_network"): _NETWORK_BLANK,
}

NOMBRE_PATTERN = r"^[a-z0-9_-]{1,60}$"
NOMBRE_MAX_LEN = 60

TYPE_PREFIX = {
    "TextWidget": "text",
    "ImageWidget": "imagen",
    "TextImageWidget": "textimage",
    "KpiGridWidget": "kpi",
    "TableWidget": "table",
    "ChartWidget": "chart",
    "TopContentsWidget": "topcontents",
    "TopCreatorsWidget": "topcreators",
}

ALLOWED_IMAGE_EXTENSIONS = [".jpg", ".jpeg", ".png", ".webp"]
```

- [ ] **Step 2: Reescribir `parsed.py`**

Leer el archivo actual. Adaptar las dataclasses para representar Section + Widget en lugar de Block. Reemplazar contenido por:

```python
"""Datos parseados del xlsx — input al builder."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date


@dataclass
class ParsedWidget:
    type_name: str          # "TextWidget", "TableWidget", etc.
    section_nombre: str     # FK to ParsedSection.nombre
    widget_orden: int
    widget_title: str
    fields: dict            # widget-specific scalar fields
    items: list[dict] = field(default_factory=list)  # rows/items hijos


@dataclass
class ParsedSection:
    nombre: str
    title: str
    layout: str             # "stack" | "columns_2" | "columns_3"
    order: int
    instructions: str


@dataclass
class ParsedReport:
    stage_id: int | None
    kind: str
    period_start: date
    period_end: date
    title: str
    intro_text: str
    conclusions_text: str
    sections: list[ParsedSection]                        # ordered by `order`
    widgets_by_section: dict[str, list[ParsedWidget]]    # section_nombre → [widgets]
    image_refs: set[str]
```

- [ ] **Step 3: Reescribir `excel_parser.py`**

Esto es el archivo más complejo. Estrategia: entender el archivo actual, mantener la arquitectura general (parser por hoja con manejo de errores acumulativo), pero reorganizar:

1. Parsear `Reporte` (KV) — sin Layout.
2. Parsear `Sections` — devolver lista de `ParsedSection`.
3. Para cada hoja de widget (8 hojas), parsear y agrupar por `(section_nombre, widget_orden)`.
4. Cross-reference: cada widget debe referenciar una `section_nombre` existente.
5. Image refs: collect across todos los widgets.

Reescribir completo:

```python
"""Parser xlsx → ParsedReport (post sections-widgets-redesign)."""
from __future__ import annotations

import re
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from io import BytesIO
from typing import Callable

from openpyxl import load_workbook
from openpyxl.worksheet.worksheet import Worksheet

from . import schema as s
from .errors import ImporterError
from .parsed import ParsedReport, ParsedSection, ParsedWidget


_NOMBRE_RE = re.compile(s.NOMBRE_PATTERN)


def parse(
    xlsx_bytes: bytes,
    available_images: set[str] | frozenset[str] = frozenset(),
) -> tuple[ParsedReport | None, list[ImporterError]]:
    errors: list[ImporterError] = []

    try:
        wb = load_workbook(BytesIO(xlsx_bytes), data_only=True)
    except Exception:
        return None, [ImporterError(
            sheet="(workbook)", row=None, column=None,
            reason="xlsx corrupto o ilegible",
        )]

    missing = [n for n in s.SHEETS_IN_ORDER if n not in wb.sheetnames]
    if missing:
        for name in missing:
            errors.append(ImporterError(
                sheet=name, row=None, column=None, reason="hoja faltante",
            ))
        return None, errors

    report_scalars, errors_reporte = _parse_reporte(wb[s.SHEET_REPORTE])
    errors.extend(errors_reporte)

    sections, errors_sections = _parse_sections(wb[s.SHEET_SECTIONS])
    errors.extend(errors_sections)

    section_nombres = {s_.nombre for s_ in sections}

    widgets_by_section: dict[str, list[ParsedWidget]] = {n: [] for n in section_nombres}
    for sheet_name, parser_fn in _WIDGET_PARSERS.items():
        widgets, sheet_errors = parser_fn(wb[sheet_name], section_nombres)
        errors.extend(sheet_errors)
        for w in widgets:
            widgets_by_section.setdefault(w.section_nombre, []).append(w)

    # Validar widget_orden único dentro de cada section.
    for nombre, widgets in widgets_by_section.items():
        seen = set()
        for w in widgets:
            if w.widget_orden in seen:
                errors.append(ImporterError(
                    sheet="(widgets)", row=None, column="widget_orden",
                    reason=f"widget_orden {w.widget_orden} duplicado en section '{nombre}'",
                ))
            seen.add(w.widget_orden)

    # Image refs.
    image_refs: set[str] = set()
    for widgets in widgets_by_section.values():
        for w in widgets:
            for filename in _collect_image_refs(w):
                image_refs.add(filename)
    for filename in sorted(image_refs):
        if filename not in available_images:
            errors.append(ImporterError(
                sheet="(images)", row=None, column="imagen",
                reason=(
                    f"imagen '{filename}' referenciada en el Excel pero "
                    "no presente en images/ del ZIP."
                ),
            ))

    if errors:
        return None, errors

    assert report_scalars is not None
    return ParsedReport(
        stage_id=None,
        sections=sorted(sections, key=lambda s_: s_.order),
        widgets_by_section=widgets_by_section,
        image_refs=image_refs,
        **report_scalars,
    ), errors


# --- Reporte (KV) ---
def _parse_reporte(ws: Worksheet) -> tuple[dict | None, list[ImporterError]]:
    errors: list[ImporterError] = []
    raw_kv: dict[str, object] = {}

    for row_idx in range(1, ws.max_row + 1):
        key_cell = ws.cell(row=row_idx, column=1).value
        if not isinstance(key_cell, str):
            continue
        key = key_cell.strip()
        if key.startswith("#") or key == "":
            continue
        normalized = key.rstrip("*").strip()
        raw_kv[normalized] = ws.cell(row=row_idx, column=2).value

    scalars: dict[str, object] = {}
    required_by_key = {key: req for key, _t, req, _ex in s.REPORTE_KV_ROWS}
    type_by_key = {key: t for key, t, _r, _ex in s.REPORTE_KV_ROWS}

    for key, type_hint in type_by_key.items():
        value = raw_kv.get(key)
        required = required_by_key[key]

        if _is_blank(value):
            if required:
                errors.append(ImporterError(
                    sheet=s.SHEET_REPORTE, row=None, column=key,
                    reason="obligatorio",
                ))
            if type_hint == "text":
                scalars[_kv_dataclass_name(key)] = ""
            continue

        if type_hint == "enum":
            label = str(value).strip()
            if label not in s.KIND_FROM_LABEL:
                errors.append(ImporterError(
                    sheet=s.SHEET_REPORTE, row=None, column=key,
                    reason=f"valor '{label}' inválido. Esperado: {', '.join(s.KIND_FROM_LABEL)}",
                ))
                continue
            scalars[_kv_dataclass_name(key)] = s.KIND_FROM_LABEL[label]
        elif type_hint == "date":
            d = _parse_date(value)
            if d is None:
                errors.append(ImporterError(
                    sheet=s.SHEET_REPORTE, row=None, column=key,
                    reason=f"fecha inválida: '{value}'",
                ))
                continue
            scalars[_kv_dataclass_name(key)] = d
        elif type_hint == "text":
            scalars[_kv_dataclass_name(key)] = str(value)

    return (scalars if scalars else None), errors


# --- Sections ---
def _parse_sections(ws: Worksheet) -> tuple[list[ParsedSection], list[ImporterError]]:
    sections: list[ParsedSection] = []
    errors: list[ImporterError] = []
    seen_orders: set[int] = set()
    seen_nombres: set[str] = set()

    for row_idx, row in _iter_data_rows(ws, s.SECTIONS_HEADERS):
        nombre = _str(row.get("nombre")).strip()
        if not _NOMBRE_RE.match(nombre):
            errors.append(ImporterError(
                sheet=s.SHEET_SECTIONS, row=row_idx, column="nombre",
                reason=f"'{nombre}' no cumple {s.NOMBRE_PATTERN}",
            ))
            continue
        if nombre in seen_nombres:
            errors.append(ImporterError(
                sheet=s.SHEET_SECTIONS, row=row_idx, column="nombre",
                reason=f"'{nombre}' duplicado",
            ))
            continue
        seen_nombres.add(nombre)

        orden = _coerce_int(row.get("order"))
        if orden is None or orden < 1:
            errors.append(ImporterError(
                sheet=s.SHEET_SECTIONS, row=row_idx, column="order",
                reason=f"entero ≥ 1 esperado, recibí '{row.get('order')}'",
            ))
            continue
        if orden in seen_orders:
            errors.append(ImporterError(
                sheet=s.SHEET_SECTIONS, row=row_idx, column="order",
                reason=f"order {orden} duplicado",
            ))
            continue
        seen_orders.add(orden)

        layout = _str(row.get("layout")).strip() or "stack"
        if layout not in s.LAYOUT_VALUES:
            errors.append(ImporterError(
                sheet=s.SHEET_SECTIONS, row=row_idx, column="layout",
                reason=f"'{layout}' inválido. Esperado: {', '.join(s.LAYOUT_VALUES)}",
            ))
            continue

        sections.append(ParsedSection(
            nombre=nombre,
            title=_str(row.get("title")),
            layout=layout,
            order=orden,
            instructions=_str(row.get("instructions")),
        ))

    return sections, errors


# --- Widget parsers (8 hojas) ---

def _parse_widget_sheet_simple(
    ws: Worksheet, sheet_name: str, headers: list[str],
    type_name: str, section_nombres: set[str],
    fields_to_capture: list[str],
) -> tuple[list[ParsedWidget], list[ImporterError]]:
    """Parser para hojas que NO tienen items hijos (Texts, Images, TextImages).
    Cada row es un widget completo."""
    widgets: list[ParsedWidget] = []
    errors: list[ImporterError] = []

    for row_idx, row in _iter_data_rows(ws, headers):
        section_nombre = _str(row.get("section_nombre")).strip()
        if section_nombre not in section_nombres:
            errors.append(ImporterError(
                sheet=sheet_name, row=row_idx, column="section_nombre",
                reason=f"'{section_nombre}' no existe en hoja Sections",
            ))
            continue

        widget_orden = _coerce_int(row.get("widget_orden"))
        if widget_orden is None or widget_orden < 1:
            errors.append(ImporterError(
                sheet=sheet_name, row=row_idx, column="widget_orden",
                reason=f"entero ≥ 1 esperado, recibí '{row.get('widget_orden')}'",
            ))
            continue

        fields = {}
        for col in fields_to_capture:
            fields[col] = _str(row.get(col)) if not _is_blank(row.get(col)) else ""

        widgets.append(ParsedWidget(
            type_name=type_name,
            section_nombre=section_nombre,
            widget_orden=widget_orden,
            widget_title=_str(row.get("widget_title")),
            fields=fields,
        ))

    return widgets, errors


def _parse_texts(ws, section_nombres):
    return _parse_widget_sheet_simple(
        ws, s.SHEET_TEXTS, s.TEXTS_HEADERS, "TextWidget", section_nombres,
        ["body"],
    )


def _parse_images(ws, section_nombres):
    return _parse_widget_sheet_simple(
        ws, s.SHEET_IMAGES, s.IMAGES_HEADERS, "ImageWidget", section_nombres,
        ["imagen", "image_alt", "caption"],
    )


def _parse_textimages(ws, section_nombres):
    widgets, errors = _parse_widget_sheet_simple(
        ws, s.SHEET_TEXTIMAGES, s.TEXTIMAGES_HEADERS, "TextImageWidget", section_nombres,
        ["body", "imagen", "image_alt", "image_position", "columns"],
    )
    # Validar columns y image_position
    for w in widgets:
        cols = w.fields.get("columns") or "1"
        if cols not in s.COLUMNS_VALUES:
            errors.append(ImporterError(
                sheet=s.SHEET_TEXTIMAGES, row=None, column="columns",
                reason=f"valor '{cols}' inválido (widget {w.widget_orden} en '{w.section_nombre}')",
            ))
        pos = w.fields.get("image_position") or "top"
        if pos not in s.IMAGE_POSITION_VALUES:
            errors.append(ImporterError(
                sheet=s.SHEET_TEXTIMAGES, row=None, column="image_position",
                reason=f"valor '{pos}' inválido",
            ))
        # Coerce
        w.fields["columns"] = int(cols) if cols.isdigit() else 1
        w.fields["image_position"] = pos
    return widgets, errors


def _parse_grouped_widget_sheet(
    ws: Worksheet, sheet_name: str, headers: list[str],
    type_name: str, section_nombres: set[str],
    block_field_cols: list[str], item_field_cols: list[str],
    item_orden_col: str,
) -> tuple[list[ParsedWidget], list[ImporterError]]:
    """Parser para hojas con items hijos: KpiGrids, Tables, Charts, TopContents, TopCreators.

    Agrupa rows por (section_nombre, widget_orden). Block fields (los del widget en sí)
    deben ser consistentes entre rows del mismo widget. Item fields construyen `items`.
    """
    errors: list[ImporterError] = []
    groups: dict[tuple[str, int], dict] = {}

    for row_idx, row in _iter_data_rows(ws, headers):
        section_nombre = _str(row.get("section_nombre")).strip()
        if section_nombre not in section_nombres:
            errors.append(ImporterError(
                sheet=sheet_name, row=row_idx, column="section_nombre",
                reason=f"'{section_nombre}' no existe en hoja Sections",
            ))
            continue

        widget_orden = _coerce_int(row.get("widget_orden"))
        if widget_orden is None or widget_orden < 1:
            errors.append(ImporterError(
                sheet=sheet_name, row=row_idx, column="widget_orden",
                reason=f"entero ≥ 1 esperado",
            ))
            continue

        key = (section_nombre, widget_orden)
        block_fields = {col: _str(row.get(col)) if not _is_blank(row.get(col)) else "" for col in block_field_cols}
        widget_title = _str(row.get("widget_title"))

        item_orden = _coerce_int(row.get(item_orden_col))
        item: dict = {item_orden_col: item_orden}
        for col in item_field_cols:
            item[col] = row.get(col)

        if key not in groups:
            groups[key] = {
                "title": widget_title,
                "fields": block_fields,
                "items": [],
            }
        else:
            existing = groups[key]
            for col in block_field_cols:
                if existing["fields"][col] != block_fields[col]:
                    errors.append(ImporterError(
                        sheet=sheet_name, row=row_idx, column=col,
                        reason=f"'{block_fields[col]}' difiere de '{existing['fields'][col]}' (widget {widget_orden} en '{section_nombre}')",
                    ))
        groups[key]["items"].append(item)

    widgets = [
        ParsedWidget(
            type_name=type_name,
            section_nombre=section_nombre,
            widget_orden=widget_orden,
            widget_title=data["title"],
            fields=data["fields"],
            items=data["items"],
        )
        for (section_nombre, widget_orden), data in groups.items()
    ]
    return widgets, errors


def _parse_kpigrids(ws, section_nombres):
    return _parse_grouped_widget_sheet(
        ws, s.SHEET_KPIGRIDS, s.KPIGRIDS_HEADERS, "KpiGridWidget", section_nombres,
        block_field_cols=[],
        item_field_cols=["label", "value", "unit", "period_comparison", "period_comparison_label"],
        item_orden_col="tile_orden",
    )


def _parse_tables(ws, section_nombres):
    widgets, errors = _parse_grouped_widget_sheet(
        ws, s.SHEET_TABLES, s.TABLES_HEADERS, "TableWidget", section_nombres,
        block_field_cols=["widget_show_total"],
        item_field_cols=["is_header"] + s.TABLE_CELL_COLS,
        item_orden_col="row_orden",
    )
    # Convert widget_show_total to bool
    for w in widgets:
        w.fields["widget_show_total"] = _coerce_bool(w.fields.get("widget_show_total"))
    return widgets, errors


def _parse_charts(ws, section_nombres):
    widgets, errors = _parse_grouped_widget_sheet(
        ws, s.SHEET_CHARTS, s.CHARTS_HEADERS, "ChartWidget", section_nombres,
        block_field_cols=["widget_network", "chart_type"],
        item_field_cols=["point_label", "point_value"],
        item_orden_col="point_orden",
    )
    # Validate chart_type and resolve network
    for w in widgets:
        ct = w.fields.get("chart_type") or "bar"
        if ct not in s.CHART_TYPE_VALUES:
            errors.append(ImporterError(
                sheet=s.SHEET_CHARTS, row=None, column="chart_type",
                reason=f"chart_type '{ct}' inválido",
            ))
        w.fields["chart_type"] = ct
        net_label = w.fields.get("widget_network") or ""
        w.fields["widget_network"] = s.NETWORK_FROM_LABEL.get(net_label) if net_label else None
    return widgets, errors


def _parse_topcontents(ws, section_nombres):
    widgets, errors = _parse_grouped_widget_sheet(
        ws, s.SHEET_TOPCONTENTS, s.TOPCONTENTS_HEADERS, "TopContentsWidget", section_nombres,
        block_field_cols=["widget_network", "widget_period_label"],
        item_field_cols=["imagen", "caption", "post_url", "source_type",
                         "views", "likes", "comments", "shares", "saves"],
        item_orden_col="item_orden",
    )
    for w in widgets:
        net_label = w.fields.get("widget_network") or ""
        w.fields["widget_network"] = s.NETWORK_FROM_LABEL.get(net_label) if net_label else None
    return widgets, errors


def _parse_topcreators(ws, section_nombres):
    widgets, errors = _parse_grouped_widget_sheet(
        ws, s.SHEET_TOPCREATORS, s.TOPCREATORS_HEADERS, "TopCreatorsWidget", section_nombres,
        block_field_cols=["widget_network", "widget_period_label"],
        item_field_cols=["imagen", "handle", "post_url",
                         "views", "likes", "comments", "shares"],
        item_orden_col="item_orden",
    )
    for w in widgets:
        net_label = w.fields.get("widget_network") or ""
        w.fields["widget_network"] = s.NETWORK_FROM_LABEL.get(net_label) if net_label else None
    return widgets, errors


_WIDGET_PARSERS: dict[str, Callable] = {
    s.SHEET_TEXTS: _parse_texts,
    s.SHEET_IMAGES: _parse_images,
    s.SHEET_TEXTIMAGES: _parse_textimages,
    s.SHEET_KPIGRIDS: _parse_kpigrids,
    s.SHEET_TABLES: _parse_tables,
    s.SHEET_CHARTS: _parse_charts,
    s.SHEET_TOPCONTENTS: _parse_topcontents,
    s.SHEET_TOPCREATORS: _parse_topcreators,
}


# --- Image refs collector ---
def _collect_image_refs(w: ParsedWidget):
    img = w.fields.get("imagen")
    if img:
        yield img
    for item in w.items:
        i = item.get("imagen")
        if i:
            yield i


# --- Helpers (idénticos al parser anterior) ---
def _iter_data_rows(ws: Worksheet, headers: list[str]):
    for row_idx in range(2, ws.max_row + 1):
        values = [ws.cell(row=row_idx, column=c).value for c in range(1, len(headers) + 1)]
        if all(_is_blank(v) for v in values):
            continue
        yield row_idx, dict(zip(headers, values))


def _parse_date(value) -> date | None:
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if isinstance(value, datetime):
        return value.date()
    if not isinstance(value, str):
        return None
    for fmt in ("%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(value.strip(), fmt).date()
        except ValueError:
            continue
    return None


def _coerce_int(value) -> int | None:
    if _is_blank(value):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        try:
            return int(float(value))
        except (TypeError, ValueError):
            return None


def _coerce_bool(value) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().upper() == "TRUE"
    return bool(value)


def _is_blank(v) -> bool:
    return v is None or (isinstance(v, str) and v.strip() == "")


def _str(v) -> str:
    if v is None:
        return ""
    return str(v)


def _kv_dataclass_name(key: str) -> str:
    mapping = {
        "tipo": "kind",
        "fecha_inicio": "period_start",
        "fecha_fin": "period_end",
        "titulo": "title",
        "intro": "intro_text",
        "conclusiones": "conclusions_text",
    }
    return mapping[key]
```

- [ ] **Step 4: Reescribir `builder.py`**

```python
"""Builder: ParsedReport → Report+Section+Widgets persistidos."""
from __future__ import annotations

from decimal import Decimal, InvalidOperation

from django.core.files.base import ContentFile
from django.db import transaction

from apps.reports.models import (
    ChartWidget, ChartDataPoint,
    ImageWidget,
    KpiGridWidget, KpiTile,
    Report,
    Section,
    TableWidget, TableRow,
    TextWidget,
    TextImageWidget,
    TopContentsWidget, TopContentItem,
    TopCreatorsWidget, TopCreatorItem,
)

from .parsed import ParsedReport, ParsedWidget


@transaction.atomic
def build_report(parsed: ParsedReport, image_bytes: dict[str, bytes], *, stage_id: int) -> Report:
    report = Report.objects.create(
        stage_id=stage_id,
        kind=parsed.kind,
        period_start=parsed.period_start,
        period_end=parsed.period_end,
        title=parsed.title,
        intro_text=parsed.intro_text,
        conclusions_text=parsed.conclusions_text,
        status=Report.Status.DRAFT,
    )

    for ps in parsed.sections:
        section = Section.objects.create(
            report=report,
            order=ps.order,
            title=ps.title,
            layout=ps.layout,
            instructions=ps.instructions,
        )
        widgets = parsed.widgets_by_section.get(ps.nombre, [])
        for w in sorted(widgets, key=lambda x: x.widget_orden):
            _BUILDERS[w.type_name](section, w, image_bytes)

    return report


def _build_text(section, w: ParsedWidget, images):
    TextWidget.objects.create(
        section=section, order=w.widget_orden,
        title=w.widget_title,
        body=w.fields.get("body", ""),
    )


def _build_image(section, w: ParsedWidget, images):
    iw = ImageWidget(
        section=section, order=w.widget_orden,
        title=w.widget_title,
        image_alt=w.fields.get("image_alt", ""),
        caption=w.fields.get("caption", ""),
    )
    _attach_image(iw, "image", w.fields.get("imagen"), images)
    iw.save()


def _build_textimage(section, w: ParsedWidget, images):
    iw = TextImageWidget(
        section=section, order=w.widget_orden,
        title=w.widget_title,
        body=w.fields.get("body", ""),
        image_alt=w.fields.get("image_alt", ""),
        image_position=w.fields.get("image_position", "top"),
        columns=w.fields.get("columns", 1),
    )
    _attach_image(iw, "image", w.fields.get("imagen"), images)
    iw.save()


def _build_kpigrid(section, w: ParsedWidget, images):
    kw = KpiGridWidget.objects.create(
        section=section, order=w.widget_orden, title=w.widget_title,
    )
    KpiTile.objects.bulk_create([
        KpiTile(
            widget=kw,
            order=item.get("tile_orden") or (idx + 1),
            label=str(item.get("label", "")),
            value=_dec(item.get("value"), Decimal("0")),
            unit=str(item.get("unit") or ""),
            period_comparison=_dec(item.get("period_comparison"), None),
            period_comparison_label=str(item.get("period_comparison_label") or ""),
        )
        for idx, item in enumerate(w.items)
    ])


def _build_table(section, w: ParsedWidget, images):
    tw = TableWidget.objects.create(
        section=section, order=w.widget_orden, title=w.widget_title,
        show_total=bool(w.fields.get("widget_show_total")),
    )
    for idx, item in enumerate(w.items):
        cells_raw = [item.get(f"cell_{i}") for i in range(1, 9)]
        last_non_blank = -1
        for i, v in enumerate(cells_raw):
            if v is not None and not (isinstance(v, str) and v.strip() == ""):
                last_non_blank = i
        cells = [str(v) if v is not None else "" for v in cells_raw[: last_non_blank + 1]]
        TableRow.objects.create(
            widget=tw,
            order=item.get("row_orden") or (idx + 1),
            is_header=str(item.get("is_header") or "").strip().upper() == "TRUE",
            cells=cells,
        )


def _build_chart(section, w: ParsedWidget, images):
    cw = ChartWidget.objects.create(
        section=section, order=w.widget_orden, title=w.widget_title,
        network=w.fields.get("widget_network"),
        chart_type=w.fields.get("chart_type", "bar"),
    )
    ChartDataPoint.objects.bulk_create([
        ChartDataPoint(
            widget=cw,
            order=item.get("point_orden") or (idx + 1),
            label=str(item.get("point_label", "")),
            value=_dec(item.get("point_value"), Decimal("0")),
        )
        for idx, item in enumerate(w.items)
    ])


def _build_topcontents(section, w: ParsedWidget, images):
    tcw = TopContentsWidget.objects.create(
        section=section, order=w.widget_orden, title=w.widget_title,
        network=w.fields.get("widget_network"),
        period_label=w.fields.get("widget_period_label", ""),
    )
    for idx, item in enumerate(w.items):
        child = TopContentItem(
            widget=tcw,
            order=item.get("item_orden") or (idx + 1),
            caption=str(item.get("caption") or ""),
            post_url=str(item.get("post_url") or ""),
            source_type=str(item.get("source_type") or "ORGANIC"),
            views=_int_or_none(item.get("views")),
            likes=_int_or_none(item.get("likes")),
            comments=_int_or_none(item.get("comments")),
            shares=_int_or_none(item.get("shares")),
            saves=_int_or_none(item.get("saves")),
        )
        _attach_image(child, "thumbnail", item.get("imagen"), images)
        child.save()


def _build_topcreators(section, w: ParsedWidget, images):
    tcw = TopCreatorsWidget.objects.create(
        section=section, order=w.widget_orden, title=w.widget_title,
        network=w.fields.get("widget_network"),
        period_label=w.fields.get("widget_period_label", ""),
    )
    for idx, item in enumerate(w.items):
        child = TopCreatorItem(
            widget=tcw,
            order=item.get("item_orden") or (idx + 1),
            handle=str(item.get("handle", "")),
            post_url=str(item.get("post_url") or ""),
            views=_int_or_none(item.get("views")),
            likes=_int_or_none(item.get("likes")),
            comments=_int_or_none(item.get("comments")),
            shares=_int_or_none(item.get("shares")),
        )
        _attach_image(child, "thumbnail", item.get("imagen"), images)
        child.save()


_BUILDERS = {
    "TextWidget": _build_text,
    "ImageWidget": _build_image,
    "TextImageWidget": _build_textimage,
    "KpiGridWidget": _build_kpigrid,
    "TableWidget": _build_table,
    "ChartWidget": _build_chart,
    "TopContentsWidget": _build_topcontents,
    "TopCreatorsWidget": _build_topcreators,
}


def _attach_image(instance, field_name, filename, images):
    if not filename:
        return
    data = images.get(filename)
    if data is None:
        raise ValueError(f"Imagen '{filename}' no está en el bundle.")
    field = getattr(instance, field_name)
    field.save(filename, ContentFile(data), save=False)


def _dec(value, default):
    if value is None or (isinstance(value, str) and not value.strip()):
        return default
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        return default


def _int_or_none(value):
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        try:
            return int(float(value))
        except (TypeError, ValueError):
            return None
```

- [ ] **Step 5: Reescribir `excel_writer.py` (skeleton + Instrucciones)**

Leer el archivo actual, reescribir el skeleton y las Instrucciones para reflejar el nuevo schema. La función `build_template()` itera `s.SHEETS_IN_ORDER` y para cada hoja escribe el header `s.SHEET_HEADERS[name]` (excepto Reporte que tiene KV custom). Aplica DataValidation desde `s.DROPDOWNS`. La función `build_skeleton()` produce el workbook vacío (usado por importer + exporter).

Mantener la misma estructura de clases pero con headers/sheets nuevos.

Para Instrucciones, actualizar el texto:
- Mencionar que la jerarquía es Section → Widget.
- Explicar la hoja `Sections`: nombre único + title (pill) + layout (stack/columns_2/columns_3) + order.
- Explicar las 8 hojas widget: cada row referencia `section_nombre` + `widget_orden`; widgets con items hijos repiten los block fields en cada row del item.
- Actualizar el contrato para el LLM: referencia a `TextWidget`, `TableWidget`, etc. (los nombres nuevos).

(Detalle exacto del texto está en el archivo actual; adaptarlo al nuevo modelo.)

- [ ] **Step 6: Reescribir `excel_exporter.py`**

Reescribir las funciones populate. Cambia el orden:

1. `_populate_reporte` (KV solo, sin Layout).
2. `_populate_sections` — itera `report.sections.order_by("order")`, una row por section.
3. Per widget type (8 funciones), itera widgets de cada type y popula su hoja.

Reemplazar `_assign_names` para que asigne nombres a Sections (no a widgets):

```python
def _assign_section_names(report: Report) -> dict[int, str]:
    counters: dict[str, int] = {}
    names: dict[int, str] = {}
    for section in report.sections.all().order_by("order"):
        # nombre por slug del title o "section_N"
        prefix = "section"
        counters[prefix] = counters.get(prefix, 0) + 1
        names[section.pk] = f"{prefix}_{counters[prefix]}"
    return names
```

Cada `_populate_*` (Texts, Tables, etc.) recibe `names: dict[int, str]` (section_pk → section_nombre) y escribe `section_nombre` correspondiente.

(El detalle es tedioso pero mecánico — copiar el patrón del exporter actual y adaptar columnas. Cada widget itera sus items y emite las rows.)

- [ ] **Step 7: Reescribir tests del importer**

`backend/tests/unit/test_excel_writer.py` y `backend/tests/unit/test_excel_parser.py`:
- Actualizar fixtures: crear Report → Section → Widget en lugar de Report → Block.
- Actualizar asserts sobre `wb.sheetnames`: la lista esperada cambia.
- Añadir un roundtrip test: crear un Report con varias sections de distintos layouts y widgets, exportar, parsear, asserttear que la estructura sobrevive.

- [ ] **Step 8: Verificar todo el suite**

```bash
docker compose exec backend pytest backend/tests/unit/test_excel_parser.py backend/tests/unit/test_excel_writer.py backend/tests/unit/test_bundle_reader.py backend/tests/unit/test_validate_import_command.py backend/tests/unit/test_reports_admin_import.py -v
```
Expected: PASS. Si falla, fix y retry.

```bash
docker compose exec backend pytest backend/tests/unit/ -v
```
Expected: full suite green.

- [ ] **Step 9: Test manual del importer admin**

Levantar la app, ir al admin, descargar template (`/admin/reports/report/download-template/`), abrir el xlsx y verificar visualmente que:
- Hay hojas `Sections`, `Texts`, `Images`, `TextImages`, `KpiGrids`, `Tables`, `Charts`, `TopContents`, `TopCreators`.
- Los headers de cada hoja son los esperados.
- Las dropdowns funcionan (layout, image_position, etc.).

Descargar example de un Report seedeado (`/admin/reports/report/download-example/<id>/`), abrirlo, verificar que la data está bien rellenada. Reimportarlo (`/admin/reports/report/import/`) en otro stage y verificar que el nuevo Report es idéntico al original.

- [ ] **Step 10: Commit**

```bash
git add backend/apps/reports/importers/ \
        backend/tests/unit/test_excel_parser.py \
        backend/tests/unit/test_excel_writer.py
git commit -m "feat(reports): rewrite importer for Sections + Widgets schema"
```

---

## Task 8: Drop legacy block models, FE, tests

**Files:**
- Borrar: `backend/apps/reports/models/blocks/` (directorio completo)
- Borrar: `backend/tests/unit/blocks/` (directorio completo)
- Modify: `backend/apps/reports/models/__init__.py`
- Migration: `backend/apps/reports/migrations/0023_drop_blocks.py` (auto)

- [ ] **Step 1: Verificar que ningún código de producción referencia legacy block models**

```bash
grep -rn "ReportBlock\|TextImageBlock\|ImageBlock\|KpiGridBlock\|TableBlock\|ChartBlock\|TopContentsBlock\|TopCreatorsBlock\|MetricsTableBlock\|AttributionTableBlock" \
  backend/apps/ --include="*.py" 2>/dev/null | grep -v migrations | grep -v "/blocks/"
```

Expected: cero hits, o solo los aliases en `models/__init__.py` que vamos a sacar.

- [ ] **Step 2: Borrar el directorio `models/blocks/`**

```bash
git rm -r backend/apps/reports/models/blocks/
```

- [ ] **Step 3: Borrar tests legacy de blocks**

```bash
git rm -r backend/tests/unit/blocks/
```

- [ ] **Step 4: Limpiar `models/__init__.py`**

Editar `backend/apps/reports/models/__init__.py` y quitar TODOS los imports de `.blocks.*` (incluyendo los aliases legacy). El archivo final debe tener solo:

```python
"""Reports domain models — Sections + Widgets architecture."""
from .report import Report  # noqa: F401
from .follower_snapshot import BrandFollowerSnapshot  # noqa: F401

# Sections + Widgets:
from .section import Section  # noqa: F401
from .widgets.base_widget import Widget  # noqa: F401
from .widgets.text import TextWidget  # noqa: F401
from .widgets.image import ImageWidget  # noqa: F401
from .widgets.text_image import TextImageWidget  # noqa: F401
from .widgets.kpi_grid import KpiGridWidget, KpiTile  # noqa: F401
from .widgets.table import TableWidget, TableRow  # noqa: F401
from .widgets.chart import ChartWidget, ChartDataPoint  # noqa: F401
from .widgets.top_contents import TopContentsWidget, TopContentItem  # noqa: F401
from .widgets.top_creators import TopCreatorsWidget, TopCreatorItem  # noqa: F401

# Attachments:
from .attachments import ReportAttachment  # noqa: F401
```

- [ ] **Step 5: Generar migración de drop**

```bash
docker compose exec backend python manage.py makemigrations reports --name drop_blocks
```

Expected: `0023_drop_blocks.py` con `DeleteModel` para los 8 blocks legacy + 4 row/item legacy + `RemoveField` previos para FKs.

- [ ] **Step 6: Aplicar migración**

```bash
docker compose exec backend python manage.py migrate reports
```

- [ ] **Step 7: Actualizar el LLM seed prompt**

Editar `backend/apps/llm/seed/parse_pdf_report.md`. Reemplazar las menciones a `*Block` por `*Widget` y agregar la jerarquía Section → Widget. Cuerpo:

```markdown
6. Tipos válidos de widget (campo `type_name`):
   - TextWidget — texto puro (markdown)
   - ImageWidget — imagen con alt + caption opcional
   - TextImageWidget — combo texto + imagen integrado (con image_position y columns)
   - KpiGridWidget — grilla de KPIs (tiles con label/value)
   - TableWidget — tabla genérica (rows con cells: list[str]; primera row con is_header=true)
   - ChartWidget — gráfico (chart_type bar/line, datapoints label/value)
   - TopContentsWidget — top de posts (caption + métricas + thumbnail)
   - TopCreatorsWidget — top de creadores (handle + métricas + thumbnail)
7. Cada widget pertenece a una `section` (con title=pill, layout=stack/columns_2/columns_3).
```

(Adaptar al texto exacto del archivo actual.)

- [ ] **Step 8: Verificar suite**

```bash
docker compose exec backend python manage.py check
docker compose exec backend pytest backend/tests/ -v
```
Expected: 0 issues, todo PASS.

```bash
docker compose exec frontend npx tsc --noEmit
```

Expected: no app errors (preexistentes en tests playwright están OK).

- [ ] **Step 9: Commit**

```bash
git add backend/apps/reports/models/__init__.py \
        backend/apps/reports/migrations/0023_drop_blocks.py \
        backend/apps/llm/seed/parse_pdf_report.md
git commit -m "refactor(reports): drop legacy block models + tests"
```

---

## Task 9: Reseed final + full suite + e2e smoke + visual check

**Files:** none (verification only)

- [ ] **Step 1: Flush + migrate + seed**

```bash
docker compose exec backend python manage.py flush --no-input
docker compose exec backend python manage.py migrate
docker compose exec backend python manage.py seed_demo
```

Expected: completes clean. Verificar la jerarquía:

```bash
docker compose exec backend python manage.py shell -c "
from apps.reports.models import Report
for r in Report.objects.all().order_by('id'):
    print(f'{r.id} {r.title} - {r.stage.name}')
    for sec in r.sections.all().order_by('order'):
        print(f'  Section #{sec.order} [{sec.layout}]: {sec.title}')
        for w in sec.widgets.all().order_by('order'):
            print(f'    Widget #{w.order}: {type(w).__name__} title={w.title!r}')
"
```

Spot-check el output: para abril, debería verse algo como:
```
9 Reporte general · Abril - Conversión
  Section #1 [stack]: Contexto del mes
    Widget #1: TextImageWidget title=''
  Section #2 [stack]: KPIs del mes
    Widget #1: KpiGridWidget title=''
  Section #3 [stack]: Mes a mes
    Widget #1: TableWidget title=''
  ...
```

- [ ] **Step 2: Restart frontend para clear Next.js cache**

```bash
docker compose restart frontend
sleep 15
```

- [ ] **Step 3: Ejecutar unit tests**

```bash
npm run test:unit
```
Expected: PASS.

- [ ] **Step 4: Ejecutar e2e smoke**

```bash
npm run test:e2e:smoke
```
Expected: PASS. Si algún E2E asserta sobre texto del viewer (pills, etc.), debería seguir funcionando porque el output visual es idéntico al de antes.

- [ ] **Step 5: Visual check del viewer**

Browser → `http://localhost:3000/login` → demo user → navegar a un reporte. Verificar:

1. Pills aparecen con sus titles correctos.
2. Color rotation: pill 1 = mint, pill 2 = pink, pill 3 = yellow, pill 4 = white, pill 5 = mint, etc.
3. KPIs side-by-side dentro del KpiGridWidget.
4. Tablas auto-format + deltas verde/rojo.
5. Total row en Atribución OneLink.
6. Posts del mes y Creators del mes con cards.
7. Charts (bar + line) con sus datos.
8. Conclusiones aparece justo después de la KPI section (igual que hoy).

- [ ] **Step 6: Si todo verde, no hay commit**

(Solo verificación.)

---

## Task 10: Update memorias

**Files:**
- Modify: `C:\Users\danie\.claude\projects\C--Users-danie-Impactia-Git-Chirri-Peppers-Chirri-Portal\memory\project_reports_are_powerpoint.md` (extender)
- Modify: `C:\Users\danie\.claude\projects\C--Users-danie-Impactia-Git-Chirri-Peppers-Chirri-Portal\memory\project_block_vs_item_polymorphism.md` (deprecar terminología "block")
- Modify: `C:\Users\danie\.claude\projects\C--Users-danie-Impactia-Git-Chirri-Peppers-Chirri-Portal\memory\MEMORY.md` (update entries)

- [ ] **Step 1: Extender `project_reports_are_powerpoint.md`**

Agregar al final:

```markdown
## Update 2026-04-27 — Sections + Widgets

El modelo flat `Report → Block` evolucionó a `Report → Section → Widget`:

- `Section` es el contenedor de presentación (pill + layout: stack/columns_2/columns_3).
- `Widget` es la unidad atómica (polimórfico, mismo patrón que el viejo `ReportBlock`).
- El pill ya no vive en cada widget — vive en la Section. Color rotation se calcula desde `Section.order` (cycle mint → pink → yellow → white).
- Widgets pueden tener `title` opcional (subtítulo dentro del widget, no pill).
- 8 widget types: TextWidget, ImageWidget, TextImageWidget, KpiGridWidget, TableWidget, ChartWidget, TopContentsWidget, TopCreatorsWidget.
- Para "varios elementos lado a lado" → o usás un widget compuesto (KpiGridWidget tiene tiles internos side-by-side), o usás `Section.layout = columns_2/columns_3` que mete todos los widgets de la section en grid responsivo.
- Sin `Widget.width` (cada widget ocupa todo el espacio asignado por el layout de la section).
- ReportTemplate (DEV-118) cuando se implemente debería partir de este modelo, no del antiguo.
```

- [ ] **Step 2: Update `project_block_vs_item_polymorphism.md`**

Agregar al final:

```markdown
## Update 2026-04-27 — Block → Widget rename

La regla sigue valiendo, solo cambia la terminología:
- "Block" como concepto NO existe más en el código. Se llama `Widget`.
- El contenedor de N widgets es `Section` (con pill + layout).
- "Shape de render distinto = dos widgets distintos" sigue valiendo (TableWidget vs ChartWidget).
- "Mismo shape, dominios distintos = un widget genérico" sigue valiendo (TableWidget colapsa lo que antes era MetricsTable + Attribution).
- "Items polimórficos bajo un widget compuesto" sigue valiendo (TopContentsWidget items, TopCreatorsWidget items, KpiGridWidget tiles).
```

- [ ] **Step 3: Update `MEMORY.md`**

Cambiar la línea de `Reports = PowerPoint` para reflejar el cambio:

```markdown
- [Reports = PowerPoint](project_reports_are_powerpoint.md) — blocks (renombrados a widgets bajo Sections) son artefactos de presentación; mismo shape de render = mismo widget aunque el dominio difiera.
```

Y la línea de `Block vs Item polymorphism`:

```markdown
- [Widget vs Item polymorphism](project_block_vs_item_polymorphism.md) — shape widget distinto → dos widgets; shape idéntico con items distintos → un widget genérico + items polimórficos.
```

- [ ] **Step 4: No hay commit (memorias son del usuario)**

---

## Self-Review Checklist

**Spec coverage:**
- ✅ Section model + Layout enum (Task 1).
- ✅ Widget polymorphic base (Task 1).
- ✅ 8 widget subtypes (Task 2).
- ✅ Serializers + dispatcher (Task 3).
- ✅ Admin + sortable inlines + polymorphic widget (Task 4).
- ✅ Frontend types + 8 widget components + SectionRenderer + page.tsx (Task 5).
- ✅ Color rotation por Section.order (Task 5 SectionRenderer).
- ✅ seed_demo emite Sections + Widgets (Task 6).
- ✅ Importer reescrito (Task 7).
- ✅ Drop legacy (Task 8).
- ✅ Verify (Task 9).
- ✅ Memorias (Task 10).

**Type consistency:**
- `Widget` model → `WidgetDto` FE → `Widget` admin: 8 subtypes con mismos nombres.
- `Section.Layout`: `stack` / `columns_2` / `columns_3` consistente en backend, FE, importer.
- `KpiTile.widget` (no `kpi_grid_block`), `TableRow.widget` (no `table_block`), `ChartDataPoint.widget`, `TopContentItem.widget`, `TopCreatorItem.widget` — FK renombrado a `widget` en todos los items.

**Pendientes razonables (no en scope):**
- ReportTemplate (DEV-118) — se implementa aparte cuando llegue. Memoria documenta que debe usar el nuevo modelo.
- Optimizar prefetch_related polimórfico para reducir N+1 — la forma actual `prefetch_related("sections__widgets")` puede generar queries extras por subtype; si se nota performance issue, optimizar entonces.

---

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-04-27-sections-widgets-redesign.md`. Two execution options:

**1. Subagent-Driven (recommended)** — yo despacho un subagente fresco por task, reviso entre tasks, iteración rápida.

**2. Inline Execution** — ejecuto los tasks en esta sesión usando executing-plans, batch con checkpoints para review.

¿Cuál preferís?
