# Unify Table Blocks Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Colapsar `MetricsTableBlock` + `AttributionTableBlock` (y sus row models `MetricsTableRow`, `OneLinkAttribution`) en un único `TableBlock` genérico. Un reporte es como un PowerPoint: una tabla es una tabla, sin importar el dominio de los datos.

**Architecture:** `TableBlock` con `title` (pill) + `show_total`. Hijo `TableRow` con `order`, `is_header` (flag), y `cells: JSONField` (lista de strings). El frontend hace auto-format de números/deltas y suma totales. Sin choices de dominio (Network, source_type) en este block — los valores van como texto en las celdas.

**Tech Stack:** Django 5 + django-polymorphic, DRF, PostgreSQL, Next.js 14 App Router, openpyxl, pytest, Playwright.

**Pre-condition:** OK destruir DB y reseed (confirmado por Dani 2026-04-26 — no hay producción todavía, todo es demo).

---

## File Structure

**Crear:**
- `backend/apps/reports/models/blocks/table.py` — `TableBlock` + `TableRow`.
- `backend/apps/reports/migrations/0020_table_block.py` — auto-generada con `makemigrations`.
- `backend/apps/reports/migrations/0021_drop_legacy_table_blocks.py` — auto-generada al borrar los modelos legacy.
- `backend/tests/unit/blocks/test_table_block.py` — tests del modelo + serializer + admin.
- `frontend/app/reports/[id]/blocks/TableBlock.tsx` — render component.

**Modificar:**
- `backend/apps/reports/models/__init__.py` — agregar `TableBlock`/`TableRow`, sacar legacy.
- `backend/apps/reports/serializers.py` — agregar `TableBlockSerializer`, sacar legacy serializers.
- `backend/apps/reports/admin.py` — agregar inline + admin para `TableBlock`, sacar legacy.
- `backend/apps/reports/importers/schema.py` — sacar `SHEET_METRICSTABLES`/`SHEET_ATTRIBUTION`/headers; agregar `SHEET_TABLES` + `TABLES_HEADERS`.
- `backend/apps/reports/importers/excel_parser.py` — sacar `_parse_metricstables`/`_parse_attribution`; agregar `_parse_tables`.
- `backend/apps/reports/importers/builder.py` — sacar `_build_metricstables`/`_build_attribution`; agregar `_build_tables`.
- `backend/apps/reports/importers/excel_exporter.py` — sacar `_populate_metricstables`/`_populate_attribution`; agregar `_populate_tables`.
- `backend/apps/reports/importers/excel_writer.py` — actualizar texto de Instrucciones.
- `backend/apps/tenants/management/commands/seed_demo.py` — emitir `TableBlock` para Mes-a-mes/IG/TikTok/X/Atribución.
- `frontend/lib/api.ts` — agregar `TableBlockDto`/`TableRowDto`, sacar legacy DTOs.
- `frontend/app/reports/[id]/blocks/BlockRenderer.tsx` — registrar `TableBlock`, sacar legacy.

**Borrar:**
- `backend/apps/reports/models/blocks/metrics_table.py`
- `backend/apps/reports/models/blocks/attribution.py`
- `backend/apps/reports/models/onelink_attribution.py`
- `backend/tests/unit/blocks/test_metrics_table_block.py`
- `backend/tests/unit/blocks/test_attribution_table_block.py`
- `backend/tests/unit/test_onelink_attribution_block_fk.py`
- `frontend/app/reports/[id]/blocks/MetricsTableBlock.tsx`
- `frontend/app/reports/[id]/blocks/AttributionTableBlock.tsx`

**Preservar:**
- `apps/reports/choices.py` — `Network` y `SourceType` siguen vivos: los usan `TopContentsBlock`, `TopCreatorsBlock`, `ChartBlock`, `TopContentItem`. Solo se eliminan los usos en `MetricsTableBlock`/`MetricsTableRow`.

---

## Task 1: Backend — agregar modelos `TableBlock` + `TableRow`

**Files:**
- Create: `backend/apps/reports/models/blocks/table.py`
- Modify: `backend/apps/reports/models/__init__.py`
- Test: `backend/tests/unit/blocks/test_table_block.py`

- [ ] **Step 1: Escribir el test del modelo**

Crear archivo `backend/tests/unit/blocks/test_table_block.py`:

```python
"""Tests del TableBlock genérico — DEV-XXX."""
import pytest

from apps.reports.models import Report, TableBlock, TableRow
from apps.reports.tests.factories import make_report


@pytest.mark.django_db
def test_table_block_can_be_created_with_pill_and_show_total():
    report = make_report()
    block = TableBlock.objects.create(
        report=report, order=1,
        title="Instagram", show_total=False,
    )
    assert block.report_id == report.id
    assert block.title == "Instagram"
    assert block.show_total is False


@pytest.mark.django_db
def test_table_rows_persist_cells_as_string_list():
    report = make_report()
    block = TableBlock.objects.create(report=report, order=1, title="IG")
    TableRow.objects.create(
        table_block=block, order=1, is_header=True,
        cells=["Métrica", "Valor", "Δ"],
    )
    TableRow.objects.create(
        table_block=block, order=2, is_header=False,
        cells=["ORGANIC · reach", "312000", "+9.9%"],
    )
    rows = list(block.rows.order_by("order"))
    assert len(rows) == 2
    assert rows[0].is_header is True
    assert rows[0].cells == ["Métrica", "Valor", "Δ"]
    assert rows[1].cells == ["ORGANIC · reach", "312000", "+9.9%"]


@pytest.mark.django_db
def test_table_row_order_is_unique_per_block():
    from django.db import IntegrityError, transaction
    report = make_report()
    block = TableBlock.objects.create(report=report, order=1)
    TableRow.objects.create(table_block=block, order=1, cells=["a"])
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            TableRow.objects.create(table_block=block, order=1, cells=["b"])


@pytest.mark.django_db
def test_table_block_polymorphic_returns_subtype():
    """Asegurar que django-polymorphic devuelve la instancia subtipo."""
    from apps.reports.models import ReportBlock
    report = make_report()
    TableBlock.objects.create(report=report, order=1, title="X")
    fetched = ReportBlock.objects.filter(report=report).first()
    assert isinstance(fetched, TableBlock)
```

- [ ] **Step 2: Correr el test (debe fallar — modelo no existe)**

Run: `docker compose exec backend pytest backend/tests/unit/blocks/test_table_block.py -v`
Expected: ImportError porque `TableBlock` y `TableRow` no existen.

- [ ] **Step 3: Crear el modelo**

Crear `backend/apps/reports/models/blocks/table.py`:

```python
"""TableBlock + TableRow — tabla genérica (un reporte es un PowerPoint, no un dominio).

Reemplaza MetricsTableBlock + AttributionTableBlock. Los valores de las
celdas son strings; el frontend infiere alineación y formato (números a la
derecha con locale es-AR, deltas con coloreo verde/rojo).
"""
from django.db import models

from .base_block import ReportBlock


class TableBlock(ReportBlock):
    title = models.CharField(
        max_length=200, blank=True,
        help_text="Pill title arriba de la tabla (ej. 'Instagram', 'Atribución OneLink').",
    )
    show_total = models.BooleanField(
        default=False,
        help_text=(
            "Si está activado, el frontend agrega una fila 'Total' al final "
            "sumando las columnas numéricas de las filas no-header."
        ),
    )

    class Meta:
        app_label = "reports"
        verbose_name = "Table Block"
        verbose_name_plural = "Table Blocks"


class TableRow(models.Model):
    table_block = models.ForeignKey(
        TableBlock, on_delete=models.CASCADE, related_name="rows",
    )
    order = models.PositiveIntegerField()
    is_header = models.BooleanField(
        default=False,
        help_text="Si está activado, la fila se renderea con estilo de header (bold + uppercase + bg).",
    )
    cells = models.JSONField(
        default=list,
        help_text="Lista de strings, una por columna. El render formatea números/deltas automáticamente.",
    )

    class Meta:
        app_label = "reports"
        ordering = ["table_block", "order"]
        constraints = [
            models.UniqueConstraint(
                fields=["table_block", "order"],
                name="uniq_row_order_per_table",
            ),
        ]

    def __str__(self):
        return f"{self.table_block_id} #{self.order}: {self.cells}"
```

- [ ] **Step 4: Registrar en `models/__init__.py`**

Editar `backend/apps/reports/models/__init__.py` y agregar la línea con los imports de blocks:

```python
from .blocks.table import TableBlock, TableRow  # noqa: F401
```

(Ubicarla junto a las demás importaciones de blocks, antes de la sección de Attachments.)

- [ ] **Step 5: Generar la migración**

Run: `docker compose exec backend python manage.py makemigrations reports --name table_block`
Expected: `0020_table_block.py` creado con `CreateModel TableBlock` y `CreateModel TableRow`.

- [ ] **Step 6: Aplicar la migración**

Run: `docker compose exec backend python manage.py migrate reports`
Expected: `Applying reports.0020_table_block... OK`

- [ ] **Step 7: Correr el test (debe pasar)**

Run: `docker compose exec backend pytest backend/tests/unit/blocks/test_table_block.py -v`
Expected: 4 passed.

- [ ] **Step 8: Commit**

```bash
git add backend/apps/reports/models/blocks/table.py \
        backend/apps/reports/models/__init__.py \
        backend/apps/reports/migrations/0020_table_block.py \
        backend/tests/unit/blocks/test_table_block.py
git commit -m "feat(reports): add generic TableBlock + TableRow models"
```

---

## Task 2: Backend — `TableBlockSerializer` + dispatch polimórfico

**Files:**
- Modify: `backend/apps/reports/serializers.py`
- Test: `backend/tests/unit/blocks/test_table_block.py` (extender)

- [ ] **Step 1: Agregar test del serializer**

Append a `backend/tests/unit/blocks/test_table_block.py`:

```python
@pytest.mark.django_db
def test_table_block_serializes_with_polymorphic_dispatcher():
    from apps.reports.serializers import ReportBlockSerializer
    report = make_report()
    block = TableBlock.objects.create(
        report=report, order=1, title="IG", show_total=True,
    )
    TableRow.objects.create(
        table_block=block, order=1, is_header=True,
        cells=["Métrica", "Valor", "Δ"],
    )
    TableRow.objects.create(
        table_block=block, order=2,
        cells=["ORGANIC · reach", "312000", "+9.9%"],
    )
    data = ReportBlockSerializer(block).data
    assert data["type"] == "TableBlock"
    assert data["title"] == "IG"
    assert data["show_total"] is True
    assert len(data["rows"]) == 2
    assert data["rows"][0] == {
        "order": 1, "is_header": True,
        "cells": ["Métrica", "Valor", "Δ"],
    }
    assert data["rows"][1] == {
        "order": 2, "is_header": False,
        "cells": ["ORGANIC · reach", "312000", "+9.9%"],
    }
```

- [ ] **Step 2: Correr el test (debe fallar)**

Run: `docker compose exec backend pytest backend/tests/unit/blocks/test_table_block.py::test_table_block_serializes_with_polymorphic_dispatcher -v`
Expected: FAIL — el dispatcher devuelve fallback `{"id", "order", "type": "TableBlock"}` sin rows porque no hay serializer registrado.

- [ ] **Step 3: Agregar `TableRowSerializer` y `TableBlockSerializer`**

Editar `backend/apps/reports/serializers.py`. Agregar el import:

```python
from .models import (
    Report, ReportAttachment,
    TextImageBlock, ImageBlock, KpiGridBlock, KpiTile,
    MetricsTableBlock, MetricsTableRow,
    TableBlock, TableRow,
    TopContentsBlock, TopContentItem,
    TopCreatorsBlock, TopCreatorItem,
    AttributionTableBlock,
    ChartBlock, ChartDataPoint,
    OneLinkAttribution,
)
```

Y agregar los serializers (ubicar `TableRowSerializer` con los demás child row serializers, y `TableBlockSerializer` con los demás subtype block serializers):

```python
class TableRowSerializer(serializers.ModelSerializer):
    class Meta:
        model = TableRow
        fields = ("order", "is_header", "cells")


class TableBlockSerializer(serializers.ModelSerializer):
    type = serializers.SerializerMethodField()
    rows = TableRowSerializer(many=True, read_only=True)

    class Meta:
        model = TableBlock
        fields = BASE_BLOCK_FIELDS + ("type", "title", "show_total", "rows")

    def get_type(self, obj) -> str:
        return "TableBlock"
```

Y registrar en `_BLOCK_SERIALIZERS`:

```python
_BLOCK_SERIALIZERS = {
    TextImageBlock: TextImageBlockSerializer,
    ImageBlock: ImageBlockSerializer,
    KpiGridBlock: KpiGridBlockSerializer,
    MetricsTableBlock: MetricsTableBlockSerializer,
    TableBlock: TableBlockSerializer,
    TopContentsBlock: TopContentsBlockSerializer,
    TopCreatorsBlock: TopCreatorsBlockSerializer,
    AttributionTableBlock: AttributionTableBlockSerializer,
    ChartBlock: ChartBlockSerializer,
}
```

- [ ] **Step 4: Correr el test (debe pasar)**

Run: `docker compose exec backend pytest backend/tests/unit/blocks/test_table_block.py -v`
Expected: 5 passed.

- [ ] **Step 5: Correr todos los tests de serializer del report para asegurar que nada se rompió**

Run: `docker compose exec backend pytest backend/tests/unit/blocks/test_polymorphic_serializer.py backend/tests/unit/test_report_detail_serializer.py -v`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add backend/apps/reports/serializers.py backend/tests/unit/blocks/test_table_block.py
git commit -m "feat(reports): add TableBlockSerializer + polymorphic dispatch"
```

---

## Task 3: Backend — admin con inline `TableRow`

**Files:**
- Modify: `backend/apps/reports/admin.py`

- [ ] **Step 1: Agregar inline + admin**

Editar `backend/apps/reports/admin.py`. Importar `TableBlock`/`TableRow`:

```python
from .models import (
    Report, ReportAttachment, ReportBlock,
    TextImageBlock, ImageBlock, KpiGridBlock, KpiTile,
    MetricsTableBlock, MetricsTableRow,
    TableBlock, TableRow,
    TopContentsBlock, TopContentItem,
    TopCreatorsBlock, TopCreatorItem,
    AttributionTableBlock,
    ChartBlock, ChartDataPoint,
    OneLinkAttribution, BrandFollowerSnapshot,
)
```

Agregar `TableRowInline` con los demás inlines (después de `OneLinkAttributionInline`):

```python
class TableRowInline(SortableTabularInline):
    """Filas de TableBlock — texto plano por celda. Soporta drag-reorder."""
    model = TableRow
    extra = 0
    fields = ("order", "is_header", "cells")
    ordering = ("order",)
```

Agregar el inline child al `ReportBlockInline.child_inlines`:

```python
class TableBlockInline(StackedPolymorphicInline.Child):
    model = TableBlock
```

Y agregarlo en la tupla `child_inlines`. Y registrar `TableBlock` en `ReportBlockAdmin.child_models`:

```python
@admin.register(ReportBlock)
class ReportBlockAdmin(PolymorphicParentModelAdmin):
    base_model = ReportBlock
    child_models = (
        TextImageBlock, ImageBlock, KpiGridBlock, MetricsTableBlock, TableBlock,
        TopContentsBlock, TopCreatorsBlock, AttributionTableBlock, ChartBlock,
    )
    list_display = ("report", "order", "polymorphic_ctype")
    list_filter = ("polymorphic_ctype",)
    search_fields = ("report__title",)
```

Agregar el admin standalone (después de `MetricsTableBlockAdmin`):

```python
@admin.register(TableBlock)
class TableBlockAdmin(_BlockChildAdminBase):
    inlines = [TableRowInline]
    list_display = ("report", "order", "title", "show_total")
```

- [ ] **Step 2: Correr los tests de admin polimórfico**

Run: `docker compose exec backend pytest backend/tests/unit/blocks/test_admin_polymorphic.py -v`
Expected: PASS (no se está testeando `TableBlock` específicamente en este suite, pero el suite verifica que el admin se carga sin errores con todos los child models).

- [ ] **Step 3: Verificar que el admin abre sin errores**

Run: `docker compose exec backend python manage.py check`
Expected: `System check identified no issues (0 silenced).`

- [ ] **Step 4: Commit**

```bash
git add backend/apps/reports/admin.py
git commit -m "feat(reports): register TableBlock in admin with sortable rows inline"
```

---

## Task 4: Frontend — `TableBlockDto` + `TableBlock.tsx`

**Files:**
- Modify: `frontend/lib/api.ts`
- Create: `frontend/app/reports/[id]/blocks/TableBlock.tsx`
- Modify: `frontend/app/reports/[id]/blocks/BlockRenderer.tsx`

- [ ] **Step 1: Agregar DTOs en `lib/api.ts`**

Editar `frontend/lib/api.ts`. Justo antes de `// -- Block subtype DTOs --`, agregar:

```typescript
export type TableRowDto = {
  order: number;
  is_header: boolean;
  cells: string[];
};
```

Y agregar el block DTO junto a los demás (cerca de `MetricsTableBlockDto`):

```typescript
export type TableBlockDto = BaseBlockFields & {
  type: "TableBlock";
  title: string;
  show_total: boolean;
  rows: TableRowDto[];
};
```

Y agregarlo a la unión:

```typescript
export type ReportBlockDto =
  | TextImageBlockDto
  | ImageBlockDto
  | KpiGridBlockDto
  | MetricsTableBlockDto
  | TableBlockDto
  | TopContentsBlockDto
  | TopCreatorsBlockDto
  | AttributionTableBlockDto
  | ChartBlockDto;
```

- [ ] **Step 2: Crear el componente `TableBlock.tsx`**

Crear `frontend/app/reports/[id]/blocks/TableBlock.tsx`:

```tsx
import type { TableBlockDto, TableRowDto } from "@/lib/api";

const NUMBER_RE = /^[+-]?\d+(?:[.,]\d+)?\s*$/;
const PERCENT_RE = /^[+-]?\d+(?:[.,]\d+)?\s*%$/;

type CellKind = "text" | "number" | "percent_delta";

function classify(cell: string): CellKind {
  const trimmed = cell.trim();
  if (PERCENT_RE.test(trimmed)) return "percent_delta";
  if (NUMBER_RE.test(trimmed)) return "number";
  return "text";
}

function parseNumber(cell: string): number | null {
  const n = Number(cell.trim().replace(",", "."));
  return Number.isFinite(n) ? n : null;
}

function formatNumber(cell: string): string {
  const n = parseNumber(cell);
  if (n === null) return cell;
  if (Number.isInteger(n)) return n.toLocaleString("es-AR");
  return n.toLocaleString("es-AR", { maximumFractionDigits: 2 });
}

function formatPercent(cell: string): { text: string; positive: boolean } {
  const n = Number(cell.trim().replace("%", "").replace(",", "."));
  return {
    text: cell.trim().startsWith("+") || n < 0
      ? `${n >= 0 ? "+" : ""}${n.toLocaleString("es-AR", { maximumFractionDigits: 2 })}%`
      : `+${n.toLocaleString("es-AR", { maximumFractionDigits: 2 })}%`,
    positive: n >= 0,
  };
}

const thStyle: React.CSSProperties = {
  padding: "14px 20px",
  fontSize: 11,
  fontWeight: 800,
  letterSpacing: "0.14em",
  textTransform: "uppercase",
  color: "var(--chirri-black)",
  background: "var(--chirri-paper)",
  borderBottom: "2px solid var(--chirri-black)",
};

const tdStyle: React.CSSProperties = {
  padding: "14px 20px",
  fontSize: 14,
  color: "var(--chirri-black)",
};

function renderCell(cell: string, isFirstCol: boolean, isHeader: boolean): React.ReactNode {
  const kind = classify(cell);
  if (isHeader) {
    return cell;
  }
  if (kind === "percent_delta") {
    const { text, positive } = formatPercent(cell);
    return (
      <span
        style={{
          fontWeight: 700,
          color: positive ? "var(--chirri-mint-deep)" : "var(--chirri-pink-deep)",
        }}
      >
        {text}
      </span>
    );
  }
  if (kind === "number") return formatNumber(cell);
  return cell;
}

function alignFor(cell: string, isHeader: boolean): "left" | "right" {
  if (isHeader) {
    // Header alignment matches the data column it labels — heuristic: first column left, others right.
    return "left"; // overridden per-column below
  }
  const kind = classify(cell);
  return kind === "text" ? "left" : "right";
}

function computeTotals(rows: TableRowDto[], colCount: number): string[] {
  const dataRows = rows.filter((r) => !r.is_header);
  const totals: string[] = [];
  for (let col = 0; col < colCount; col++) {
    if (col === 0) {
      totals.push("Total");
      continue;
    }
    let sum = 0;
    let summable = false;
    for (const r of dataRows) {
      const cell = r.cells[col] ?? "";
      const kind = classify(cell);
      if (kind === "number") {
        const n = parseNumber(cell);
        if (n !== null) {
          sum += n;
          summable = true;
        }
      }
    }
    totals.push(summable ? formatNumber(String(sum)) : "");
  }
  return totals;
}

export default function TableBlock({ block }: { block: TableBlockDto }) {
  const sorted = [...(block.rows ?? [])].sort((a, b) => a.order - b.order);
  if (sorted.length === 0) return null;

  const headerRows = sorted.filter((r) => r.is_header);
  const dataRows = sorted.filter((r) => !r.is_header);
  const colCount = Math.max(...sorted.map((r) => r.cells.length));
  const showTotal = block.show_total && dataRows.length > 0;
  const totals = showTotal ? computeTotals(sorted, colCount) : null;
  const title = block.title?.trim();

  return (
    <section style={{ marginBottom: 48 }}>
      {title && <span className="pill-title">{title.toUpperCase()}</span>}
      <div
        className="card"
        style={{
          marginTop: title ? 16 : 0,
          padding: 0,
          overflow: "hidden",
          background: "#fff",
        }}
      >
        <table style={{ width: "100%", borderCollapse: "collapse" }}>
          {headerRows.length > 0 && (
            <thead>
              {headerRows.map((r) => (
                <tr key={`h-${r.order}`}>
                  {Array.from({ length: colCount }).map((_, col) => {
                    const cell = r.cells[col] ?? "";
                    const align: "left" | "right" = col === 0 ? "left" : "right";
                    return (
                      <th
                        key={col}
                        scope="col"
                        style={{ ...thStyle, textAlign: align }}
                      >
                        {cell}
                      </th>
                    );
                  })}
                </tr>
              ))}
            </thead>
          )}
          <tbody>
            {dataRows.map((r, i) => (
              <tr
                key={`d-${r.order}`}
                style={{ borderTop: i > 0 ? "1px solid rgba(10,10,10,0.08)" : "none" }}
              >
                {Array.from({ length: colCount }).map((_, col) => {
                  const cell = r.cells[col] ?? "";
                  const align = alignFor(cell, false);
                  return (
                    <td
                      key={col}
                      style={{
                        ...tdStyle,
                        textAlign: align,
                        fontWeight: col === 0 ? 600 : 400,
                      }}
                    >
                      {renderCell(cell, col === 0, false)}
                    </td>
                  );
                })}
              </tr>
            ))}
            {showTotal && totals && (
              <tr
                style={{
                  borderTop: "2px solid var(--chirri-black)",
                  background: "var(--chirri-paper)",
                }}
              >
                {totals.map((cell, col) => (
                  <td
                    key={col}
                    style={{
                      ...tdStyle,
                      textAlign: col === 0 ? "left" : "right",
                      fontWeight: 800,
                    }}
                  >
                    {cell}
                  </td>
                ))}
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </section>
  );
}
```

- [ ] **Step 3: Registrar en `BlockRenderer.tsx`**

Editar `frontend/app/reports/[id]/blocks/BlockRenderer.tsx`:

```tsx
import type { ReportBlockDto } from "@/lib/api";
import TextImageBlock from "./TextImageBlock";
import ImageBlock from "./ImageBlock";
import KpiGridBlock from "./KpiGridBlock";
import MetricsTableBlock from "./MetricsTableBlock";
import TableBlock from "./TableBlock";
import TopContentsBlock from "./TopContentsBlock";
import TopCreatorsBlock from "./TopCreatorsBlock";
import AttributionTableBlock from "./AttributionTableBlock";
import ChartBlock from "./ChartBlock";

export default function BlockRenderer({ block }: { block: ReportBlockDto }) {
  switch (block.type) {
    case "TextImageBlock":
      return <TextImageBlock block={block} />;
    case "ImageBlock":
      return <ImageBlock block={block} />;
    case "KpiGridBlock":
      return <KpiGridBlock block={block} />;
    case "MetricsTableBlock":
      return <MetricsTableBlock block={block} />;
    case "TableBlock":
      return <TableBlock block={block} />;
    case "TopContentsBlock":
      return <TopContentsBlock block={block} />;
    case "TopCreatorsBlock":
      return <TopCreatorsBlock block={block} />;
    case "AttributionTableBlock":
      return <AttributionTableBlock block={block} />;
    case "ChartBlock":
      return <ChartBlock block={block} />;
    default: {
      const _exhaustive: never = block;
      console.warn("unknown_block_type", (_exhaustive as { type: string }).type);
      return null;
    }
  }
}
```

- [ ] **Step 4: Verificar typecheck del frontend**

Run: `docker compose exec frontend npx tsc --noEmit`
Expected: 0 errors.

- [ ] **Step 5: Commit**

```bash
git add frontend/lib/api.ts \
        frontend/app/reports/[id]/blocks/TableBlock.tsx \
        frontend/app/reports/[id]/blocks/BlockRenderer.tsx
git commit -m "feat(reports): add TableBlock frontend renderer"
```

---

## Task 5: Backend — actualizar `seed_demo` para usar `TableBlock`

**Files:**
- Modify: `backend/apps/tenants/management/commands/seed_demo.py`
- Test: `backend/tests/unit/test_seed_demo.py` (extender o ajustar)

- [ ] **Step 1: Leer las funciones afectadas para preservar contexto**

Run: `grep -n "MetricsTable\|AttributionTable\|OneLink" backend/apps/tenants/management/commands/seed_demo.py`
(Ya identificado: cubre `_seed_blocks_marzo_educacion` y `_seed_blocks_abril`.)

- [ ] **Step 2: Reemplazar `MetricsTableBlock` cross-network "Mes a mes" en abril**

Editar `backend/apps/tenants/management/commands/seed_demo.py`. Reemplazar este bloque:

```python
    # 3) MetricsTableBlock — cross-network (Mes a mes)
    mtm = MetricsTableBlock.objects.create(
        report=report, order=3, title="Mes a mes", network=None,
    )
    MetricsTableRow.objects.bulk_create([
        MetricsTableRow(metrics_table_block=mtm, order=1,
                        metric_name="engagement_rate", value=Decimal("5.3"),
                        source_type=SourceType.ORGANIC,
                        period_comparison=Decimal("0.5")),
        MetricsTableRow(metrics_table_block=mtm, order=2,
                        metric_name="followers_gained", value=Decimal("21300"),
                        source_type=SourceType.ORGANIC,
                        period_comparison=Decimal("15.7")),
        MetricsTableRow(metrics_table_block=mtm, order=3,
                        metric_name="app_downloads", value=Decimal("310"),
                        source_type=SourceType.INFLUENCER,
                        period_comparison=Decimal("32")),
    ])
```

por:

```python
    # 3) TableBlock — cross-network (Mes a mes)
    mtm = TableBlock.objects.create(
        report=report, order=3, title="Mes a mes",
    )
    TableRow.objects.bulk_create([
        TableRow(table_block=mtm, order=1, is_header=True,
                 cells=["Métrica", "Valor", "Δ"]),
        TableRow(table_block=mtm, order=2,
                 cells=["ORGANIC · engagement_rate", "5.3", "+0.5%"]),
        TableRow(table_block=mtm, order=3,
                 cells=["ORGANIC · followers_gained", "21300", "+15.7%"]),
        TableRow(table_block=mtm, order=4,
                 cells=["INFLUENCER · app_downloads", "310", "+32%"]),
    ])
```

- [ ] **Step 3: Reemplazar `MetricsTableBlock` Instagram en abril**

Reemplazar:

```python
    # 4) MetricsTableBlock — Instagram
    ig = MetricsTableBlock.objects.create(
        report=report, order=4, title="Instagram", network=Network.INSTAGRAM,
    )
    MetricsTableRow.objects.bulk_create([
        MetricsTableRow(metrics_table_block=ig, order=1,
                        metric_name="reach", value=Decimal("312000"),
                        source_type=SourceType.ORGANIC,
                        period_comparison=Decimal("9.9")),
        MetricsTableRow(metrics_table_block=ig, order=2,
                        metric_name="reach", value=Decimal("594000"),
                        source_type=SourceType.PAID,
                        period_comparison=Decimal("16.0")),
        MetricsTableRow(metrics_table_block=ig, order=3,
                        metric_name="reach", value=Decimal("1810000"),
                        source_type=SourceType.INFLUENCER,
                        period_comparison=Decimal("10.4")),
    ])
```

por:

```python
    # 4) TableBlock — Instagram
    ig = TableBlock.objects.create(
        report=report, order=4, title="Instagram",
    )
    TableRow.objects.bulk_create([
        TableRow(table_block=ig, order=1, is_header=True,
                 cells=["Métrica", "Valor", "Δ"]),
        TableRow(table_block=ig, order=2,
                 cells=["ORGANIC · reach", "312000", "+9.9%"]),
        TableRow(table_block=ig, order=3,
                 cells=["PAID · reach", "594000", "+16%"]),
        TableRow(table_block=ig, order=4,
                 cells=["INFLUENCER · reach", "1810000", "+10.4%"]),
    ])
```

- [ ] **Step 4: Reemplazar `AttributionTableBlock` en abril**

Reemplazar:

```python
    # 7) AttributionTableBlock
    AttributionTableBlock.objects.create(
        report=report, order=7, title="Atribución OneLink", show_total=True,
    )
```

por:

```python
    # 7) TableBlock — Atribución OneLink (las rows se llenan en _seed_demo_data)
    TableBlock.objects.create(
        report=report, order=7, title="Atribución OneLink", show_total=True,
    )
```

- [ ] **Step 5: Reemplazar las 4 `MetricsTableBlock` de marzo (Mes a mes / IG / TikTok / X)**

Hacer el mismo reemplazo en el bloque `_seed_blocks_marzo_educacion` (líneas ~599–661 del archivo). Patrón de reemplazo: cada `MetricsTableBlock.objects.create(...)` + `MetricsTableRow.objects.bulk_create([...])` se vuelve `TableBlock.objects.create(...)` + `TableRow.objects.bulk_create([header, ...rows])`. El `metric_name` se concatena con el `source_type` en la celda 0 (`f"{source_type} · {metric_name}"`), el value pasa a celda 1 como string, y el `period_comparison` (si existe) pasa a celda 2 como `f"+{n}%"`.

Ejemplo concreto para "Mes a mes" marzo:

```python
    # 2) TableBlock — Mes a mes (cross-network, sin red asignada)
    mtm = TableBlock.objects.create(
        report=report, order=2, title="Mes a mes",
    )
    TableRow.objects.bulk_create([
        TableRow(table_block=mtm, order=1, is_header=True,
                 cells=["Métrica", "Valor", "Δ"]),
        TableRow(table_block=mtm, order=2,
                 cells=["ORGANIC · engagement_rate", "4.8", "+0.3%"]),
        TableRow(table_block=mtm, order=3,
                 cells=["ORGANIC · followers_gained", "18400", "+24%"]),
    ])
```

Aplicar el mismo patrón a IG (orden 3), TikTok (orden 4), y X (orden 5). Para las filas sin `period_comparison`, dejar la celda Δ vacía (`""`).

- [ ] **Step 6: Reemplazar el seeder de `OneLinkAttribution` por filas de `TableBlock`**

En `_seed_demo_data` (cerca de línea 388), eliminar el loop que crea `OneLinkAttribution`. La nueva lógica busca el `TableBlock` con título "Atribución OneLink" y popula sus rows:

Reemplazar:

```python
        onelink_specs = [
            ("@pasaje.en.mano", 1200, 180),
            ("@financierapopular", 800, 95),
            ("@pymes_ar", 400, 30),
        ]
```

(no cambia)

Y reemplazar el bloque que llama a `AttributionTableBlock.objects.filter(...)` y crea `OneLinkAttribution`:

```python
            attribution_block = AttributionTableBlock.objects.filter(
                report=report,
            ).first()
            ...
            if attribution_block is not None:
                OneLinkAttribution.objects.filter(attribution_block=attribution_block).delete()
            ...
            if attribution_block is not None:
                for handle, clicks, downloads in onelink_specs:
                    OneLinkAttribution.objects.create(
                        attribution_block=attribution_block,
                        influencer_handle=handle,
                        clicks=clicks,
                        app_downloads=downloads,
                    )
```

por:

```python
            onelink_block = TableBlock.objects.filter(
                report=report, title="Atribución OneLink",
            ).first()
            ...
            if onelink_block is not None:
                onelink_block.rows.all().delete()
                TableRow.objects.bulk_create([
                    TableRow(table_block=onelink_block, order=1, is_header=True,
                             cells=["Influencer", "Clicks", "Descargas"]),
                    *[
                        TableRow(
                            table_block=onelink_block,
                            order=i + 2,
                            cells=[handle, str(clicks), str(downloads)],
                        )
                        for i, (handle, clicks, downloads) in enumerate(onelink_specs)
                    ],
                ])
```

(El `...` indica las líneas adyacentes que no cambian — preservar el orden de los demás bloques en el if-cascade.)

- [ ] **Step 7: Actualizar imports**

Al inicio de `seed_demo.py`, en el import desde `apps.reports.models`, agregar `TableBlock, TableRow` y dejar `MetricsTableBlock, MetricsTableRow, AttributionTableBlock, OneLinkAttribution` por ahora (se sacarán en Task 7). Resultado:

```python
from apps.reports.models import (
    AttributionTableBlock,
    BrandFollowerSnapshot,
    ChartBlock,
    ChartDataPoint,
    ImageBlock,
    KpiGridBlock,
    KpiTile,
    MetricsTableBlock,
    MetricsTableRow,
    OneLinkAttribution,
    Report,
    ReportAttachment,
    TableBlock,
    TableRow,
    TextImageBlock,
    TopContentsBlock,
    TopContentItem,
    TopCreatorsBlock,
    TopCreatorItem,
)
```

- [ ] **Step 8: Reseed local DB**

Run: `docker compose exec backend python manage.py flush --no-input && docker compose exec backend python manage.py migrate && docker compose exec backend python manage.py seed_demo`
Expected: `seed_demo` corre sin errores.

- [ ] **Step 9: Correr el test del seed**

Run: `docker compose exec backend pytest backend/tests/unit/test_seed_demo.py -v`
Expected: PASS. Si el test asserta sobre `MetricsTableBlock`/`AttributionTableBlock`/`OneLinkAttribution` específicamente, ajustar para que asserte sobre `TableBlock`/`TableRow` con los títulos correctos. Verificar leyendo el test antes de editar.

- [ ] **Step 10: Probar visualmente en el navegador**

Levantar el dev stack si no está corriendo:

Run: `docker compose up -d`

Abrir `http://localhost:3000/reports` con login `demo@chirripeppers.com` / `demo2026`, navegar al reporte de Abril, y verificar visualmente que las tablas (Mes a mes, IG, TikTok, X, Atribución OneLink) renderean igual que las imágenes de referencia: pill title arriba, columnas alineadas, deltas verde/rojo, primera columna en bold, total en la atribución.

Si algo se ve mal, fix en `TableBlock.tsx` antes de seguir.

- [ ] **Step 11: Commit**

```bash
git add backend/apps/tenants/management/commands/seed_demo.py
git commit -m "feat(reports): seed_demo emits TableBlock for metrics/attribution"
```

---

## Task 6: Backend — unificar importer schema en una hoja `Tables`

**Files:**
- Modify: `backend/apps/reports/importers/schema.py`
- Modify: `backend/apps/reports/importers/excel_parser.py`
- Modify: `backend/apps/reports/importers/builder.py`
- Modify: `backend/apps/reports/importers/excel_exporter.py`
- Modify: `backend/apps/reports/importers/excel_writer.py`
- Test: `backend/tests/unit/test_excel_parser.py` (ajustar)
- Test: `backend/tests/unit/test_excel_writer.py` (ajustar)

- [ ] **Step 1: Modificar `schema.py` — agregar Tables, sacar MetricsTables/Attribution**

Editar `backend/apps/reports/importers/schema.py`:

Reemplazar:

```python
SHEET_METRICSTABLES = "MetricsTables"
SHEET_TOPCONTENTS = "TopContents"
SHEET_TOPCREATORS = "TopCreators"
SHEET_ATTRIBUTION = "Attribution"
SHEET_CHARTS = "Charts"

SHEETS_IN_ORDER = [
    SHEET_INSTRUCCIONES,
    SHEET_REPORTE,
    SHEET_TEXTIMAGE,
    SHEET_IMAGENES,
    SHEET_KPIS,
    SHEET_METRICSTABLES,
    SHEET_TOPCONTENTS,
    SHEET_TOPCREATORS,
    SHEET_ATTRIBUTION,
    SHEET_CHARTS,
]
```

por:

```python
SHEET_TABLES = "Tables"
SHEET_TOPCONTENTS = "TopContents"
SHEET_TOPCREATORS = "TopCreators"
SHEET_CHARTS = "Charts"

SHEETS_IN_ORDER = [
    SHEET_INSTRUCCIONES,
    SHEET_REPORTE,
    SHEET_TEXTIMAGE,
    SHEET_IMAGENES,
    SHEET_KPIS,
    SHEET_TABLES,
    SHEET_TOPCONTENTS,
    SHEET_TOPCREATORS,
    SHEET_CHARTS,
]
```

Reemplazar `METRICSTABLES_HEADERS` y `ATTRIBUTION_HEADERS`:

```python
METRICSTABLES_HEADERS = [
    "nombre", "block_title", "block_network", "item_orden",
    "metric_name", "value", "source_type", "period_comparison",
]
...
ATTRIBUTION_HEADERS = [
    "nombre", "block_title", "block_show_total",
    "item_orden", "handle", "clicks", "app_downloads",
]
```

por:

```python
TABLES_HEADERS = [
    "nombre", "block_title", "block_show_total",
    "row_orden", "is_header",
    "cell_1", "cell_2", "cell_3", "cell_4",
    "cell_5", "cell_6", "cell_7", "cell_8",
]

TABLE_CELL_COLS = [f"cell_{i}" for i in range(1, 9)]
```

En `SHEET_HEADERS`, reemplazar las dos entradas legacy por la nueva:

```python
SHEET_HEADERS = {
    SHEET_TEXTIMAGE: TEXTIMAGE_HEADERS,
    SHEET_IMAGENES: IMAGENES_HEADERS,
    SHEET_KPIS: KPIS_HEADERS,
    SHEET_TABLES: TABLES_HEADERS,
    SHEET_TOPCONTENTS: TOPCONTENTS_HEADERS,
    SHEET_TOPCREATORS: TOPCREATORS_HEADERS,
    SHEET_CHARTS: CHARTS_HEADERS,
}
```

En `DROPDOWNS`, sacar las entradas legacy y agregar:

```python
DROPDOWNS = {
    (SHEET_REPORTE, "tipo"): list(KIND_LABELS.values()),
    (SHEET_TEXTIMAGE, "image_position"): IMAGE_POSITION_VALUES,
    (SHEET_TEXTIMAGE, "columns"): COLUMNS_VALUES,
    (SHEET_TABLES, "block_show_total"): BOOL_VALUES,
    (SHEET_TABLES, "is_header"): BOOL_VALUES,
    (SHEET_TOPCONTENTS, "block_network"): _NETWORK_BLANK,
    (SHEET_TOPCONTENTS, "source_type"): _SOURCE_BLANK,
    (SHEET_TOPCREATORS, "block_network"): _NETWORK_BLANK,
    (SHEET_CHARTS, "block_network"): _NETWORK_BLANK,
    (SHEET_CHARTS, "chart_type"): CHART_TYPE_VALUES,
}
```

En `TYPE_PREFIX`, reemplazar las dos entradas:

```python
TYPE_PREFIX = {
    "TextImageBlock": "textimage",
    "ImageBlock": "imagen",
    "KpiGridBlock": "kpi",
    "TableBlock": "table",
    "TopContentsBlock": "topcontents",
    "TopCreatorsBlock": "topcreators",
    "ChartBlock": "chart",
}
```

- [ ] **Step 2: Modificar `excel_parser.py` — agregar `_parse_tables`, sacar legacy**

Editar `backend/apps/reports/importers/excel_parser.py`. Reemplazar las funciones `_parse_metricstables` y `_parse_attribution` por una única `_parse_tables`:

```python
def _parse_tables(ws: Worksheet) -> tuple[list[ParsedBlock], list[ImporterError]]:
    """Parser de la hoja Tables: agrupa filas por 'nombre', cada fila es una row.

    block_title + block_show_total deben ser consistentes entre filas del mismo
    block. Las celdas se leen de cell_1..cell_8 y se truncan al último no-vacío.
    """
    errors: list[ImporterError] = []
    groups: dict[str, dict] = {}

    for row_idx, row in _iter_data_rows(ws, s.TABLES_HEADERS):
        nombre = _valid_nombre(row, s.SHEET_TABLES, row_idx, errors)
        if nombre is None:
            continue

        block_title = _str(row.get("block_title"))
        block_show_total = _coerce_bool(row.get("block_show_total"))
        is_header = _coerce_bool(row.get("is_header"))
        row_orden = _coerce_int(row.get("row_orden"))
        if row_orden is None or row_orden < 1:
            errors.append(ImporterError(
                sheet=s.SHEET_TABLES, row=row_idx, column="row_orden",
                reason=f"entero ≥ 1 esperado, recibí '{row.get('row_orden')}'",
            ))
            continue

        cells_raw = [row.get(col) for col in s.TABLE_CELL_COLS]
        # Truncar después del último no-vacío.
        last_non_blank = -1
        for i, v in enumerate(cells_raw):
            if not _is_blank(v):
                last_non_blank = i
        cells = [_str(v) for v in cells_raw[: last_non_blank + 1]]

        if nombre not in groups:
            groups[nombre] = {
                "title": block_title,
                "show_total": block_show_total,
                "rows": [],
            }
        else:
            existing = groups[nombre]
            if existing["title"] != block_title:
                errors.append(ImporterError(
                    sheet=s.SHEET_TABLES, row=row_idx, column="block_title",
                    reason=(
                        f"valor '{block_title}' difiere del usado antes para "
                        f"'{nombre}' ('{existing['title']}'). "
                        "Los block_* fields deben ser idénticos en todas las filas."
                    ),
                ))
            if existing["show_total"] != block_show_total:
                errors.append(ImporterError(
                    sheet=s.SHEET_TABLES, row=row_idx, column="block_show_total",
                    reason=(
                        f"valor '{block_show_total}' difiere del usado antes para "
                        f"'{nombre}' ('{existing['show_total']}')."
                    ),
                ))
        groups[nombre]["rows"].append({
            "row_orden": row_orden,
            "is_header": is_header,
            "cells": cells,
        })

    result = [
        ParsedBlock(
            type_name="TableBlock",
            nombre=nombre,
            fields={
                "block_title": data["title"],
                "block_show_total": data["show_total"],
            },
            items=sorted(data["rows"], key=lambda r: r["row_orden"]),
        )
        for nombre, data in groups.items()
    ]
    return result, errors
```

Y reemplazar el dict `_BLOCK_PARSERS`:

```python
_BLOCK_PARSERS: dict[str, Callable[[Worksheet], tuple[list[ParsedBlock], list[ImporterError]]]] = {
    s.SHEET_TEXTIMAGE: _parse_textimage,
    s.SHEET_IMAGENES: _parse_imagenes,
    s.SHEET_KPIS: _parse_kpis,
    s.SHEET_TABLES: _parse_tables,
    s.SHEET_TOPCONTENTS: _parse_topcontents,
    s.SHEET_TOPCREATORS: _parse_topcreators,
    s.SHEET_CHARTS: _parse_charts,
}
```

Eliminar las funciones `_parse_metricstables` y `_parse_attribution` (ya no se usan).

- [ ] **Step 3: Modificar `builder.py` — agregar `_build_tables`, sacar legacy**

Editar `backend/apps/reports/importers/builder.py`. En el import de `apps.reports.models`, sacar `AttributionTableBlock`, `MetricsTableBlock`, `MetricsTableRow`, `OneLinkAttribution`, agregar `TableBlock`, `TableRow`. Resultado:

```python
from apps.reports.models import (
    ChartBlock,
    ChartDataPoint,
    ImageBlock,
    KpiGridBlock,
    KpiTile,
    Report,
    TableBlock,
    TableRow,
    TextImageBlock,
    TopContentItem,
    TopContentsBlock,
    TopCreatorItem,
    TopCreatorsBlock,
)
```

Reemplazar las funciones `_build_metricstables` y `_build_attribution` por:

```python
def _build_tables(report, order, pb: ParsedBlock, images):
    block = TableBlock.objects.create(
        report=report, order=order,
        title=pb.fields["block_title"],
        show_total=pb.fields.get("block_show_total", False),
    )
    TableRow.objects.bulk_create([
        TableRow(
            table_block=block,
            order=item["row_orden"],
            is_header=item.get("is_header", False),
            cells=item["cells"],
        )
        for item in pb.items
    ])
```

Y actualizar el dict `_BUILDERS`:

```python
_BUILDERS = {
    "TextImageBlock": _build_textimage,
    "ImageBlock": _build_imagen,
    "KpiGridBlock": _build_kpis,
    "TableBlock": _build_tables,
    "TopContentsBlock": _build_topcontents,
    "TopCreatorsBlock": _build_topcreators,
    "ChartBlock": _build_chart,
}
```

- [ ] **Step 4: Modificar `excel_exporter.py` — agregar `_populate_tables`, sacar legacy**

Editar `backend/apps/reports/importers/excel_exporter.py`. Updated imports:

```python
from apps.reports.models import (
    ChartBlock,
    ImageBlock,
    KpiGridBlock,
    Report,
    TableBlock,
    TextImageBlock,
    TopContentsBlock,
    TopCreatorsBlock,
)
```

Reemplazar la llamada a las dos funciones de populate en `export()`:

```python
def export(report: Report) -> BytesIO:
    """Serializa `report` al mismo xlsx que produciría el importer."""
    wb = build_skeleton()
    names = _assign_names(report)

    _populate_reporte(wb[s.SHEET_REPORTE], report, names)
    _populate_textimage(wb[s.SHEET_TEXTIMAGE], report, names)
    _populate_imagenes(wb[s.SHEET_IMAGENES], report, names)
    _populate_kpis(wb[s.SHEET_KPIS], report, names)
    _populate_tables(wb[s.SHEET_TABLES], report, names)
    _populate_topcontents(wb[s.SHEET_TOPCONTENTS], report, names)
    _populate_topcreators(wb[s.SHEET_TOPCREATORS], report, names)
    _populate_charts(wb[s.SHEET_CHARTS], report, names)

    return to_bytes(wb)
```

Reemplazar `_populate_metricstables` y `_populate_attribution` por:

```python
def _populate_tables(
    ws: Worksheet, report: Report, names: dict[int, str]
) -> None:
    row = 2
    for block in TableBlock.objects.filter(report=report).order_by("order"):
        for r in block.rows.all().order_by("order"):
            cells_padded = list(r.cells) + [""] * (8 - len(r.cells))
            values = {
                "nombre": names[block.pk],
                "block_title": block.title,
                "block_show_total": "TRUE" if block.show_total else "FALSE",
                "row_orden": r.order,
                "is_header": "TRUE" if r.is_header else "FALSE",
            }
            for i, cell in enumerate(cells_padded[:8], start=1):
                values[f"cell_{i}"] = cell
            _write_row(ws, row, s.TABLES_HEADERS, values)
            row += 1
```

- [ ] **Step 5: Actualizar `excel_writer.py` (texto de Instrucciones)**

Editar `backend/apps/reports/importers/excel_writer.py`. Buscar las menciones a `MetricsTables` y `Attribution` y reemplazarlas por `Tables`. La sección `_INSTRUCCIONES_SECTIONS` actualizada en la línea 197:

```python
            "· Hojas con sub-items (Kpis, Tables, TopContents, TopCreators, Charts): los campos del parent (ej. block_title) se repiten en cada row del item. Agrupamos por 'nombre'.",
```

Y agregar una línea explicando la hoja `Tables`:

```python
            "· Hoja Tables: tabla genérica con cell_1..cell_8 (variables, dejá vacíos los que no usás). is_header=TRUE marca filas de encabezado. block_show_total=TRUE agrega una fila Total al final con la suma de las columnas numéricas.",
```

(Insertarlo dentro de la lista de líneas de la sección "A. Cómo llenar el Excel", justo después de la línea sobre hojas con sub-items.)

En la sección "D. Para LLMs / scripts", actualizar el bullet de enums:

```python
            "· Enums: 'tipo' ∈ {Influencer, General, Quincenal, Mensual, Cierre de etapa}. 'block_network' ∈ {Instagram, TikTok, X, (vacío)}. 'source_type' ∈ {Orgánico, Influencer, Pauta, (vacío)}. 'image_position' ∈ {left, right, top}. 'chart_type' ∈ {bar, line}. 'block_show_total' ∈ {TRUE, FALSE}. 'is_header' ∈ {TRUE, FALSE}.",
```

- [ ] **Step 6: Actualizar tests del importer**

Run: `docker compose exec backend pytest backend/tests/unit/test_excel_writer.py backend/tests/unit/test_excel_parser.py -v`
Expected: muchos tests fallan (esperan hojas legacy).

Editar los tests para que esperen la hoja `Tables` en vez de `MetricsTables`/`Attribution`. Patrón:
- Donde el test crea fixtures de `MetricsTableBlock`/`AttributionTableBlock`, reemplazar por `TableBlock` con rows planas.
- Donde el test verifica nombres de hojas o headers, reemplazar `SHEET_METRICSTABLES` y `SHEET_ATTRIBUTION` por `SHEET_TABLES`.
- Asserts sobre headers: usar `s.TABLES_HEADERS`.

Ejecutar el suite hasta verde:

Run: `docker compose exec backend pytest backend/tests/unit/test_excel_writer.py backend/tests/unit/test_excel_parser.py -v`
Expected: PASS.

- [ ] **Step 7: Test de roundtrip explícito**

Agregar a `backend/tests/unit/test_excel_parser.py` (o crear `test_excel_roundtrip_table.py` si preferís archivo nuevo):

```python
@pytest.mark.django_db
def test_table_block_roundtrip_export_then_parse():
    """Exportar un report con TableBlock y volverlo a parsear devuelve la misma estructura."""
    from apps.reports.models import TableBlock, TableRow
    from apps.reports.importers.excel_exporter import export
    from apps.reports.importers.excel_parser import parse
    from apps.reports.tests.factories import make_report

    report = make_report()
    block = TableBlock.objects.create(
        report=report, order=1, title="IG", show_total=True,
    )
    TableRow.objects.bulk_create([
        TableRow(table_block=block, order=1, is_header=True,
                 cells=["Métrica", "Valor", "Δ"]),
        TableRow(table_block=block, order=2,
                 cells=["ORGANIC · reach", "312000", "+9.9%"]),
    ])

    xlsx_bytes = export(report).getvalue()
    parsed, errors = parse(xlsx_bytes)
    assert errors == []
    assert parsed is not None

    table_blocks = [b for b in parsed.blocks.values() if b.type_name == "TableBlock"]
    assert len(table_blocks) == 1
    pb = table_blocks[0]
    assert pb.fields["block_title"] == "IG"
    assert pb.fields["block_show_total"] is True
    assert len(pb.items) == 2
    assert pb.items[0]["is_header"] is True
    assert pb.items[0]["cells"] == ["Métrica", "Valor", "Δ"]
    assert pb.items[1]["cells"] == ["ORGANIC · reach", "312000", "+9.9%"]
```

Run: `docker compose exec backend pytest backend/tests/unit/test_excel_parser.py::test_table_block_roundtrip_export_then_parse -v`
Expected: PASS.

- [ ] **Step 8: Probar el importer admin manualmente**

En el admin, descargar un xlsx ejemplo (`/admin/reports/report/download-example/<id>/` para el reporte de Abril seedeado), abrirlo, verificar que la hoja `Tables` está y tiene las rows esperadas. Volver a subirlo desde `/admin/reports/report/import/` con el stage correcto y confirmar que el reporte resultante tiene las mismas tablas que el original.

Si algo falla acá, fix en el parser/exporter.

- [ ] **Step 9: Commit**

```bash
git add backend/apps/reports/importers/ \
        backend/tests/unit/test_excel_writer.py \
        backend/tests/unit/test_excel_parser.py
git commit -m "feat(reports): unify importer Tables sheet (drop MetricsTables + Attribution)"
```

---

## Task 7: Drop legacy models, FE components, tests

**Files:**
- Delete: `backend/apps/reports/models/blocks/metrics_table.py`
- Delete: `backend/apps/reports/models/blocks/attribution.py`
- Delete: `backend/apps/reports/models/onelink_attribution.py`
- Delete: `backend/tests/unit/blocks/test_metrics_table_block.py`
- Delete: `backend/tests/unit/blocks/test_attribution_table_block.py`
- Delete: `backend/tests/unit/test_onelink_attribution_block_fk.py`
- Delete: `frontend/app/reports/[id]/blocks/MetricsTableBlock.tsx`
- Delete: `frontend/app/reports/[id]/blocks/AttributionTableBlock.tsx`
- Modify: `backend/apps/reports/models/__init__.py`
- Modify: `backend/apps/reports/serializers.py`
- Modify: `backend/apps/reports/admin.py`
- Modify: `backend/apps/tenants/management/commands/seed_demo.py`
- Modify: `frontend/lib/api.ts`
- Modify: `frontend/app/reports/[id]/blocks/BlockRenderer.tsx`
- Create: `backend/apps/reports/migrations/0021_drop_legacy_table_blocks.py` (auto-generada)

- [ ] **Step 1: Remover los archivos de modelos legacy**

```bash
rm backend/apps/reports/models/blocks/metrics_table.py \
   backend/apps/reports/models/blocks/attribution.py \
   backend/apps/reports/models/onelink_attribution.py
```

- [ ] **Step 2: Sacar imports en `models/__init__.py`**

Editar `backend/apps/reports/models/__init__.py` y dejar:

```python
"""Reports domain models — package post-DEV-116 (split por concern)."""
from .report import Report  # noqa: F401
from .follower_snapshot import BrandFollowerSnapshot  # noqa: F401

# Typed blocks:
from .blocks.base_block import ReportBlock  # noqa: F401
from .blocks.text_image import TextImageBlock  # noqa: F401
from .blocks.image import ImageBlock  # noqa: F401
from .blocks.kpi_grid import KpiGridBlock, KpiTile  # noqa: F401
from .blocks.table import TableBlock, TableRow  # noqa: F401
from .blocks.top_contents import TopContentsBlock, TopContentItem  # noqa: F401
from .blocks.top_creators import TopCreatorsBlock, TopCreatorItem  # noqa: F401
from .blocks.chart import ChartBlock, ChartDataPoint  # noqa: F401

# Attachments (DEV-108):
from .attachments import ReportAttachment  # noqa: F401
```

- [ ] **Step 3: Sacar imports + serializers + dispatcher entries en `serializers.py`**

Editar `backend/apps/reports/serializers.py`. Sacar:
- import de `MetricsTableBlock, MetricsTableRow, AttributionTableBlock, OneLinkAttribution`
- clases `MetricsTableRowSerializer`, `OneLinkEntrySerializer`, `MetricsTableBlockSerializer`, `AttributionTableBlockSerializer`
- entradas en `_BLOCK_SERIALIZERS` para `MetricsTableBlock` y `AttributionTableBlock`

El dict resultante:

```python
_BLOCK_SERIALIZERS = {
    TextImageBlock: TextImageBlockSerializer,
    ImageBlock: ImageBlockSerializer,
    KpiGridBlock: KpiGridBlockSerializer,
    TableBlock: TableBlockSerializer,
    TopContentsBlock: TopContentsBlockSerializer,
    TopCreatorsBlock: TopCreatorsBlockSerializer,
    ChartBlock: ChartBlockSerializer,
}
```

- [ ] **Step 4: Sacar admin entries**

Editar `backend/apps/reports/admin.py`. Sacar:
- import de `MetricsTableBlock, MetricsTableRow, AttributionTableBlock, OneLinkAttribution`
- clases `MetricsTableRowInline`, `OneLinkAttributionInline`
- child inlines `MetricsTableBlockInline` y `AttributionTableBlockInline` dentro de `ReportBlockInline`
- entradas en `child_inlines` y `child_models` de `ReportBlockInline` y `ReportBlockAdmin`
- las clases `MetricsTableBlockAdmin` y `AttributionTableBlockAdmin` (con sus `@admin.register` decoradores)

- [ ] **Step 5: Sacar referencias en `seed_demo.py`**

Editar el import:

```python
from apps.reports.models import (
    BrandFollowerSnapshot,
    ChartBlock,
    ChartDataPoint,
    ImageBlock,
    KpiGridBlock,
    KpiTile,
    Report,
    ReportAttachment,
    TableBlock,
    TableRow,
    TextImageBlock,
    TopContentsBlock,
    TopContentItem,
    TopCreatorsBlock,
    TopCreatorItem,
)
```

(Con `MetricsTableBlock`, `MetricsTableRow`, `AttributionTableBlock`, `OneLinkAttribution` sacados.)

- [ ] **Step 6: Sacar DTOs legacy en `frontend/lib/api.ts`**

Editar `frontend/lib/api.ts`. Sacar:
- `MetricsTableRowDto`
- `OneLinkEntryDto`
- `MetricsTableBlockDto`
- `AttributionTableBlockDto`
- las entradas correspondientes en la unión `ReportBlockDto`

Resultado de la unión:

```typescript
export type ReportBlockDto =
  | TextImageBlockDto
  | ImageBlockDto
  | KpiGridBlockDto
  | TableBlockDto
  | TopContentsBlockDto
  | TopCreatorsBlockDto
  | ChartBlockDto;
```

- [ ] **Step 7: Sacar componentes legacy y referencias en `BlockRenderer.tsx`**

Editar `frontend/app/reports/[id]/blocks/BlockRenderer.tsx`:

```tsx
import type { ReportBlockDto } from "@/lib/api";
import TextImageBlock from "./TextImageBlock";
import ImageBlock from "./ImageBlock";
import KpiGridBlock from "./KpiGridBlock";
import TableBlock from "./TableBlock";
import TopContentsBlock from "./TopContentsBlock";
import TopCreatorsBlock from "./TopCreatorsBlock";
import ChartBlock from "./ChartBlock";

export default function BlockRenderer({ block }: { block: ReportBlockDto }) {
  switch (block.type) {
    case "TextImageBlock":
      return <TextImageBlock block={block} />;
    case "ImageBlock":
      return <ImageBlock block={block} />;
    case "KpiGridBlock":
      return <KpiGridBlock block={block} />;
    case "TableBlock":
      return <TableBlock block={block} />;
    case "TopContentsBlock":
      return <TopContentsBlock block={block} />;
    case "TopCreatorsBlock":
      return <TopCreatorsBlock block={block} />;
    case "ChartBlock":
      return <ChartBlock block={block} />;
    default: {
      const _exhaustive: never = block;
      console.warn("unknown_block_type", (_exhaustive as { type: string }).type);
      return null;
    }
  }
}
```

Y borrar los archivos:

```bash
rm "frontend/app/reports/[id]/blocks/MetricsTableBlock.tsx" \
   "frontend/app/reports/[id]/blocks/AttributionTableBlock.tsx"
```

- [ ] **Step 8: Borrar tests legacy**

```bash
rm backend/tests/unit/blocks/test_metrics_table_block.py \
   backend/tests/unit/blocks/test_attribution_table_block.py \
   backend/tests/unit/test_onelink_attribution_block_fk.py
```

Si queda alguna referencia residual a `MetricsTableBlock`/`AttributionTableBlock`/`OneLinkAttribution` en otros tests (`test_polymorphic_serializer.py`, `test_polymorphic_prefetch.py`, `test_admin_polymorphic.py`, `test_legacy_models_gone.py`, `test_seed_demo.py`, `test_reports_api.py`, `conftest.py`), ajustarlas para apuntar a `TableBlock`/`TableRow`. Buscar referencias:

Run: `grep -rn "MetricsTableBlock\|AttributionTableBlock\|OneLinkAttribution\|MetricsTableRow" backend/tests/ backend/apps/`
Expected: 0 matches después de los ajustes.

- [ ] **Step 9: Generar la migración de drop**

Run: `docker compose exec backend python manage.py makemigrations reports --name drop_legacy_table_blocks`
Expected: `0021_drop_legacy_table_blocks.py` creado con `DeleteModel` para `MetricsTableBlock`, `MetricsTableRow`, `AttributionTableBlock`, `OneLinkAttribution`.

- [ ] **Step 10: Aplicar la migración**

Run: `docker compose exec backend python manage.py migrate reports`
Expected: `Applying reports.0021_drop_legacy_table_blocks... OK`

- [ ] **Step 11: Verificar typecheck del frontend y system check del backend**

Run paralelo:
- `docker compose exec frontend npx tsc --noEmit`
- `docker compose exec backend python manage.py check`

Expected: ambos sin errores.

- [ ] **Step 12: Commit**

```bash
git add backend/apps/reports/ backend/tests/ backend/apps/tenants/ \
        frontend/lib/api.ts frontend/app/reports/
git commit -m "refactor(reports): drop legacy MetricsTableBlock + AttributionTableBlock + OneLinkAttribution"
```

---

## Task 8: Reseed + correr suite completo

**Files:** none (verification only)

- [ ] **Step 1: Reseed dev DB clean**

Run: `docker compose exec backend python manage.py flush --no-input && docker compose exec backend python manage.py migrate && docker compose exec backend python manage.py seed_demo`
Expected: completa sin errores; reportes seedeados.

- [ ] **Step 2: Correr unit tests**

Run: `npm run test:unit`
Expected: PASS.

- [ ] **Step 3: Correr e2e smoke**

Run: `npm run test:e2e:smoke`
Expected: PASS. Si algún assert depende de texto de OneLink/MetricsTable que cambió, ajustar el test E2E para que asserte sobre el nuevo render (los textos visibles "INSTAGRAM", "ATRIBUCIÓN ONELINK", "ORGANIC · reach", "@pasaje.en.mano" siguen siendo idénticos, así que no debería romper).

- [ ] **Step 4: Smoke manual del viewer**

Abrir `http://localhost:3000/reports/<id>` para el report Abril Aurora. Verificar:
- Pill title "MES A MES" + tabla con 3 columnas y deltas verde.
- Pill title "INSTAGRAM" + tabla con 3 columnas y deltas verde.
- Pill title "ATRIBUCIÓN ONELINK" + tabla con 3 columnas y fila Total al final en bold.
- Charts y demás blocks renderean igual que antes.

- [ ] **Step 5: Si todo verde, no commit (no hay cambios — esto es solo verification)**

Si hubo ajustes en E2E:

```bash
git add e2e/
git commit -m "test(e2e): adjust assertions for unified TableBlock"
```

---

## Task 9: Actualizar memorias

**Files:**
- Modify: `C:\Users\danie\.claude\projects\C--Users-danie-Impactia-Git-Chirri-Peppers-Chirri-Portal\memory\project_block_vs_item_polymorphism.md`
- Create (probable): `C:\Users\danie\.claude\projects\C--Users-danie-Impactia-Git-Chirri-Peppers-Chirri-Portal\memory\project_reports_are_powerpoint.md`
- Modify: `C:\Users\danie\.claude\projects\C--Users-danie-Impactia-Git-Chirri-Peppers-Chirri-Portal\memory\MEMORY.md`

- [ ] **Step 1: Crear `project_reports_are_powerpoint.md`**

Contenido:

```markdown
---
name: Reports son artefactos de presentación, no dominio
description: Los blocks de un report son agnósticos al dominio (como un PowerPoint) — no modelar entidades de negocio dentro de un block.
type: project
---

Un report en Chirri Portal es un artefacto de presentación, no un modelo de dominio. La regla:

- Los blocks tienen shape de **render** (tabla, KPI grid, gráfico, imagen), no de **dominio** (no hay "AttributionBlock" ni "InfluencerMetricsBlock").
- Si dos blocks tienen el mismo shape de render pero datos de dominios distintos, son **el mismo block**. La diferencia vive en el contenido de las celdas / strings, no en el modelo.
- No modelar entidades de dominio (ej. `OneLinkAttribution`) cuando solo se usan dentro de un report — viven como strings dentro del block.

**Why:** discutido con Dani 2026-04-26 al rediseñar los table blocks. La justificación de modelar AttributionTableBlock + OneLinkAttribution era "tipado por columna" y "AI fetcher metadata"; ambos perdieron al criterio "es un PowerPoint, agnóstico". Cross-report analytics no se necesita; si se necesitara, vivirían fuera de `apps/reports`.

**How to apply:**
- Antes de proponer un nuevo block tipado: ¿el shape de render es realmente distinto, o es solo un dominio distinto con la misma shape? Si es lo segundo, agregar al block existente.
- No agregar choices de dominio (Network, source_type, etc.) a un block como campos del modelo — pertenecen a las celdas/strings que rendea.
- `Network` y `SourceType` siguen vivos en `choices.py` solo porque otros blocks (TopContents, TopCreators, Chart) los usan como hint de fetcher / metadata; nada nuevo debería sumarles.
- Excepción justificada: ChartBlock conserva `chart_type` (bar/line) porque es shape de render distinto, no dominio.
```

Escribir el archivo en `C:\Users\danie\.claude\projects\C--Users-danie-Impactia-Git-Chirri-Peppers-Chirri-Portal\memory\project_reports_are_powerpoint.md`.

- [ ] **Step 2: Actualizar `project_block_vs_item_polymorphism.md`**

Reemplazar la línea de precedentes (la que dice "Precedentes donde dos blocks separados es correcto: MetricsTableBlock vs ChartBlock") por:

```markdown
- Precedente donde un block genérico colapsa varios subtipos: `TableBlock` (2026-04-26) — antes había `MetricsTableBlock` + `AttributionTableBlock`; tenían el mismo shape de render (tabla con rows/cells) y solo el dominio difería. Ver `project_reports_are_powerpoint.md`.
- Precedente donde dos blocks separados es correcto: `TableBlock` vs `ChartBlock` (DEV-116) — shape de render distinto (tabla vs gráfico), no solo dominio.
- Precedente donde un block genérico + items polimórficos es correcto: TopBlock (DEV-129).
```

- [ ] **Step 3: Actualizar `MEMORY.md`**

Agregar la línea correspondiente al nuevo memory:

```markdown
- [Reports = PowerPoint](project_reports_are_powerpoint.md) — blocks son artefactos de presentación; mismo shape de render = mismo block aunque el dominio difiera.
```

(Insertar manteniendo el orden existente.)

- [ ] **Step 4: No commit (memorias son del usuario, no del repo)**

---

## Self-Review Checklist

**Spec coverage:**
- ✅ Modelo nuevo `TableBlock` + `TableRow` (Task 1).
- ✅ Serializer + dispatcher polimórfico (Task 2).
- ✅ Admin con inline (Task 3).
- ✅ Frontend renderer (Task 4).
- ✅ Seed demo migrado (Task 5).
- ✅ Importer migrado (Task 6).
- ✅ Drop de legacy (Task 7).
- ✅ Reseed + suite (Task 8).
- ✅ Memorias actualizadas (Task 9).

**Type consistency check:**
- `TableBlock` con `title`, `show_total` ✓ usados consistente en serializer, admin, FE, seed, exporter.
- `TableRow` con `order`, `is_header`, `cells` ✓ shape preservada en serializer DTO, admin inline, parser/builder, FE.
- `cells: JSONField(default=list)` ✓ FE espera `cells: string[]`.
- `TABLES_HEADERS` en schema con 13 columnas ✓ parser, builder, exporter usan los mismos nombres.

**Pendientes razonables que NO están en este plan (por scope):**
- Sub-categorización de columnas con metadata (alignment override, format hint) — el FE auto-detecta y eso alcanza para los 2 use-cases actuales. Si en el futuro aparece una tabla donde la heurística no acierta, considerar agregar `column_meta: JSONField` al `TableBlock`.
- Migración de data preservando reportes existentes — el usuario confirmó que se reseed.
- Limpieza del PDF importer (`apps/reports/importers/pdf_*` o similar): grep no muestra que use `MetricsTableBlock`/`AttributionTableBlock` directamente, pero conviene sanity-check si el importer LLM emite `Tables` ahora (Task 6 cubre el schema; el LLM pipeline es downstream).

---

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-04-26-unify-table-blocks.md`. Two execution options:

**1. Subagent-Driven (recommended)** — yo despacho un subagente fresco por task, reviso entre tasks, iteración rápida.

**2. Inline Execution** — ejecuto los tasks en esta sesión usando executing-plans, batch con checkpoints para review.

¿Cuál preferís?
