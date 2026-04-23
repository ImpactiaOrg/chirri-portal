# DEV-116 — Typed Blocks Refactor · Design Spec

**Date:** 2026-04-22
**Ticket:** [DEV-116](https://linear.app/impactia/issue/DEV-116)
**Status:** Brainstorm complete, pending plan

## Context

Hoy `ReportBlock` usa un patrón `type: CharField + config: JSONField` con validación imperativa en `backend/apps/reports/blocks/registry.py` + `schemas.py`. La separación data ↔ layout (`ReportMetric` feeds `ReportBlock` que filtra via config) se armó antes de definir Metricool como data source y complejiza sin justificación real. Un reporte es un **snapshot tipo "PowerPoint HTML"**: display-only, no se re-usa para analytics — el análisis serio vive en Metricool o en un data warehouse dedicado, no en report snapshots.

Este spec reemplaza el modelo actual con **bloques tipados con herencia multi-tabla de Django**. Cada subtipo de bloque es su propia tabla con columnas tipadas. El admin usable por Euge (operadora no-técnica) cae como consecuencia natural de tener columnas tipadas + `django-polymorphic` para el UX de "agregar bloque → elegir tipo → aparecen los campos".

Nada está en producción, así que la migración es destructiva: se elimina `ReportMetric`, `ReportBlock.config`, `ReportBlock.type`, `OneLinkAttribution.report` FK, y los agregados cross-report `build_yoy` / `build_q1_rollup` / `build_follower_snapshots`. `seed_demo` se reescribe.

## Design decisions (closed)

Las siguientes decisiones están cerradas y **no se revisan** fuera de nuevos datos empíricos. Las referencias a PRINCIPLES.md (P1–P10) marcan cuál principio respalda cada decisión:

1. **Herencia multi-tabla vs 6 tablas independientes** → Herencia. Base `ReportBlock` polimórfica + subtipos con `class KpiGridBlock(ReportBlock)`. Motivo: queries de "blocks de un reporte en orden" y constraint `uniq_order_per_report` viven en una sola tabla. *(P2 Single Responsibility — cada subtipo un concern; P4 Open/Closed — nuevos tipos extienden la base.)*
2. **Filas hijas (tiles, metric rows, onelink entries)** → tablas FK propias por tipo, NO unificadas en una tabla genérica. Motivo: identidades semánticas distintas, evitar refactor-pain cuando divergen. *(P10 Simplicity Over Cleverness — tres tablas honestas > una tabla genérica "inteligente".)*
3. **Metadata en el block** → minimal, con dos capas, y **toda opcional**:
   - **Estructurada** (campos tipados por subtipo): solo lo que sirve como "instrucciones para el armado" verificables automáticamente. `network` es metadata real en todas las brands analizadas; `source_type` y `has_comparison` son row-level. Los campos de metadata (`network`, `chart_type`, etc.) son `null=True, blank=True` o tienen default — nada obliga al operador a completarlos al crear el bloque.
   - **No-estructurada** (`instructions: TextField(blank=True)` en la base): contexto narrativo libre que el operador escribe para guiar al AI o para sí mismo. Complementa los campos estructurados cuando el caso de uso excede lo que un enum puede capturar. Opcional.
   - **Fields estructurales** (no-metadata): `TopContentBlock.kind` (POST/CREATOR) sí es required — define qué ES el bloque, no es hint opcional.
4. **YoY y Q1 rollup** → eliminados. No están en uso real en reportes de hoy (P10, UC, FW), y si reaparecen se modelan como nuevos block types tipados via DEV-117. *(P10 Simplicity — no mantener código para casos de uso sin demanda.)*
5. **ChartBlock** → un chart por block (no `group_by`). Data points son child snapshot rows. `BrandFollowerSnapshot` sobrevive como source-of-truth brand-level pero no se consume en serializers (se consume al crear/publicar para popular los data points del block). *(P2 SRP — un block, un chart.)*
6. **`django-polymorphic`** → SÍ. Dependencia explícita. Entrega el UX "agregar bloque → elegir tipo → campos aparecen" out-of-the-box y evita ~2 días de admin custom. *(P10 Simplicity Over Cleverness — dependencia madura vs código custom que duplica funcionalidad.)*

## Data model

### Base

```
ReportBlock (abstract-feeling base, concrete table via MTI)
├── report            FK → Report (on_delete=CASCADE)
├── order             PositiveIntegerField (unique per report)
├── instructions      TextField(blank=True)    # free-text AI/operator hints (ver nota)
├── created_at        DateTimeField
├── updated_at        DateTimeField
└── polymorphic_ctype (managed by django-polymorphic)

constraints:
  - UniqueConstraint(fields=["report", "order"])
```

**Nota sobre `instructions`:** campo de texto libre editable en el admin,
que actúa como **metadata no-estructurada** para complementar los campos
tipados del subtipo. Propósito: dar contexto narrativo al AI que popula
el bloque (DEV-111) o al operador que lo completa manualmente. Ejemplos:

- En un `TopContentBlock`: "incluir solo reels con ads, ignorar los
  orgánicos de la campaña Q4 vieja".
- En un `MetricsTableBlock(network=IG)`: "mostrar reach por source_type y
  agregar una row de engagement_rate solo si cayó >10% vs el mes anterior".
- En un `ChartBlock`: "usar la escala del Q1 aunque falten puntos de abril".

Es backend-only — NO se renderiza en el viewer público. Visible solo
en el admin de Django y en el payload de templates (DEV-118).

### Subtypes

```
TextImageBlock(ReportBlock)
├── title                CharField(max_length=200, blank=True)
├── body                 TextField(blank=True)
├── columns              PositiveSmallIntegerField(choices=[1,2,3], default=1)
├── image_position       CharField(choices=["left","right","top"], default="top")
├── image_alt            CharField(max_length=300, blank=True)
└── image                ImageField(upload_to="report_blocks/%Y/%m/", blank=True, null=True)


KpiGridBlock(ReportBlock)
├── title                CharField(max_length=200, blank=True)
└── (FK reverso: tiles → KpiTile)

KpiTile
├── kpi_grid_block       FK → KpiGridBlock (on_delete=CASCADE, related_name="tiles")
├── label                CharField(max_length=120)
├── value                DecimalField(max_digits=16, decimal_places=4)
├── period_comparison    DecimalField(max_digits=8, decimal_places=4, null=True, blank=True)  # optional Δ%
└── order                PositiveIntegerField
constraints:
  - UniqueConstraint(fields=["kpi_grid_block", "order"])


MetricsTableBlock(ReportBlock)
├── title                CharField(max_length=200, blank=True)
├── network              CharField(choices=Network.choices, null=True, blank=True)  # metadata hint
└── (FK reverso: rows → MetricsTableRow)

MetricsTableRow
├── metrics_table_block  FK → MetricsTableBlock (on_delete=CASCADE, related_name="rows")
├── metric_name          CharField(max_length=100)
├── value                DecimalField(max_digits=16, decimal_places=4)
├── source_type          CharField(choices=SourceType.choices, null=True, blank=True)
├── period_comparison    DecimalField(max_digits=8, decimal_places=4, null=True, blank=True)
└── order                PositiveIntegerField


TopContentBlock(ReportBlock)
├── title                CharField(max_length=200, blank=True)
├── kind                 CharField(choices=[POST, CREATOR])
├── limit                PositiveSmallIntegerField(default=6, validators=[MinValueValidator(1), MaxValueValidator(20)])
└── (FK reverso: items → TopContent — ya existe; FK cambia a apuntar a TopContentBlock específicamente)

# TopContent se mantiene con sus campos actuales (handle, caption, thumbnail,
# post_url, metrics JSON), solo cambia a qué FK'ea:
#   - FK `block` pasa de apuntar a `ReportBlock` genérico a apuntar a
#     `TopContentBlock` específicamente.
#   - FK `report` (denormalización actual) se elimina — es derivable via
#     `self.block.report`. Los Managers/queries existentes se adaptan.
#
# Excepción declarada: `TopContent.metrics` se mantiene como JSONField pese a
# la decisión anti-JSON general. Motivo: cada brand usa un set distinto de
# métricas por post/creator (P10: views/reach/likes/shared/comments/saved;
# UC: +tasa_retencion; FW: +repost), typearlas explotaría con 8+ nullables.
# Se re-evalúa en DEV-117 si aparece un pattern estable que justifique
# typearlas.


AttributionTableBlock(ReportBlock)
├── title                CharField(max_length=200, blank=True)
├── show_total           BooleanField(default=True)
└── (FK reverso: entries → OneLinkAttribution)

# OneLinkAttribution.report FK se elimina; se reemplaza por attribution_block FK.


ChartBlock(ReportBlock)
├── title                CharField(max_length=200, blank=True)
├── network              CharField(choices=Network.choices, null=True, blank=True)  # metadata hint
├── chart_type           CharField(choices=[("bar","Bar")], default="bar")  # enum extensible
└── (FK reverso: data_points → ChartDataPoint)

ChartDataPoint
├── chart_block          FK → ChartBlock (on_delete=CASCADE, related_name="data_points")
├── label                CharField(max_length=60)  # "Enero", "Marzo 26", etc.
├── value                DecimalField(max_digits=16, decimal_places=4)
└── order                PositiveIntegerField
```

### Choices reusadas

```python
# De backend/apps/reports/models.py (se mantienen):
class Network(models.TextChoices):
    INSTAGRAM = "INSTAGRAM", "Instagram"
    TIKTOK = "TIKTOK", "TikTok"
    X = "X", "X/Twitter"

class SourceType(models.TextChoices):
    ORGANIC = "ORGANIC", "Orgánico"
    INFLUENCER = "INFLUENCER", "Influencer"
    PAID = "PAID", "Pauta"
```

Se mueven del modelo `ReportMetric` (que se elimina) a un módulo `backend/apps/reports/choices.py` para ser reusadas por los bloques.

### Modelos que se eliminan

- `ReportMetric` (tabla entera). Sus choices `Network` y `SourceType` migran a `choices.py`.
- `ReportBlock.config` y `ReportBlock.type` (reemplazados por MTI + polymorphic_ctype).
- `ReportBlock.image` (ahora en `TextImageBlock.image` solamente).

### Modelos que sobreviven sin cambios

- `Report`, `Stage`, `Campaign`, `Brand`, `Client` — untouched.
- `BrandFollowerSnapshot` — sigue existiendo como source-of-truth brand-level cross-report; ya no lo consume el serializer, lo consume el operador/AI al popular ChartBlocks.

### Complexity budget (dim 4)

Regla del repo: ningún archivo debería exceder **300 líneas por diseño**. El refactor corre riesgo en `backend/apps/reports/models.py` (hoy ~220 líneas, sumar 6 subtipos + 3 child tables lo lleva a ~450). Plan de splitting:

```
backend/apps/reports/models/
├── __init__.py          # re-exports: Report, ReportBlock, TextImageBlock, ... para import compatibility
├── report.py            # Report, Stage-related references
├── blocks/
│   ├── __init__.py      # re-exports subtypes
│   ├── base.py          # ReportBlock (PolymorphicModel)
│   ├── text_image.py    # TextImageBlock
│   ├── kpi_grid.py      # KpiGridBlock + KpiTile
│   ├── metrics_table.py # MetricsTableBlock + MetricsTableRow
│   ├── top_content.py   # TopContentBlock + TopContent (mover desde models.py)
│   ├── attribution.py   # AttributionTableBlock + OneLinkAttribution
│   └── chart.py         # ChartBlock + ChartDataPoint
├── follower_snapshot.py # BrandFollowerSnapshot (standalone)
└── choices.py           # Network, SourceType (reusables)
```

Cada archivo queda <150 líneas. Imports externos usan `from apps.reports.models import ReportBlock, KpiGridBlock` — el `__init__.py` re-exporta para preservar compatibility.

Mismo principio para `admin.py`: splitting por subtipo en `admin/blocks/*.py` si el admin.py consolidado supera 300 líneas.

Serializers: `serializers/` directorio con un archivo por subtipo si el consolidado supera 300 líneas.

**Principio aplicado:** P2 (Single Responsibility) + P10 (Simplicity) — un archivo, un concepto.

## Admin UX

**Stack:** `django-polymorphic` + `adminsortable2` (ya presente).

- `ReportAdmin` tiene **un solo inline** `ReportBlockInline` (polymorphic). Muestra todos los blocks del reporte ordenados por `order`, con drag-to-reorder cross-subtipo.
- "Add block" → dropdown con los 6 subtypes → campos del subtipo aparecen dinámicamente.
- Click en un block existente → form del subtipo con sus campos + inlines de children (tiles, rows, data_points, items, entries) editables inline.
- Children (`KpiTile`, `MetricsTableRow`, `ChartDataPoint`, `OneLinkAttribution`, `TopContent`) tienen sus propios `TabularInline` dentro del admin del subtipo padre, con drag-reorder via `adminsortable2`.

`ReportBlockAdmin` standalone (registered) se mantiene con acceso polimórfico para edición avanzada o debugging.

## Serializers

`ReportBlockSerializer` base (polymorphic-aware) despacha por subtipo. Usando `django-polymorphic` serializer helpers:

```python
class ReportBlockSerializer(PolymorphicSerializer):
    model_serializer_mapping = {
        TextImageBlock: TextImageBlockSerializer,
        KpiGridBlock: KpiGridBlockSerializer,
        MetricsTableBlock: MetricsTableBlockSerializer,
        TopContentBlock: TopContentBlockSerializer,
        AttributionTableBlock: AttributionTableBlockSerializer,
        ChartBlock: ChartBlockSerializer,
    }
```

Cada serializer subtipo incluye sus children nested (tiles, rows, etc.) y devuelve un discriminador `type` en el payload para que el frontend despache.

`ReportDetailSerializer` pierde los fields `yoy`, `q1_rollup`, `follower_snapshots`. Queda con `blocks` (polymorphic list) + campos escalares del report + `metrics` y `onelink` se eliminan (la data ahora vive en los blocks).

## API contract (dim 3 — Boundaries)

El endpoint `/api/reports/<id>/` devuelve hoy `ReportDetailSerializer` con los fields `metrics`, `onelink`, `yoy`, `q1_rollup`, `follower_snapshots`, `blocks[config]`. **Post-refactor**:

- Eliminados del payload: `metrics`, `onelink`, `yoy`, `q1_rollup`, `follower_snapshots`.
- Agregados por block en `blocks[]`: subtype-specific fields + nested children (`tiles`, `rows`, `items`, `entries`, `data_points`).
- Discriminador: `type: "TextImageBlock" | "KpiGridBlock" | ...` en cada block (renombrado implícito de `TEXT_IMAGE` a `TextImageBlock` para alinear con el Python class name que `django-polymorphic` inyecta).

**API versioning**: el API está unversioned (`/api/`). **No hay consumers externos** todavía — solo el frontend de Next.js que se deploya en el mismo repo. Por lo tanto:
- La PR cambia backend + frontend en el mismo commit (atomicidad de deploy).
- No se mantiene compatibilidad con el shape viejo; deploy rompe si se separan.
- Si en el futuro aparece un consumer externo (ej. mobile app), se versiona con `/api/v2/` — out of scope para DEV-116.

**Validation at boundaries (P7)**:
- Entrada (admin forms, serializer writes): `django-polymorphic` + ModelForm + `full_clean()` validan choices, constraints, nullability.
- Salida (serializer read): schema consistente por subtipo; el discriminator `type` es el contract para el frontend.

## Frontend impact

`frontend/lib/api.ts`:

```typescript
export type ReportBlockDto =
  | TextImageBlockDto
  | KpiGridBlockDto
  | MetricsTableBlockDto
  | TopContentBlockDto
  | AttributionTableBlockDto
  | ChartBlockDto;

// Union discriminada por `type`. Cada DTO con sus campos tipados y children nested.
```

`ReportDto` pierde `metrics`, `onelink`, `follower_snapshots`, `yoy`, `q1_rollup`. Mantiene `blocks`.

Los renderers en `frontend/app/reports/[id]/blocks/*.tsx` ya despachan por `type`. Solo cambian los accesos a campos:
- `MetricsTableBlock.tsx`: lee `block.rows` en vez de `report.metrics.filter(...)`.
- `KpiGridBlock.tsx`: lee `block.tiles` en vez de calcular `reach_total` desde `report.metrics`.
- `ChartBlock.tsx`: lee `block.data_points` en vez de `report.follower_snapshots[network]`.
- `TopContentBlock.tsx`: lee `block.items` (ya está casi — el FK se formalizó recientemente).
- `AttributionTableBlock.tsx`: lee `block.entries` en vez de `report.onelink`.

## Migration & seed rewrite

**Migración destructiva** (no preservar data):

```
1. Delete all ReportMetric rows, ReportBlock rows, TopContent rows, OneLinkAttribution rows.
2. Drop ReportMetric table.
3. Drop ReportBlock.config, ReportBlock.type, ReportBlock.image fields.
4. Alter TopContent: remove report FK, change block FK to point to TopContentBlock.
5. Alter OneLinkAttribution: remove report FK, add attribution_block FK.
6. Create tables for 6 subtypes (MTI child tables).
7. Create child tables: KpiTile, MetricsTableRow, ChartDataPoint.
8. Add uniqueness constraints.
```

Debería caber en una sola migración Django. Nombre sugerido: `0009_typed_blocks.py`.

**`seed_demo.py`** se reescribe:

- Eliminar la creación de `ReportMetric` rows.
- Cada reporte con layout completo crea los 11 bloques como instancias tipadas:
  - `KpiGridBlock(order=1, title="KPIs del mes")` + tiles con (label, value).
  - `MetricsTableBlock(order=2, network=null, title="Mes a mes")` — cross-network, rows con `period_comparison` populado.
  - `MetricsTableBlock(order=3, network=INSTAGRAM, title="Instagram")` + rows IG.
  - `MetricsTableBlock(order=4, network=TIKTOK, title="TikTok")` + rows TK.
  - `MetricsTableBlock(order=5, network=X, title="X / Twitter")` + rows X.
  - `TopContentBlock(order=6, kind=POST, limit=6, title="Posts del mes")` + items.
  - `TopContentBlock(order=7, kind=CREATOR, limit=6, title="Creators del mes")` + items.
  - `AttributionTableBlock(order=8, show_total=True)` + OneLinkAttribution entries.
  - `ChartBlock(order=9, network=INSTAGRAM, chart_type="bar", title="Followers IG")` + data_points.
  - `ChartBlock(order=10, network=TIKTOK, chart_type="bar", title="Followers TikTok")` + data_points.
  - `ChartBlock(order=11, network=X, chart_type="bar", title="Followers X")` + data_points.
- Bloques "Year over year" y "Q1 rollup" del seed actual se eliminan.

Credenciales demo (`belen.rizzo@balanz.com` / `balanz2026`) se mantienen.

## Testing

### Strategy overview

Tres capas de tests, cubriendo las dimensiones 1 y 9 de entropy-scan:

1. **Unit** — por modelo, validan constraints, clean(), defaults, cascades.
2. **Integration** — serializer polimórfico end-to-end (input queryset → JSON output); admin form POST.
3. **E2E smoke** — user-visible; Playwright contra frontend con stack completo.

**Coverage target:** >85% en `backend/apps/reports/models/blocks/*`, >80% en `admin/` y `serializers/`. Medido con `pytest --cov`. Rutas triviales (Django Admin defaults) pueden quedar sin cover explícito, con `pragma: no cover` si hace falta.

### Unit tests (pytest)

Por subtipo (un archivo cada uno en `backend/tests/unit/blocks/`):

- `test_text_image_block_model.py` — constraints, clean(), save con defaults (`columns=1`, `image_position="top"`), image upload validators, order uniqueness dentro del Report.
- `test_kpi_grid_block_model.py` — KpiTile inline creation, `UniqueConstraint(kpi_grid_block, order)`, cascade on delete, `period_comparison` nullable.
- `test_metrics_table_block_model.py` — `Network.choices` acepta/rechaza valores, `network=null` OK, MetricsTableRow cascade, `source_type` y `period_comparison` nullable por row.
- `test_top_content_block_model.py` — `kind` required, `limit` validator (1-20), `TopContent.block` FK points to `TopContentBlock` subtype (no al base), `TopContent.report` FK eliminado.
- `test_attribution_table_block_model.py` — `OneLinkAttribution.attribution_block` FK, `OneLinkAttribution.report` eliminado, `show_total` default True.
- `test_chart_block_model.py` — `chart_type` choices ("bar" único valor válido por ahora), ChartDataPoint cascade, `label` + `value` required, `order` unique dentro del chart.

### Integration tests

- `test_polymorphic_serializer.py` — dado un Report con bloques de los 6 tipos, llamar `ReportDetailSerializer` y verificar:
  - El payload devuelve `blocks` como lista ordenada.
  - Cada block tiene discriminator `type` correcto.
  - Nested children (tiles, rows, data_points, items, entries) aparecen con sus fields.
  - No aparecen fields eliminados (`metrics`, `onelink`, `yoy`, `q1_rollup`, `follower_snapshots`).
- `test_polymorphic_prefetch.py` — verifica que la query de serialización no es N+1: usar `django-polymorphic`'s `PolymorphicQuerySet.select_related()` para fetchear subtipos; aserto que **≤2 queries SQL** por Report (1 para blocks + 1 por cada subtype con children). Mediado con `django-debug-toolbar` o `CaptureQueriesContext`.
- `test_migration_0009.py` — corre la migración contra una DB Postgres fresca y verifica que las tablas y constraints quedan bien. Usa `django-test-migrations` si está disponible, o `MIGRATION_MODULES={}` + `call_command("migrate")` fixture.

### Admin tests (smoke)

- `test_admin_polymorphic_inline.py` — Django `Client` logueada como superuser:
  - POST a `/admin/reports/report/add/` con payload que incluye un `KpiGridBlock` inline → verifica creación.
  - POST al changeform de Report con blocks pre-existentes → verifica edición.
  - GET a `/admin/reports/reportblock/add/` muestra el dropdown de subtypes (contenido HTML).
  - Verifica que `instructions` TextField aparece en el form de cada subtipo.

### E2E (Playwright)

- `frontend/tests/report-blocks.spec.ts` — smoke existente; los pill labels esperados (KPIs, MES A MES, INSTAGRAM, TIKTOK, X/TWITTER, POSTS, CREATORS, ATRIBUCIÓN, FOLLOWERS) deberían seguir apareciendo **asumiendo que el seed regenera los 11 blocks en el mismo orden**. Si algo difiere, el spec se actualiza en esta misma PR.
- `frontend/tests/campaigns.spec.ts` — untouched (la "ÚLTIMO" pill que agregamos hoy sobrevive).
- `frontend/tests/reports.spec.ts` — smoke del viewer, untouched excepto si cambia el shape del title/metadata.

### Tests que se eliminan

- `backend/tests/unit/test_pdf_validators.py` — sobrevive (es de `original_pdf`, no de blocks).
- `backend/tests/unit/test_report_detail_serializer.py` — **se reescribe** para el nuevo payload polimórfico.
- `backend/tests/unit/test_report_nplus1.py` — **se reescribe** para chequear prefetch polimórfico (ver `test_polymorphic_prefetch.py`).
- `backend/tests/unit/test_report_viewer_models.py` — **se reescribe** para cubrir los 6 subtipos.
- `backend/tests/unit/test_reports_detail_view.py` — adapta a nuevos fields.
- `backend/tests/unit/test_topcontent_block_fk.py` — adapta al nuevo FK target (`TopContentBlock` específico).
- `backend/tests/unit/test_pdf_validators.py` — sin cambios.

Tests eliminados completamente:
- Tests del `registry.py` y `schemas.py` (si existen en `backend/tests/unit/test_block_config*.py`).
- Tests que dependen de `ReportMetric` directo.

### Testability design notes

Siguiendo P1 (Tests Before Code) y P5 (Depend on Abstractions):

- Todos los model tests usan `pytest-django` fixtures (`db`, `client`, custom factories). Sin dependencias inyectables — los modelos Django son self-contained.
- Admin tests usan `django.test.Client` con un superuser fixture, NO unittest ni selenium — queremos black-box del admin.
- Serializer tests instancian con querysets reales (factory_boy) para cubrir el path polimórfico. NO mockear `django-polymorphic` internals — si rompe la librería, queremos saberlo.
- **Antes de escribir cada subtipo, el test falla primero** (TDD por fase, P1). El plan de implementación (DEV-116 plan) va a ser fase-por-fase con este ordenamiento.

### Requisito del repo

CLAUDE.md del repo: "Unit test para la lógica de backend nueva o modificada. E2E update cuando el cambio es user-visible." Se cumplen ambos.

## Non-functional requirements

### Security & permissions (dim 7)

- **Tenant scoping preservado**: toda query de blocks pasa por `Report` → `stage.campaign.brand.client_id`. El refactor no toca este chain; `ReportBlock` sigue siendo FK a `Report` y la permission layer en `CampaignViewSet` + `ReportViewSet` sigue aplicando. Gotcha conocido del repo (CLAUDE.md): tenant scoping va en la view, no en middleware — se preserva.
- **Admin permissions**: Django admin se accede con superuser/staff, permissions via `django.contrib.auth`. Euge opera como staff — no cambia. Principio P7 (Security by Default).
- **Input validation at boundaries**: 
  - Admin forms → `django-polymorphic` + Django ModelForm validation con `full_clean()` en save (CHECK constraints, choices, null/blank).
  - Serializer input (cuando DEV-111 use DRF writeable serializers) → DRF `PolymorphicSerializer` valida por subtipo. No-op en DEV-116 (serializer es read-only).
  - Migration: data migration 0009 es destructiva, no tiene input de usuario, seguro.
- **Secrets**: no se agregan nuevos. `django-polymorphic` no usa secrets.
- **Dependency audit**: `django-polymorphic` revisar versión compatible con Django 5 (última release >= 3.1, activamente mantenida, 2K+ stars). Check license (BSD-3-Clause, compatible). No transitive deps riesgosas.
- **SQL injection**: no raw queries introducidas; ORM de Django maneja escape.
- **CSRF/XSS**: admin views ya tienen CSRF by default; el `instructions` TextField se renderiza en admin templates que escapan HTML por default (no marcar `safe`).
- **Principio aplicado:** P7 (Security by Default), P9 (Fail Fast) — `full_clean()` corre en save(), errores surfaceados inmediatamente.

### Observability (dim 10)

Este refactor es primariamente backend admin, sin endpoints nuevos. Logging strategy:

- **Migration**: Django corre migraciones con su logger default. Agregar un `RunPython` operation con `logger.info("typed_blocks_migration_complete", extra={"blocks_created": N})` al final de 0009 para tener señal en el deploy log de Hetzner.
- **Admin actions**: Django admin auto-logea creación/edición/borrado en `django.contrib.admin.models.LogEntry`. No agregar logging custom a menos que necesitemos más contexto.
- **Serializer errors**: si `PolymorphicSerializer` falla al resolver un subtipo (ej. row huérfana), loguear como WARNING con `block_id` en el contexto. Principio P9 (Fail Fast).
- **Metrics**: no se agregan metrics nuevas en este ticket. DEV-111/112 (Metricool fetcher) va a necesitar metrics de "% blocks auto-filled" y latencia de AI calls, pero es out of scope.
- **Health checks**: existing `/health` endpoint (si existe) se mantiene. No se toca.
- **Correlation IDs**: no aplica directamente; el admin no es API con request tracing.
- **Principio aplicado:** P8 (Evidence Over Assumptions) — migración logea resultado visible en deploy logs para verificar que corrió.

### Frontend quality (dim 11)

Frontend tiene cambios menores (DTO union + field access updates) — no se introducen nuevos componentes ni refactor visual.

- **Design tokens**: los renderers existentes ya consumen `var(--chirri-*)` CSS vars, no se agregan colores hardcodeados. Sin cambios.
- **Component size**: los renderers actuales (`MetricsTableBlock.tsx`, `KpiGridBlock.tsx`, etc.) están todos <150 líneas. Con el cambio de field access, se mantienen en ese rango. Complexity budget OK.
- **Accessibility**: los renderers existentes ya usan `<table>`, `<th scope>`, ARIA labels donde aplica (verificado durante DEV-105). Sin regresión.
- **Performance**:
  - Bundle size: `ReportBlockDto` como union discriminada no agrega bundle overhead (TypeScript compile-time only).
  - List rendering: blocks se mapean con `key={block.id}` — ya implementado.
  - No lazy loading necesario (un reporte tiene 11 blocks máximo).
- **State management**: sin cambios — los blocks se reciben como props del server component, no hay client state nuevo.
- **i18n**: todas las strings user-facing son en español, hardcoded en los renderers. El repo no tiene sistema i18n global (consciente — CLAUDE.md). Sin cambios.
- **Responsive**: los layouts existentes ya son responsive via CSS Grid; sin cambios.
- **TypeScript strictness**: typecheck debe quedar limpio con los nuevos DTOs. Ejecutar `npm run typecheck` como parte del criterio de done.

### Git strategy (dim 8)

Commits atómicos, uno por concerns lógico. Estructura sugerida:

1. `feat(reports): scaffold typed block hierarchy with django-polymorphic` — agrega `django-polymorphic` a requirements, crea models/blocks/ con las 6 subclasses + child tables, migración 0009, SIN borrar aún los modelos viejos. Tests unit para cada subtype (P1 TDD — tests fallan antes, pasan después).
2. `refactor(reports): move ReportMetric removal + admin to typed blocks` — elimina `ReportMetric`, `ReportBlock.config/type/image`, reemplaza registry/schemas. Admin polimórfico con los 6 ModelAdmin. `seed_demo` reescrito. Tests admin.
3. `refactor(reports): polymorphic serializer + frontend DTOs` — `PolymorphicSerializer`, union DTOs en `lib/api.ts`, renderers ajustados. Integration tests del serializer.
4. `docs: update QUALITY_SCORE + README for typed blocks refactor` — ver repo hygiene abajo.

PR target: `main` desde una branch nueva (`dzacharias/dev-116-typed-blocks-refactor`). No merge directo a `development` salvo que Dani lo decida — el deploy-on-push a development hace que cada commit se deploye, queremos una PR review.

Ownership: Dani (single dev). Sin bloqueantes de knowledge — el spec + plan capturan el contexto suficiente para picked up por otro dev si fuera necesario.

**Principio aplicado:** P10 (Simplicity) — commits chicos, reviewable individualmente.

### Documentation updates (dim 12)

Como parte de DEV-116, actualizar:

- **`docs/QUALITY_SCORE.md`**: re-evaluar el domain `reports` después del refactor. Target: mantener B o subir a A. El refactor elimina complejidad (registry, schemas, aggregations) → expectativa A si queda limpio.
- **`docs/SPEC.md`** (si existe): actualizar la sección del reports domain reflejando la nueva jerarquía de blocks. Verificar antes de escribir si existe.
- **`README.md`**: verificar si menciona `ReportBlock.config` o el esquema JSON; si sí, actualizar. Probable: actualización chica o nula.
- **`backend/apps/reports/README.md`** (si existe): actualizar con el nuevo módulo structure (`models/blocks/`, `admin/`, `serializers/`).
- **`CLAUDE.md` del repo**: el gotcha de "tenant scoping va en la view" se mantiene válido — no tocar.
- **Este spec**: al terminar DEV-116, el spec queda como histórico en `docs/superpowers/specs/`. No se archiva ni elimina (pattern del repo preservar specs para auditoría).
- **Plan file** (`docs/superpowers/plans/`): se genera en el próximo step de entropy-driven. Se archiva (o deja) según pattern del repo cuando DEV-116 cierra.

### CI/CD & Deployment (dim 13)

El repo tiene GitHub Actions configurado (ver `.github/workflows/test.yml` + `deploy.yml`) con pipeline Impactia-style:

**Stage 1 — PR gate**: `test.yml` corre en cada PR a `main`/`development`:
- Backend: `pytest` con Postgres service.
- Frontend: `npm run typecheck` + `npm run build` + `npm run test:e2e:smoke`.
- **Requirement del refactor**: migration 0009 corre contra Postgres fresco en CI (los tests de migración en `test_migration_0009.py` lo cubren).

**Stage 2 — Build**: Docker build del backend con SHA pinning (`image: ...:${{ github.sha }}`). Ya está configurado.

**Stage 3 — Deploy**: `deploy.yml` en push a `development` → Hetzner. Incluye:
- `python manage.py migrate` antes de restart.
- Migration 0009 es **destructiva** (elimina ReportMetric table); como nada está en prod, no hay riesgo de data loss. Documentar en el commit message: "This migration drops ReportMetric. No production data exists at time of merge."

**Stage 4 — Post-deploy smoke**: Chirri Portal hoy NO tiene smoke post-deploy automatizado en el pipeline — es manual. **Follow-up ticket sugerido** (no blocking DEV-116): agregar job post-deploy con `playwright test --config=playwright-smoke.config.ts` con `baseURL=https://dev.chirri.example.com`.

**Stage 5 — Rollback**: en caso de falla post-migration:
- Opción A (blue-green): no disponible, Hetzner deployment es in-place.
- Opción B (revert commit + re-deploy): rollback deploy es revert del commit en `development` + push. La migración destructiva NO se puede reverter trivialmente — hay que restaurar de backup o rehacer seed. Aceptable dado que es pre-prod.
- Documentar en `docs/DEPLOY.md` (crear si no existe) el proceso de rollback para futuras migraciones destructivas.

**Secrets**: sin nuevos secretos para DEV-116.

**Environment**: deploy a Hetzner development → staging para Balanz demo. Prod real todavía no existe (pilot no lanzado).

**Principio aplicado:** P8 (Evidence Over Assumptions) — post-deploy smoke + manual verification que seed_demo corra limpio en el ambiente.

## Out of scope

Explícitamente NO incluido en DEV-116:

- Nuevos block types identificados por DEV-117 (discovery). Se agregan en tickets follow-up.
- Cambios en DEV-118 (Templates) — se adapta a modelos polimórficos cuando arranque.
- Cambios en DEV-111/112 (Metricool fetcher) — escribirán al subtipo correcto; se refleja en su scope cuando arranque.
- Reimplementación de YoY y Q1 rollup — eliminados, se re-introducen si y cuando surja demanda.
- Dashboard de analytics sobre data histórica — explícitamente fuera; si se necesita, es un ticket separado con fuente real (Metricool, warehouse).

## Impact on other tickets

- **DEV-117** (discovery): los gaps que identifique se modelan como Django subclasses nuevas, no como JSON config extras. Aligera el ticket.
- **DEV-118** (templates): el clonado es polimórfico. `django-polymorphic` permite `block.get_real_instance()` para clonar con los campos correctos del subtipo. Re-spec cuando arranque el ticket.
- **DEV-111** (Metricool mapper): el scope cambia de "mapper determinístico" a "mapper AI-mediado". El AI lee template con blocks tipados + metadata (`network`, `kind`, `chart_type`) + data de Metricool → puebla blocks. Anotar en DEV-111 al cerrar DEV-116.
- **DEV-112/113** (Metricool admin action + tests): trivialmente adaptados al flujo AI-mediado.

## Dependencies

- `django-polymorphic` — nueva dependencia de backend. Agregar a `requirements.txt`.
- `adminsortable2` — ya presente, se sigue usando para drag-reorder.

Sin dependencias frontend nuevas.

## Estimation

**2 días de trabajo** (1 dev full-time). Desglose:

- Modelos + migración destructiva: 4h.
- Admin + `django-polymorphic` wiring: 3h.
- Serializers (polymorphic dispatcher): 2h.
- Frontend DTOs + renderer updates: 3h.
- `seed_demo` rewrite: 2h.
- Tests (unit + smoke adaptation): 4h.

Buffer: ~2h para fixes imprevistos en herencia multi-tabla (migration edge cases, admin glitches).

## Acceptance criteria

- Admin de Django crea y edita blocks de cada tipo sin tocar JSON.
- "Agregar bloque" → dropdown de tipo → campos del subtipo aparecen inline, gracias a `django-polymorphic`.
- Campo `instructions` (TextField) visible y editable en el admin de cada subtipo (heredado de la base).
- Django `full_clean()` rechaza valores inválidos a nivel DB/modelo (choices, constraints).
- `seed_demo` corre limpio y genera reportes funcionales que renderizan en el frontend.
- E2E smoke (`report-blocks.spec.ts`, `campaigns.spec.ts`, `reports.spec.ts`) pasan con los blocks tipados.
- Eliminado: `backend/apps/reports/blocks/registry.py`, `backend/apps/reports/blocks/schemas.py`, `ReportMetric` model, `build_yoy`/`build_q1_rollup`/`build_follower_snapshots` functions.
- Frontend renderiza los 6 tipos de block con el nuevo payload tipado; typecheck limpio.
