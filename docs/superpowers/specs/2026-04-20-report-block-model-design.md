# Report Block Model — Design Spec

**Ticket:** [DEV-105](https://linear.app/impactia/issue/DEV-105)
**Date:** 2026-04-20
**Status:** Approved (pending user review of this doc)
**Blocks:** DEV-83 (Excel importer — rescope después)

## 1. Overview

Refactor del modelo `Report` de estructura rígida (13 secciones hardcoded en `frontend/app/reports/[id]/page.tsx`) a contenido flexible definido por una lista ordenada de bloques tipados por instancia.

**Mantener:** base del `Report` (stage, period, status, title, intro_text, conclusions_text, published_at). Agregar `original_pdf` como fallback descargable.

**Cambiar:** el contenido entre `intro_text` y `conclusions_text` pasa de 11 secciones siempre-presentes (ocultas si no hay data) a `blocks: ReportBlock[]` curado manualmente por instancia.

**Objetivo de negocio:** reportes fijos una vez generados, pero estructura variable por cliente y por instancia ("Hoy Yelmo ve una cosa, mañana pide más datos y ve otras"). Admin-driven en fase 1; editor visual dedicado en fase futura.

**Criterio de éxito:** los 2 reportes seeded completos ("Reporte general · Marzo" educacion + validacion) se representan 1:1 con el nuevo modelo, renderizando visualmente equivalente al estado pre-refactor (verificado por E2E smoke).

## 2. Architecture

### Backend

```
apps/reports/
  models.py              # + ReportBlock, + Report.original_pdf
  migrations/
    00XX_report_blocks.py
  serializers.py         # + BlockSerializer, + blocks[] y original_pdf_url en ReportDetailSerializer
  admin.py               # + ReportBlockInline (sortable), + original_pdf en ReportAdmin
  blocks/
    __init__.py
    schemas.py           # validadores de config por tipo (dict-based, no pydantic)
    registry.py          # BLOCK_TYPES dict: type → {validator, label}
```

### Frontend

```
app/reports/[id]/
  page.tsx                       # refactor: render desde blocks[]
  blocks/
    BlockRenderer.tsx            # dispatch por block.type
    KpiGridBlock.tsx             # (ex-KpisSummary)
    MetricsTableBlock.tsx        # (unifica NetworkSection×3, MonthlyCompare, YoyComparison, Q1RollupTable)
    TopContentBlock.tsx          # (ex-BestContentChapter)
    AttributionTableBlock.tsx    # (ex-OneLinkTable)
    ChartBlock.tsx               # (ex-FollowerGrowthSection)
    TextImageBlock.tsx           # (nuevo)
  sections/                      # queda solo HeaderSection, IntroText, ConclusionsSection (header/footer)
    HeaderSection.tsx            # + botón "Descargar PDF original" cuando report.original_pdf_url
    IntroText.tsx
    ConclusionsSection.tsx
```

Los componentes específicos (`ContentCard`, `MetricRow`, `KpiTile`, `BarChartMini`) quedan en `components/` y los nuevos blocks los reusan.

### Flow

```
Admin edita Report + Blocks (drag-drop reorder)
    ↓
API /api/reports/<id>/ serializa blocks[] en orden
    ↓
Next.js SSR renderiza HeaderSection + IntroText + {blocks.map(BlockRenderer)} + ConclusionsSection
    ↓
BlockRenderer dispatcha por type al component correspondiente
    ↓
Cada block component recibe {block: {type, config}, report} y decide qué data del report consumir
```

**Principio clave:** el `config` del bloque es declarativo (filtros, fuentes, opciones de display). La data sigue viniendo del `Report` agregado (metrics, top_content, onelink, yoy, q1_rollup, follower_snapshots). Un bloque `METRICS_TABLE` con `filter: { network: INSTAGRAM }` filtra `report.metrics` en el cliente — no guarda sus propias métricas.

**Excepción:** `TEXT_IMAGE` guarda su contenido (title, text, image) directamente en `config` porque no hay fuente agregada.

## 3. Data Model

### `Report` — cambios

```python
class Report(models.Model):
    # ... (fields existentes sin cambios)
    original_pdf = models.FileField(
        upload_to="reports/pdf/%Y/%m/",
        blank=True,
        null=True,
        validators=[validate_pdf_size, validate_pdf_mimetype],
        help_text="PDF original del reporte (Google Slides export), descargable por el cliente.",
    )
```

Agregar validadores en `apps/reports/validators.py`:
- `validate_pdf_size`: máx 20 MB
- `validate_pdf_mimetype`: application/pdf only

### `ReportBlock` — nuevo modelo

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
            models.UniqueConstraint(fields=["report", "order"], name="uniq_block_order_per_report"),
        ]

    def clean(self):
        from .blocks.registry import validate_config
        validate_config(self.type, self.config)

    def __str__(self):
        return f"{self.report_id} · {self.type} #{self.order}"
```

**Decisiones de diseño:**

- **`order` + UniqueConstraint**: garantiza orden determinístico y evita dos bloques con el mismo order. Django-admin-sortable2 reasigna orders en batch al reordenar.
- **`image` como FileField separado**: porque `ImageField` no se puede embeber en JSONField. Solo usado por `TEXT_IMAGE`; los otros tipos lo ignoran. Alternativa descartada (imagen vía URL en config) porque queremos ownership del storage + validación de mimetype.
- **`config` como JSONField con validación por tipo**: sigue el patrón ya existente de `TopContent.metrics` (JSONField). Validación via `clean()` + registry, no pydantic (YAGNI — Django forms/serializers ya cubren el uso).

### Config schemas por tipo

**`TEXT_IMAGE`**
```json
{
  "title": "string (opcional)",
  "text": "string markdown-ish (opcional)",
  "columns": 1 | 2 | 3,
  "image_position": "left" | "right" | "top"
}
```
La imagen real vive en `ReportBlock.image`. Si `image` está vacío, `image_position` se ignora. No hay valor "none" — para un bloque solo-texto, simplemente no subís imagen.

**`KPI_GRID`**
```json
{
  "title": "string (opcional)",
  "tiles": [
    { "label": "Reach total", "source": "reach_total" },
    { "label": "Reach orgánico", "source": "reach_organic" },
    { "label": "Reach influencer", "source": "reach_influencer" }
  ]
}
```
`source` values definidos: `reach_total`, `reach_organic`, `reach_influencer`, `reach_paid`, `engagement_total`. Cada uno agrega sobre `report.metrics` con filtros fijos (definidos en el frontend KpiGridBlock).

**`METRICS_TABLE`**
```json
{
  "title": "string (opcional)",
  "source": "metrics" | "yoy" | "q1_rollup",
  "filter": {
    "network": "INSTAGRAM" | "TIKTOK" | "X" | null,
    "source_type": "ORGANIC" | "INFLUENCER" | "PAID" | null,
    "has_comparison": true | false | null
  }
}
```
`filter` solo aplica cuando `source = "metrics"`. `yoy` y `q1_rollup` usan sus datos pre-agregados del serializer (ya existen).

**`TOP_CONTENT`**
```json
{
  "title": "string (opcional, default derivado del kind)",
  "kind": "POST" | "CREATOR",
  "limit": 6 (default, max 20)
}
```

**`ATTRIBUTION_TABLE`**
```json
{
  "title": "string (opcional)",
  "show_total": true (default)
}
```

**`CHART`**
```json
{
  "title": "string (opcional)",
  "source": "follower_snapshots",
  "group_by": "network",
  "chart_type": "bar"
}
```
Fase 1: solo `follower_snapshots + group_by=network + chart_type=bar` (reproduce FollowerGrowthSection). Otros sources/types son `raise ValueError("not supported in phase 1")` hasta que se extienda.

### Validación

`apps/reports/blocks/registry.py`:

```python
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
        raise ValidationError(f"Unknown block type: {block_type}")
    validator(config)
```

Cada validador chequea keys requeridos, tipos, enums. `raise ValidationError({"config": ["message"]})` para que salga en admin sin stacktrace.

## 4. API

### Response shape — `/api/reports/<id>/`

Agregar a `ReportDetailSerializer`:

```python
blocks = ReportBlockSerializer(many=True, read_only=True)
original_pdf_url = serializers.SerializerMethodField()
```

`ReportBlockSerializer`:
```python
class ReportBlockSerializer(serializers.ModelSerializer):
    image_url = serializers.SerializerMethodField()

    class Meta:
        model = ReportBlock
        fields = ("id", "type", "order", "config", "image_url")

    def get_image_url(self, obj):
        return obj.image.url if obj.image else None
```

`get_original_pdf_url`: devuelve `obj.original_pdf.url if obj.original_pdf else None` (respeta URL absoluta si R2, relativa en dev).

### N+1 prevention

Extender el queryset en `ReportDetailView.get_queryset()`:
```python
.prefetch_related("metrics", "top_content", "onelink", "blocks")
```

**Query budget target:** el test `test_report_nplus1.py` hoy permite `<= 12` queries. Con la nueva relación prefetch, debería seguir en 13 máximo (uno más por blocks). Actualizar el test explícitamente a `<= 13`.

### Typing en frontend (`lib/api.ts`)

```typescript
export type ReportBlockDto = {
  id: number;
  type: "TEXT_IMAGE" | "KPI_GRID" | "METRICS_TABLE" | "TOP_CONTENT" | "ATTRIBUTION_TABLE" | "CHART";
  order: number;
  config: Record<string, unknown>;  // validado en runtime por cada BlockComponent
  image_url: string | null;
};

// ReportDto agrega:
blocks: ReportBlockDto[];
original_pdf_url: string | null;
```

No usar generics por type variant en `config` (runtime validation en cada block component es suficiente y más simple).

## 5. Admin

### ReportBlockInline

```python
from adminsortable2.admin import SortableInlineAdminMixin

class ReportBlockInline(SortableInlineAdminMixin, admin.StackedInline):
    model = ReportBlock
    extra = 0
    fields = ("type", "config", "image")
    # order es gestionado por SortableInlineAdminMixin automáticamente
```

### ReportAdmin

```python
class ReportAdmin(admin.ModelAdmin):
    inlines = [
        ReportMetricInline,
        TopContentInline,          # nuevo (parte de DEV-83 pero entra acá)
        OneLinkAttributionInline,  # nuevo (parte de DEV-83 pero entra acá)
        ReportBlockInline,
    ]
    # ... fields existentes + "original_pdf" en fieldsets
```

**Nota:** `TopContentInline` y `OneLinkAttributionInline` estaban planeados como parte de DEV-83 pero los entregamos acá porque Julián los necesita para cargar thumbnails antes de poder armar bloques `TOP_CONTENT` útiles. Sin este paso, la UX post-merge sería: crear bloque `TOP_CONTENT`, pero no hay creators cargados → bloque vacío.

### adminsortable2

Nueva dependencia: `django-admin-sortable2==2.1.10` (latest stable a 2026-04).

Requiere `adminsortable2` en `INSTALLED_APPS` (antes de `django.contrib.admin` según docs oficiales). La migración automática no toca datos existentes — solo hace que `Meta.ordering = ["order"]` + el admin provea drag-handles.

## 6. Frontend rendering

### Refactor de `page.tsx`

```tsx
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
```

### BlockRenderer

```tsx
const BLOCK_COMPONENTS = {
  TEXT_IMAGE: TextImageBlock,
  KPI_GRID: KpiGridBlock,
  METRICS_TABLE: MetricsTableBlock,
  TOP_CONTENT: TopContentBlock,
  ATTRIBUTION_TABLE: AttributionTableBlock,
  CHART: ChartBlock,
} as const;

export default function BlockRenderer({ block, report }: { block: ReportBlockDto; report: ReportDto }) {
  const Component = BLOCK_COMPONENTS[block.type];
  if (!Component) {
    // Bloque tipo desconocido (frontend desactualizado vs backend). Log + render nothing.
    console.warn("unknown_block_type", block.type);
    return null;
  }
  return <Component block={block} report={report} />;
}
```

**Principio de resiliencia:** frontend nunca crashea por un bloque desconocido o mal configurado. Cada block component hace su propia validación defensiva del `config` y devuelve `null` si algo falla, logueando `console.warn` con detalles.

### Config runtime validation

Cada block component empieza con validación defensiva — ejemplo `KpiGridBlock`:

```tsx
const cfg = block.config as KpiGridConfig;
if (!Array.isArray(cfg.tiles) || cfg.tiles.length === 0) {
  console.warn("invalid_kpi_grid_config", block.id, cfg);
  return null;
}
```

Chequeos mínimos: keys requeridos existen, tipos correctos. No duplicar la validación full del backend — solo lo suficiente para no romper el render.

### HeaderSection — botón PDF

```tsx
{report.original_pdf_url && (
  <a
    href={report.original_pdf_url}
    download
    className="pdf-download-btn"
    aria-label="Descargar PDF original"
  >
    Descargar PDF
  </a>
)}
```

## 7. Seed data — migración

`seed_demo` actualizado. Para cada reporte seeded que hoy renderiza las 13 secciones, se crean los bloques equivalentes en orden:

```python
def _seed_blocks_for_full_report(report: Report) -> None:
    ReportBlock.objects.bulk_create([
        ReportBlock(report=report, order=1, type="KPI_GRID", config={
            "tiles": [
                {"label": "Reach total", "source": "reach_total"},
                {"label": "Reach orgánico", "source": "reach_organic"},
                {"label": "Reach influencer", "source": "reach_influencer"},
            ],
        }),
        ReportBlock(report=report, order=2, type="METRICS_TABLE", config={
            "title": "Mes a mes", "source": "metrics",
            "filter": {"has_comparison": True},
        }),
        ReportBlock(report=report, order=3, type="METRICS_TABLE", config={
            "title": "Year over year", "source": "yoy", "filter": {},
        }),
        ReportBlock(report=report, order=4, type="METRICS_TABLE", config={
            "title": "Instagram", "source": "metrics",
            "filter": {"network": "INSTAGRAM"},
        }),
        ReportBlock(report=report, order=5, type="METRICS_TABLE", config={
            "title": "TikTok", "source": "metrics",
            "filter": {"network": "TIKTOK"},
        }),
        ReportBlock(report=report, order=6, type="METRICS_TABLE", config={
            "title": "X / Twitter", "source": "metrics",
            "filter": {"network": "X"},
        }),
        ReportBlock(report=report, order=7, type="TOP_CONTENT", config={
            "title": "Posts del mes", "kind": "POST",
        }),
        ReportBlock(report=report, order=8, type="TOP_CONTENT", config={
            "title": "Creators del mes", "kind": "CREATOR",
        }),
        ReportBlock(report=report, order=9, type="ATTRIBUTION_TABLE", config={
            "show_total": True,
        }),
        ReportBlock(report=report, order=10, type="CHART", config={
            "title": "Followers", "source": "follower_snapshots",
            "group_by": "network", "chart_type": "bar",
        }),
        ReportBlock(report=report, order=11, type="METRICS_TABLE", config={
            "title": "Q1 rollup", "source": "q1_rollup", "filter": {},
        }),
    ])
```

**Reportes pre-existentes en la DB (no seeded):** al aplicar la migración, no se crean bloques automáticos. Quedan con `blocks=[]` hasta que un admin los edite. Aceptable porque en prod no hay reportes reales todavía — solo data de seed_demo que se regenera con `seed_demo --wipe`.

## 8. Testing

### Backend unit tests (pytest)

1. **`test_block_config_validation.py`**
   - `TEXT_IMAGE` con `columns` fuera de [1,2,3] → `ValidationError`.
   - `KPI_GRID` sin `tiles` o tiles vacío → `ValidationError`.
   - `METRICS_TABLE` con `source` desconocido → `ValidationError`.
   - `TOP_CONTENT` con `kind` inválido → `ValidationError`.
   - Config válido para cada tipo → no raise.

2. **`test_report_serializer_blocks.py`**
   - Reporte con 5 bloques en orden 1,2,3,4,5 se serializa en ese orden.
   - Reporte sin bloques devuelve `blocks: []`.
   - `original_pdf_url` devuelve URL cuando hay PDF, `null` cuando no.
   - Un block con imagen devuelve `image_url` URL-abs.

3. **`test_report_nplus1.py`** (extender el existente)
   - Agregar 20 bloques al report fixture.
   - Ajustar budget a `<= 13` (antes 12, +1 por prefetch blocks).
   - Assertion falla si se introduce un N+1 por blocks.

4. **`test_seed_demo_blocks.py`**
   - Después de correr `seed_demo`, los 2 reportes completos tienen exactamente 11 bloques.
   - Los tipos están en el orden esperado.

### Frontend unit tests

No hay framework unit en frontend hoy (solo Playwright E2E). Esto queda para DEV futuro. Por ahora cubrimos con E2E.

### E2E smoke (Playwright)

Extender `frontend/tests/reports.spec.ts` (o crear `frontend/tests/report-blocks.spec.ts`):

1. **"reporte seeded renderiza los bloques en orden"**
   - Login como Balanz.
   - Navegar a `/reports/<id del Marzo educacion>`.
   - Verificar presencia de KPI grid, tabla de métricas, top content, attribution table, chart.
   - Verificar que los títulos de sección esperados aparecen en orden vertical (DOM order).

2. **"unknown block type no rompe el render"**
   - Mockeable vía fixture DB: reporte con un bloque de tipo `UNKNOWN`.
   - Verificar que la página carga y renderiza los otros bloques + no console errors críticos.

3. **"PDF download button aparece cuando hay original_pdf"**
   - Reporte con `original_pdf` seteado → link visible con `[download]` attr.
   - Reporte sin PDF → link no existe.

### Visual regression (e2e-frontend)

Se dispara automáticamente en Step 5.5 del pipeline entropy-driven. Debe pasar — el render visual de los 2 reportes seeded no cambia (ese es el punto).

## 9. Security

- **Auth**: `/api/reports/<id>/` ya tiene `IsAuthenticated` + tenant scoping en view (CLAUDE.md gotcha). Blocks heredan el scoping via `report` FK — si el reporte no es visible, los bloques tampoco.
- **PDF upload**: `Report.original_pdf` con validators de mimetype (`application/pdf`) y tamaño (20 MB). Storage en `reports/pdf/%Y/%m/` (via R2 en prod).
- **Image upload en bloques**: mismos validators que `TopContent.thumbnail` (reusa `validate_image_size`, `validate_image_mimetype`).
- **Admin-only editing**: `ReportBlockInline` solo accesible via Django admin (staff users). El endpoint público `/api/reports/<id>/` es read-only.
- **JSON config**: validado en `clean()` + serializer — no se aceptan keys arbitrarios sin validación.
- **Dependency health**: `django-admin-sortable2==2.1.10` es activamente mantenido (últimos commits en 2026, compatible con Django 5).

## 10. Observability

- Logging estructurado en `ReportDetailView` ya existe (`report_served`, `report_access_denied`). Sin cambios.
- Agregar log en `BlockRenderer` cliente-side para tipos desconocidos (`console.warn`). No enviamos estos warnings al backend — son diagnóstico de dev/QA.
- Admin lleva track de cambios via Django's built-in admin log (LogEntry).

## 11. Entropy dimensions

Este spec cubre las 13 dimensiones de entropy-scan:

1. **Test coverage**: unit tests del validador + serializer + N+1; E2E smoke (§8).
2. **DRY**: `BlockRenderer` dispatch centralizado; validadores por tipo en registry; `MetricsTableBlock` unifica 6 componentes actuales.
3. **Boundaries**: config validado server-side (`clean()` + serializer) y client-side defensivo (cada block component).
4. **Docs & complexity**: ningún archivo pensado >300 líneas. `MetricsTableBlock` es el componente más grande; si crece >300 se splitea por `source`.
5. **Principles (SOLID)**: P2 (SRP: un componente por tipo de bloque), P4 (Open/Closed: nuevos tipos vía registry sin tocar BlockRenderer), P5 (DIP: validadores inyectados via registry), P9 (Fail Fast: config inválido → ValidationError en admin, nunca llega al frontend), P10 (Simplicity: sin pydantic, sin serializers polimórficos — un JSONField y un switch).
6. **Design patterns**: Strategy (registry de validadores), Dispatcher (BlockRenderer), Composition over inheritance (blocks son data, no clases).
7. **Security**: auth heredada, mimetype validators, tenant scoping, admin-only editing (§9).
8. **Git health**: commits atómicos por task del plan, siguiendo conventional commits (`feat:`, `refactor:`, `test:`, `chore:`). Plan prevé 10+ commits (modelo, migración, admin, serializer, tipo por tipo en frontend, seed, tests). Branch única `dev-105-report-block-model` que integra a `development` vía PR. Ownership: Daniel implementa, Eugenio reviewer principal (es el único otro contributor del repo). No hay single-author risk para este dominio — la feature queda documentada en spec + README para que cualquiera del equipo pueda mantenerla.
9. **Testability**: validadores son funciones puras (fácil test); block components reciben props (sin side effects).
10. **Observability**: logging estructurado heredado; warnings client-side para tipos desconocidos (§10).
11. **Frontend quality**:
    - **Design tokens**: reusa variables CSS existentes (`--chirri-pink`, `--chirri-black`, `pill-title`, `font-display`). No hardcoded colors/spacing nuevos.
    - **Component size**: cada BlockComponent ≤200 líneas. `MetricsTableBlock` es el más grande (unifica 4 secciones); si cruza 300, se splitea por `source`.
    - **Accessibility**: HTML semántico preservado (h1/h2/h3, `<table>` con `<thead>`/`<th scope>`, `<section>`). Botón PDF con `aria-label="Descargar PDF original"`. Bloques decorativos (PillTitle) no interfieren con flujo de lectura. Keyboard nav ya funciona (enlaces y buttons nativos).
    - **Performance**: SSR completo, sin client-side fetching. No se necesita lazy loading de BlockComponents — cada uno es <5 KB, Next.js bundling los incluye en el chunk de la ruta. No virtualization requerida (reportes tienen ≤15 bloques).
    - **State management**: todo estado es local al componente o derivado de props. Sin Context ni stores globales. SSR-first.
    - **i18n**: strings hardcoded en español (convención actual del codebase — no hay sistema i18n). Los `title` de cada bloque (admin-editable) son la única fuente custom; quedan en español por default.
    - **Responsive**: los componentes migrados ya tienen responsive (auto-fit grids, max-width 720 para texto). Se preserva sin cambios.
12. **Repo hygiene**: `README.md` actualizado con sección "Reportes" explicando bloques; spec file se mueve a `docs/superpowers/specs/completed/` cuando cierra; plan file mismo destino.
13. **CI/CD & deployment**:
    - **PR gate**: `test.yml` corre backend pytest + frontend typecheck + Playwright smoke en cada push/PR a `main`/`development`. Ya es required check. Sin cambios necesarios.
    - **Build**: Docker image pin por SHA (heredado del pipeline existente). Nueva dep `django-admin-sortable2==2.1.10` se agrega a `backend/requirements.txt`; el build del Docker image la instala vía `pip install -r requirements.txt`.
    - **Branch → env mapping**: `development` → Hetzner prod (via `deploy.yml` en push a esa rama). `main` queda como production-ready pointer. Sin staging separado por ahora.
    - **Post-deploy smoke**: `deploy.yml` ya corre Playwright contra `DEPLOY_URL` con `--grep "Report viewer|Home smoke|Campaign detail"`. Este spec extiende `reports.spec.ts` (o crea `report-blocks.spec.ts`), y el match "Report viewer" lo incluye automáticamente si el `describe` empieza con ese prefijo. **Acción concreta en el plan:** el `describe()` del nuevo spec debe llamarse `Report viewer · blocks` para que lo matchee el grep de `deploy.yml`.
    - **Migration en deploy**: `deploy.yml` corre `python manage.py migrate --noinput` automáticamente después del `up -d`. La migración nueva corre sin intervención. No requiere downtime (agrega tabla + campo nullable).
    - **Seed demo refresh**: después del primer deploy con el block model, correr `docker compose exec backend python manage.py seed_demo --wipe` una vez en prod para regenerar los reportes demo con bloques. Esto es una acción manual post-deploy (una sola vez) — documentar en `README.md` como "tras mergear DEV-105, correr seed_demo --wipe".
    - **Secrets**: ningún secret nuevo. El storage R2 ya está configurado (`R2_*` env vars); los nuevos paths (`reports/pdf/`, `report_blocks/`) viven en el mismo bucket.
    - **Rollback**: `git revert <merge-commit> && git push origin development` dispara redeploy al commit anterior. La migración es reversible (`python manage.py migrate reports <prev>`) — pero implica perder bloques creados. En caso real de rollback, mejor dejar los bloques y revertir solo frontend (el backend sirve `blocks: []` sin problema si nadie los consume).

## 12. Out of scope

- **Editor visual drag-drop fuera del admin** (portal UI para editar bloques). Fase 2, ticket aparte.
- **Block types extra** (QUOTE, VIDEO_EMBED, HTML_RAW, TIMELINE). Agregar al registry cuando se necesiten.
- **Templates reutilizables** ("copiar bloques del reporte anterior", "aplicar template de etapa"). Fase futura.
- **PDF rendering server-side** (renderizar el reporte a PDF) — eso es DEV-54.
- **CHART con sources distintos a follower_snapshots**: hoy solo ese source. Ampliar cuando haya caso concreto.

## 13. Risks

- **Migración rompe reportes pre-existentes**: Mitigado — `seed_demo --wipe` regenera toda la data demo. En prod no hay reportes reales.
- **adminsortable2 no juega bien con nuestros otros inlines**: Riesgo bajo. Si aparece, fallback: ordering manual via `order` numeric field (usabilidad peor pero funcional).
- **Frontend desactualizado vs backend**: si backend agrega un nuevo block type y frontend no conoce el componente, `BlockRenderer` loguea warning y no renderiza. Aceptable — mejor que crash.
- **N+1 con blocks**: mitigado con `prefetch_related("blocks")` + test explícito que falla si el budget se rompe.
- **Tamaño del JSON en config**: config es chico por diseño (<1 KB por bloque). No hay riesgo de row bloat.

## 14. Dependencies

- **Nueva pip**: `django-admin-sortable2==2.1.10`
- **Nueva npm**: ninguna (reusamos componentes existentes).
- **Nueva DB migration**: 1 archivo en `apps/reports/migrations/`.
- **Nuevos archivos media**: `report_blocks/%Y/%m/` y `reports/pdf/%Y/%m/` paths en el bucket R2.

## 15. Definition of Done

- [ ] Modelo `ReportBlock` + migración aplicada en dev.
- [ ] `Report.original_pdf` field agregado.
- [ ] `apps/reports/blocks/registry.py` + validadores por los 6 tipos.
- [ ] Admin: `ReportBlockInline` con drag-drop, `TopContentInline`, `OneLinkAttributionInline`, campo `original_pdf` editable.
- [ ] API: endpoint devuelve `blocks[]` en orden + `original_pdf_url`, sin N+1.
- [ ] Frontend: `page.tsx` refactor, 6 BlockComponents implementados, `BlockRenderer` dispatch.
- [ ] Botón "Descargar PDF original" en HeaderSection cuando hay PDF.
- [ ] `seed_demo` genera los 11 bloques para los 2 reportes completos → render visual preservado.
- [ ] Unit tests: validador de config (6 tipos), serializer (blocks + PDF URL), N+1 (<=13 queries con 20 blocks), seed_demo crea bloques esperados.
- [ ] E2E smoke: reportes seeded renderizan correctamente + unknown block type no rompe + botón PDF aparece solo con PDF.
- [ ] Visual regression e2e-frontend pasa (los 2 reportes lucen igual).
- [ ] Docs: `README.md` sección "Reportes" actualizada.
- [ ] Entropy-scan post-ejecución: dominio `backend/reports` + `frontend/reports` en grade >= B.

## 16. References

- `backend/apps/reports/models.py` — base del Report actual
- `backend/apps/reports/serializers.py` — ReportDetailSerializer a extender
- `backend/apps/reports/views.py` — ReportDetailView queryset a extender con prefetch
- `backend/apps/reports/admin.py` — ReportAdmin a extender con 3 inlines nuevos
- `backend/apps/tenants/management/commands/seed_demo.py` — `_seed_report_viewer_fixtures` a extender con bloques
- `backend/tests/unit/test_report_nplus1.py` — test a extender
- `frontend/app/reports/[id]/page.tsx` — punto de refactor principal
- `frontend/app/reports/[id]/sections/*` — componentes a migrar a `blocks/*` (mantener HeaderSection, IntroText, ConclusionsSection)
- `frontend/lib/api.ts` — agregar ReportBlockDto, extender ReportDto
- `django-admin-sortable2` docs: https://django-admin-sortable2.readthedocs.io/
