# DEV-83 · Excel Report Importer (Fase 1 — mapping rígido)

**Linear:** [DEV-83](https://linear.app/impactia/issue/DEV-83/importador-de-reportes-via-excel-template-fase-1-mapping-rigido)
**Status:** Draft
**Owner:** Daniel Zacharias
**Date:** 2026-04-20

## Contexto

Hoy el equipo de Chirri (Julián) arma los reportes a mano en Google Slides. El piloto (Balanz) necesita que puedan subir un reporte al portal y que el cliente lo vea renderizado, sin tocar Slides.

Fase 1 (este ticket): template `.xlsx` con formato **fijo** que definimos nosotros, sin AI, sin tolerancia a variaciones. Julián completa el template y hace upload desde el Django admin. El import crea un `Report` en estado `DRAFT` + todas las filas anidadas (métricas, top content, attribution) en una transacción. Julián revisa el DRAFT en el admin, sube thumbnails por los inlines, y publica.

Fase 2 (ticket aparte): AI best-effort para tolerar formatos distintos.

## Goals

- Reducir el tiempo de preparación de un reporte de horas (en Slides) a minutos (llenar un Excel + subir).
- Eliminar errores de data entry manuales (copy-paste desde planillas a Slides).
- Que Julián trabaje sin pedir ayuda a devs: si el Excel tiene errores, los ve de forma clara (qué hoja, qué fila, qué columna, por qué).
- Zero stacktrace al usuario en cualquier error.

## Non-goals

- AI-assisted mapping (fase 2, ticket aparte).
- UI custom fuera de Django admin.
- Edición post-import (el admin ya lo permite).
- Bulk import de muchos reportes en un archivo (1 archivo = 1 reporte).
- Import de `BrandFollowerSnapshot` (brand-level, no report-scoped — separado).

## Architecture

### Componentes

Todos dentro de `apps/reports/`:

```
apps/reports/importers/
  __init__.py
  bundle_reader.py     — pure function: bytes (zip or xlsx) → (xlsx_bytes, Dict[filename → image_bytes], List[ImporterError])
  excel_parser.py      — pure function: xlsx_bytes + image_names → (ParsedReport, List[ImporterError])
  excel_writer.py      — pure function: () → BytesIO (template vacío, 10 hojas)
  excel_exporter.py    — pure function: Report → BytesIO (xlsx con data existente, misma shape que el template)
  errors.py            — ImporterError(sheet, row, column, reason)
  schema.py            — mapping español → Python field names, enums, validaciones

apps/reports/admin.py  (extendido) — vista custom `import/`, botón en changelist
apps/reports/management/commands/
  dump_report_template.py          — CLI wrapper de excel_writer.build_template()
  dump_report_example.py           — CLI wrapper de excel_exporter.export(report_id)
  validate_import.py               — (Etapa 2) corre bundle_reader+parser sin DB, imprime errores
```

**Principios de separación (P2 SRP, P5 DIP):**

- `bundle_reader` es el único que toca `zipfile` — resuelve el upload (ZIP o XLSX pelado) y entrega al parser el `xlsx_bytes` + un dict de imágenes disponibles. Valida zip-slip, extensiones y caps de tamaño antes de pasar nada al parser.
- `excel_parser` no importa nada de Django ni de modelos — trabaja con dicts y dataclasses. Recibe el set de filenames disponibles para validar referencias `imagen` sin saber nada de bytes. Facilita test unitario puro.
- `excel_writer` genera un workbook **vacío** sin tocar DB ni filesystem — retorna `BytesIO` con las 10 hojas, headers, dropdowns y la hoja `Instrucciones`. El caller decide dónde escribirlo.
- `excel_exporter` genera un workbook **lleno con un report existente** — misma shape que el template. Sirve para (a) el ejemplo de referencia del equipo Chirri, (b) re-editar un report importado antes sin tipear todo de cero.
- `errors.py` es la única clase de error estructurada — el admin serializa `List[ImporterError]` para renderizar la tabla.
- `schema.py` centraliza el mapping español↔Python para que no haya strings mágicos dispersos.
- El admin es un **thin wrapper**: recibe el upload, llama al parser, si hay errores los muestra, si no, crea rows en `transaction.atomic()` y redirige.

### Staged delivery (template primero, parser después)

Antes de escribir una sola línea del parser o del admin, entregamos el **formato del template** + un **ejemplo lleno** para review del equipo Chirri. Si el formato es sólido, lo otro sigue mecánico. Si no, ahorramos rework.

**Etapa 1 — Template + ejemplo (scope de esta primera PR)**:
1. `schema.py` — mapping y choice labels (compartido por writer/parser/exporter).
2. `excel_writer.build_template()` — genera las 10 hojas con headers, dropdowns, hoja `Instrucciones` formateada.
3. `dump_report_template` management command — wrapper CLI del writer.
4. `excel_exporter.export(report)` — toma un Report y lo escupe al mismo shape que el template.
5. `dump_report_example --report <id>` — wrapper CLI del exporter. Por defecto usa el report Abril del seed (`_seed_all_blocks_layout`, cubre los 8 block types).
6. Review con Julián/Euge del xlsx vacío + ejemplo Abril lleno. Iterar formato si hace falta.

**Etapa 2 — Parser + admin + import + tests (PR siguiente)**:
7. `bundle_reader` + `excel_parser` + `ImportReportForm` + admin views.
8. Full test suite (unit + E2E).

Ambas etapas caen en DEV-83; la separación es operativa (review-gate) no scope.

### Flujo end-to-end

```
[Julián] → /admin/reports/report/
         → click "Descargar template"
           → admin view llama excel_writer.build_template() → HttpResponse bytes
           → download .xlsx
         → llena el Excel offline
         → /admin/reports/report/ → click "Importar desde Excel"
         → form: Stage (autocomplete) + archivo .xlsx
         → submit → admin view:
            → excel_parser.parse(bytes) → (ParsedReport, errors)
            → if errors: re-render form con tabla de errores (no toca DB)
            → if ok: transaction.atomic() → crea Report DRAFT + metrics + top_content + onelink
            → redirect a /admin/reports/report/{id}/change/
         → change form con todo populado (inlines ya renderizan metrics, destacados, attribution)
         → Julián sube thumbnails en el inline de Destacados
         → action "Publicar reportes seleccionados" → status = PUBLISHED
```

## Bundle format (ZIP + imágenes)

El upload es un **único archivo `.zip`** con esta estructura:

```
reporte.zip
├── reporte.xlsx           # el template lleno (único .xlsx en la raíz)
└── images/
    ├── post_1.jpg
    ├── post_2.png
    ├── creator_sofi.jpg
    └── ...
```

- Las celdas `imagen` del Excel referencian imágenes por **filename relativo a `images/`** (ej: `post_1.jpg`, no `images/post_1.jpg`, no paths absolutos).
- Imágenes referenciadas y ausentes del ZIP → error de validación con `(hoja, fila, columna, "imagen 'X' no encontrada en images/")`.
- Imágenes presentes en el ZIP pero no referenciadas → warning no-bloqueante (no falla el import).
- Extensiones aceptadas en `images/`: `.jpg`, `.jpeg`, `.png`, `.webp`. Otras se rechazan con error estructural.
- El ZIP se procesa en memoria con `zipfile` stdlib (no se escribe a disco hasta que cada `ImageField.save()` persiste su imagen, ya en `transaction.atomic()`).

**Por qué ZIP y no multi-file upload**: un único archivo atómico, simple de re-subir si falla, el form del admin queda con un `FileField` estándar, y los errores son claros ("falta imagen X" > "olvidaste subir 1 de 20 archivos").

## Excel template

Cubre los **8 tipos de block** del modelo tipado actual (post DEV-116/129/130): `TextImageBlock`, `ImageBlock`, `KpiGridBlock`, `MetricsTableBlock`, `TopContentsBlock`, `TopCreatorsBlock`, `AttributionTableBlock`, `ChartBlock`. Todas las imágenes de cualquier block se referencian por filename relativo a `images/` del ZIP.

### Convención transversal: `nombre` como ID de bloque

- Cada block instance tiene un `nombre` (string elegido por Julián, ej: `intro`, `kpis_mes`, `hero`).
- **Único en todo el archivo** — no puede repetirse entre hojas distintas (el parser deduce el tipo de block de la hoja donde aparece el `nombre`).
- La hoja `Reporte` lo referencia desde la sección Layout para definir el orden de aparición.
- En blocks con sub-items (Kpis, MetricsTables, TopContents, TopCreators, Attribution, Charts) la tabla es **denormalizada**: los fields del parent block se repiten en cada row del item, agrupados por `nombre`.

### Hojas (en este orden)

| # | Hoja | Shape | Mapea a |
|---|---|---|---|
| 1 | `Instrucciones` | texto | cómo llenar + armar el ZIP |
| 2 | `Reporte` | key-value + Layout | `Report` (scalars) + orden de bloques |
| 3 | `TextImage` | tabular (1 row = 1 block) | `TextImageBlock` |
| 4 | `Imagenes` | tabular (1 row = 1 block) | `ImageBlock` |
| 5 | `Kpis` | tabular denormalizada | `KpiGridBlock` + `KpiTile` |
| 6 | `MetricsTables` | tabular denormalizada | `MetricsTableBlock` + `MetricsTableRow` |
| 7 | `TopContents` | tabular denormalizada | `TopContentsBlock` + `TopContentItem` |
| 8 | `TopCreators` | tabular denormalizada | `TopCreatorsBlock` + `TopCreatorItem` |
| 9 | `Attribution` | tabular denormalizada | `AttributionTableBlock` + `OneLinkAttribution` |
| 10 | `Charts` | tabular denormalizada | `ChartBlock` + `ChartDataPoint` |

Total: **10 hojas**. Orden fijo (writer las genera siempre igual); hojas vacías = no hay blocks de ese tipo. Hoja faltante en el upload = error estructural único.

### Hoja 2 · `Reporte` (key-value + Layout inline)

**Bloque superior — data escalar del report** (key-value, 2 columnas):

| Campo | Tipo | Obligatorio | Ejemplo |
|---|---|---|---|
| tipo | enum | sí | `Mensual` |
| fecha_inicio | fecha | sí | `01/04/2026` |
| fecha_fin | fecha | sí | `30/04/2026` |
| titulo | texto | no | `Reporte general · Abril` |
| intro | texto | no | `Abril fue el mes…` |
| conclusiones | texto | no | `El ratio click→download de abril…` |

- `tipo` dropdown: `Influencer / General / Quincenal / Mensual / Cierre de etapa`.
- Fechas: aceptamos `DD/MM/YYYY`, `DD-MM-YYYY`, ISO `YYYY-MM-DD`. Normalizadas a `date`.

**Bloque inferior — Layout** (tabular, debajo del header `# Layout (orden de bloques)`):

| orden | nombre |
|---|---|
| 1 | intro |
| 2 | kpis_mes |
| 3 | mtm_cross |
| 4 | top_posts |
| 5 | hero |

- `orden`: entero 1-based, único dentro del Layout.
- `nombre`: debe existir exactamente en una de las hojas de blocks (`TextImage`/`Imagenes`/`Kpis`/etc.). Si no aparece en ninguna → error. Si aparece en más de una → error.
- Blocks definidos en sus hojas pero no listados en Layout → warning (no se renderizan en el report, pero no bloquea el import).

### Hoja 3 · `TextImage`

Una fila por block. Sin sub-items.

| nombre | title | body | imagen | image_alt | image_position | columns |
|---|---|---|---|---|---|---|
| intro | Contexto del mes | Abril fue la primera bajada real... | intro.jpg | Creator Flor Sosa grabando... | left | 1 |
| cierre | Qué probamos para mayo | Seguimos apostando al formato reel... | | | top | 2 |

- `imagen`: opcional. Filename dentro de `images/`.
- `image_position` dropdown: `left / right / top / bottom`.
- `columns`: 1 o 2.

### Hoja 4 · `Imagenes`

Una fila por block. Sin sub-items.

| nombre | title | caption | imagen | image_alt | overlay_position |
|---|---|---|---|---|---|
| hero | El mes en fotos | Momentos destacados del contenido... | hero.jpg | Collage visual del mes | bottom |

- `imagen`: **obligatoria** (ImageBlock requiere imagen).
- `overlay_position` dropdown: `top / bottom / center / none`.

### Hoja 5 · `Kpis` (denormalizada)

Parent fields (`block_title`) se repiten en cada row. Parser agrupa por `nombre`.

| nombre | block_title | item_orden | label | value | period_comparison |
|---|---|---|---|---|---|
| kpis_mes | KPIs del mes | 1 | Reach total | 3120000 | 9.9 |
| kpis_mes | KPIs del mes | 2 | Engagement rate | 5.3 | 0.5 |
| kpis_mes | KPIs del mes | 3 | App downloads | 310 | |
| kpis_mes | KPIs del mes | 4 | Click→download | 12.8 | 3.1 |

- `block_title`: repetido en cada row del mismo `nombre`. Si rows de un mismo `nombre` tienen `block_title` distinto → error.
- `period_comparison`: delta % vs período anterior. Opcional.

### Hoja 6 · `MetricsTables` (denormalizada)

| nombre | block_title | block_network | item_orden | metric_name | value | source_type | period_comparison |
|---|---|---|---|---|---|---|---|
| mtm_cross | Mes a mes | | 1 | engagement_rate | 5.3 | Orgánico | 0.5 |
| mtm_cross | Mes a mes | | 2 | followers_gained | 21300 | Orgánico | 15.7 |
| mtm_cross | Mes a mes | | 3 | app_downloads | 310 | Influencer | 32 |
| mtm_ig | Instagram | Instagram | 1 | reach | 312000 | Orgánico | 9.9 |
| mtm_ig | Instagram | Instagram | 2 | reach | 594000 | Pauta | 16.0 |
| mtm_ig | Instagram | Instagram | 3 | reach | 1810000 | Influencer | 10.4 |

- `block_network` dropdown: `Instagram / TikTok / X / (vacío)`. Vacío = tabla cross-network.
- `source_type` dropdown: `Orgánico / Influencer / Pauta`.
- `metric_name`: texto libre en snake_case (`reach`, `impressions`, `engagement_rate`, `followers_gained`, `app_downloads`).

### Hoja 7 · `TopContents` (denormalizada)

| nombre | block_title | block_network | block_period_label | block_limit | item_orden | imagen | caption | post_url | source_type | views | likes | comments | shares | saves |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| top_posts | Posts del mes | Instagram | abril | 6 | 1 | post_1.jpg | Reel testimonial de Flor | https://... | Orgánico | 120000 | 5000 | 120 | 80 | 300 |
| top_posts | Posts del mes | Instagram | abril | 6 | 2 | post_2.jpg | Carrusel educativo | https://... | Influencer | 95000 | 4200 | 98 | 60 | 210 |

- `imagen`: opcional. Si está vacío, el item se crea sin thumbnail.
- `block_limit`: cuántos top items renderiza el block en el viewer (1-20). El count real de rows en la hoja puede ser ≤ `block_limit`.

### Hoja 8 · `TopCreators` (denormalizada)

| nombre | block_title | block_network | block_period_label | block_limit | item_orden | imagen | handle | post_url | views | likes | comments | shares |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| top_creators | Creators del mes | Instagram | abril | 6 | 1 | creator_flor.jpg | @flor.sosa | https://... | 180000 | 7800 | 240 | 150 |

- `handle`: **obligatorio**. Incluir `@`.
- `imagen`: opcional.

### Hoja 9 · `Attribution` (denormalizada)

| nombre | block_title | block_show_total | item_orden | handle | clicks | app_downloads |
|---|---|---|---|---|---|---|
| attr | Atribución OneLink | TRUE | 1 | @sofi.gonet | 1200 | 180 |
| attr | Atribución OneLink | TRUE | 2 | @flor.sosa | 2400 | 310 |

- `block_show_total` boolean: `TRUE / FALSE`.
- Sin items = se deja la hoja vacía. Solo aplica a marcas con app mobile.

### Hoja 10 · `Charts` (denormalizada)

| nombre | block_title | block_network | chart_type | point_orden | point_label | point_value |
|---|---|---|---|---|---|---|
| chart_followers | Followers Instagram | Instagram | bar | 1 | Enero | 99500 |
| chart_followers | Followers Instagram | Instagram | bar | 2 | Febrero | 104568 |
| chart_followers | Followers Instagram | Instagram | bar | 3 | Marzo | 107072 |
| chart_followers | Followers Instagram | Instagram | bar | 4 | Abril | 110240 |
| chart_er | Engagement rate | | line | 1 | Enero | 3.9 |
| chart_er | Engagement rate | | line | 2 | Febrero | 4.2 |
| chart_er | Engagement rate | | line | 3 | Marzo | 4.8 |
| chart_er | Engagement rate | | line | 4 | Abril | 5.3 |

- `chart_type` dropdown: `bar / line`.
- `block_network`: opcional. Metadata hint.

### Hoja 1 · `Instrucciones`

Primera hoja del workbook (la que Julián ve al abrir el archivo). Texto plano con:

**A. Cómo llenar el Excel**
- Qué es cada hoja y cuándo llenarla.
- Convención `nombre`: cada block instance tiene un nombre único (ej. `intro`, `kpis_mes`, `hero`). Sirve para cruzar con la sección Layout de la hoja `Reporte`.
- En blocks con sub-items (Kpis, MetricsTables, TopContents, TopCreators, Attribution, Charts) los fields del parent se repiten en cada row del item. Parser agrupa por `nombre`.
- Qué valores acepta cada dropdown (enums).
- Convenciones: fechas (`DD/MM/YYYY`), handles con `@`, boolean como `TRUE`/`FALSE`, decimales con `.`.
- Advertencia: `BrandFollowerSnapshot` no va acá (es brand-level, se carga aparte).

**B. Cómo armar el ZIP para importar**
- Estructura esperada: `reporte.zip` con el `.xlsx` en la raíz + carpeta `images/` con todas las imágenes.
- En las columnas `imagen` (presentes en `TextImage`, `Imagenes`, `TopContents`, `TopCreators`) poner **solo el filename** (ej. `hero.jpg`), no path.
- Filenames case-sensitive. Extensiones aceptadas: `.jpg`, `.jpeg`, `.png`, `.webp`.
- Paso a paso: (1) llenar el Excel, (2) crear carpeta `images/`, (3) pegar las imágenes dentro, (4) seleccionar xlsx + carpeta y "Enviar a → Carpeta comprimida" en Windows / "Comprimir" en Mac, (5) subir el `.zip` resultante en el admin.
- Si no hay imágenes referenciadas, se puede subir solo el `.xlsx` (sin ZIP). El admin acepta ambos.

**C. Regenerar el template**
- `python manage.py dump_report_template` — escribe `reporte-template.xlsx` con este contenido siempre actualizado.
- `python manage.py dump_report_example --report <id>` — exporta un report existente a xlsx para usar como referencia.

**D. Para LLMs / scripts generando el ZIP desde un PDF**

Esta sección está pensada para que alguien le pase a un LLM (Claude, ChatGPT) el PDF del reporte + este xlsx template y le pida que arme el ZIP de importación. Contiene el contrato formal del schema.

- **Contrato por hoja** (lista bullet-style, no prosa):
  - `Reporte` top block — campos exactos, tipos, enums y formatos aceptados (idéntico a lo descripto en la sección 2 de arriba, pero en formato key/type/required/enum estricto).
  - `Reporte` Layout — `orden: int 1-based`, `nombre: str matching [a-z0-9_-]+ max 60`.
  - Una entrada por hoja de block con: nombre de la hoja, columnas exactas en orden, tipos, required, enums, y si admite repetición de `nombre` (hojas denormalizadas) o es unique (TextImage, Imagenes).
- **Constraints globales** (checklist):
  - `nombre` único en todo el archivo (no puede aparecer en dos hojas distintas).
  - Cada `nombre` del Layout debe existir en exactamente una hoja de blocks.
  - En hojas denormalizadas, los `block_*` fields deben ser idénticos en todos los rows con el mismo `nombre` (si varían, el row más frecuente gana con warning, o se rechaza — a definir).
  - `imagen` filenames case-sensitive, extensiones `.jpg|.jpeg|.png|.webp`, deben existir en `images/` del ZIP.
  - ZIP: `.xlsx` en la raíz con nombre cualquiera (único `.xlsx` en la raíz), carpeta `images/` con las imágenes.
- **Ejemplo canónico (few-shot)**: el archivo `reporte-abril-ejemplo.xlsx` generado por `dump_report_example` es la fuente de verdad para dudas de formato. Si una instrucción de esta sección contradice al ejemplo, el ejemplo gana y abrimos un issue.
- **Validación pre-submit**: correr `python manage.py validate_import <zip>` (Etapa 2) para chequear el ZIP sin tocar DB — devuelve la misma lista de `ImporterError(hoja, fila, columna, razón)` que vería el admin. Útil como feedback loop para el LLM.
- **Extracción de imágenes**: no se espera que el LLM extraiga imágenes del PDF. Cuando no las tenga, debe dejar `imagen` vacío en las hojas con imagen opcional, y Julián las sube desde el admin post-import. Para `Imagenes` (donde `imagen` es obligatoria) el LLM debe pedir al usuario que provea las imágenes y listar exactamente qué filenames referenció en la columna.

## Admin integration

### Botones en `/admin/reports/report/` changelist

Dos botones arriba, al lado de `+ Add report`:

- **⬇ Descargar template** → `GET /admin/reports/report/download-template/` → HttpResponse con `Content-Disposition: attachment; filename="reporte-template.xlsx"`.
- **⬆ Importar desde Excel** → `GET /admin/reports/report/import/` → form (Stage autocomplete + file).

Ambas URLs se registran vía `ReportAdmin.get_urls()` y requieren permiso `reports.add_report` (reutiliza las permissions del admin).

### Form de import

```python
class ImportReportForm(forms.Form):
    stage = forms.ModelChoiceField(
        queryset=Stage.objects.select_related("campaign__brand__client"),
        widget=AutocompleteSelect(...),
        label="Etapa destino",
    )
    file = forms.FileField(
        label="Archivo (.zip con Excel + imágenes, o .xlsx solo si no hay thumbnails)",
        validators=[FileExtensionValidator(allowed_extensions=["zip", "xlsx"])],
    )
```

El autocomplete muestra `"{Brand} · {Campaña} · {Etapa}"`. Django admin ya ofrece `autocomplete_fields` — reutilizamos.

### Inlines en `ReportAdmin`

El admin ya tiene los inlines polimórficos para los 8 block types post DEV-116/129/130 (`ReportBlockStackedPolymorphic` + children por subtipo). **No hay que tocar admin inlines en este ticket** — el importer solo crea rows a través de los mismos managers que ya consume el admin. Post-import, Julián cae en el change form del Report y ve todos los blocks populados con sus items en inlines polimórficos existentes.

Lo único que se agrega al admin es:
- `ReportAdmin.get_urls()` con `download-template/`, `download-example/<id>/` e `import/`.
- Botones en changelist + change form para invocarlos.

## Error handling

### Tipos de errores

| Tipo | Ejemplo | Presentación |
|---|---|---|
| Estructural | Hoja `Metricas` faltante | fila única, columna vacía |
| Validación de tipo | `valor = "abc"` en `Metricas` row 3 | `(Metricas, 3, valor, "esperado número")` |
| Enum inválido | `red = "Instagrma"` | `(Metricas, 3, red, "valor 'Instagrma' no es válido. Esperado: Instagram, TikTok, X")` |
| Campo obligatorio vacío | `valor` vacío en `Metricas` row 7 | `(Metricas, 7, valor, "celda vacía — obligatorio")` |
| Constraint condicional | `Creator` sin `handle` | `(Destacados, 2, handle, "obligatorio cuando tipo=Creator")` |
| Constraint DB | `unique_together` en `TopContent` | capturado, mapeado a error estructural |
| Inesperado | Workbook corrupto, bug interno | `logger.exception(...)` + mensaje genérico al usuario |

### Estrategia: acumular, no fail-fast

- El parser recorre las 4 hojas y colecciona **todos** los errores en una `List[ImporterError]` antes de decidir si commitear.
- Si `errors != []` → form se re-renderiza con tabla de errores, **sin tocar DB**.
- Si `errors == []` → entra a `transaction.atomic()` y crea todo. Si una constraint de DB falla (unique, FK rota), rollback + error mapeado.
- Errores inesperados (ej: `openpyxl` lanza `BadZipFile`) → `try/except Exception` en la view con `logger.exception(...)` y mensaje *"Error inesperado procesando el archivo. Avisá a devs."* al usuario.

### Razón

Fail-fast obligaría a Julián a N round-trips para un archivo con N errores. Acumular = ve todo junto, corrige, reintenta una vez.

## Template generation — `dump_report_template` y `dump_report_example`

```bash
$ python manage.py dump_report_template
Template escrito en reporte-template.xlsx (10 hojas)

$ python manage.py dump_report_template --out /tmp/test.xlsx
Template escrito en /tmp/test.xlsx (10 hojas)

$ python manage.py dump_report_example --report <id>
Ejemplo escrito en reporte-<id>-<slug>.xlsx (10 hojas, data del report)

$ python manage.py dump_report_example  # sin --report → usa el report Abril del seed
Ejemplo escrito en reporte-abril-ejemplo.xlsx (10 hojas)
```

- `dump_report_template` invoca `excel_writer.build_template()` — template vacío con headers, dropdowns, hoja `Instrucciones`.
- `dump_report_example` invoca `excel_exporter.export(report)` — template con data poblada de un report existente. Shape idéntico al template vacío.
- Ambos comparten `schema.py` → CLI, admin y exporter generan archivos con exactamente la misma shape.

## Testing strategy (P1, TDD)

### Unit tests — `backend/tests/unit/`

15 tests, cada uno TDD (failing test → minimal impl → passing):

1. `test_excel_parser_happy_path` — fixture válido → `ParsedReport` con 1 report + 5 metrics + 3 destacados + 2 attribution.
2. `test_excel_parser_missing_sheet` — sin hoja `Metricas` → `ImporterError(sheet="Metricas", reason="hoja faltante")`.
3. `test_excel_parser_invalid_enum` — `red=Instagrma` → error con fila.
4. `test_excel_parser_missing_required` — celda `valor` vacía → error.
5. `test_excel_parser_invalid_date` — `fecha_inicio=hoy` → error.
6. `test_excel_parser_accumulates_errors` — Excel con 3 errores distintos → retorna 3, no falla al primero.
7. `test_excel_parser_creator_without_handle` → error.
8. `test_excel_writer_roundtrip` — `build_template()` genera xlsx, lo llenamos programáticamente, lo parseamos → sin errores.
9. `test_import_view_creates_draft` — test client: POST xlsx válido → crea `Report(status=DRAFT)` + nested, redirect a change form.
10. `test_import_view_rollback_on_error` — POST xlsx inválido → DB intacta, form re-renderizado.
11. `test_import_view_permission_denied` — non-staff user → 403.
12. `test_dump_report_template_command` — comando escribe archivo, archivo es parseable.
13. `test_bundle_reader_zip_happy_path` — ZIP válido → `(xlsx_bytes, {filename: image_bytes}, [])` con el dict poblado.
14. `test_bundle_reader_zip_slip_rejected` — entry con `../../etc/passwd` → `ImporterError` estructural, no extrae nada.
15. `test_import_view_image_reference_missing` — ZIP con Excel que referencia `post_X.jpg` inexistente → error `(Destacados, N, imagen, "imagen 'post_X.jpg' no encontrada en images/")`.

### E2E — `frontend/tests/admin-import.spec.ts`

1 smoke:
- Login superuser (credencial nueva en seed_demo).
- Navegar a `/admin/reports/report/`.
- Verificar botones "Descargar template" y "Importar desde Excel".
- Click download → archivo baja con tamaño > 0.
- Click import → form visible.
- Upload fixture válido → redirect a change form, título visible, inline de metrics con ≥ 1 row.
- No errores de consola.

### Fixtures

- `backend/tests/fixtures/reporte_valido.xlsx` — template lleno con data de Marzo (reusa valores del seed), sin referencias a `imagen`.
- `backend/tests/fixtures/reporte_valido.zip` — `reporte_valido.xlsx` con columna `imagen` llena + carpeta `images/` con 3 thumbnails dummy.
- `backend/tests/fixtures/reporte_imagen_faltante.zip` — Excel referencia `post_99.jpg` pero no está en `images/`.
- `backend/tests/fixtures/reporte_invalido_enum.xlsx` — mismo pero con `red=Instagrma` en row 3.
- `backend/tests/fixtures/reporte_faltan_hojas.xlsx` — sin hoja `Metricas`.

Generados por `backend/tests/fixtures/generate_excel_fixtures.py` (script versionado junto a los .xlsx). Se regeneran si openpyxl sube mayor.

### Coverage target

≥ 90% en `apps/reports/importers/`. Los `views.py` y `admin.py` extensions alcanzados por los tests del #9-11.

## Security (P7)

- **Permissions**: las nuevas URLs del admin requieren `reports.add_report` (mismo permiso que el botón "Add report" del admin).
- **Tenant scope**: el autocomplete de Stage usa `autocomplete_fields` de Django, que ya respeta los permissions del `StageAdmin` actual. Un user no-superuser sin perms de `campaigns.view_stage` no puede elegir Stages ajenos al cliente.
- **Input validation**: el parser valida todo antes de tocar DB. Sin raw SQL, sin f-strings en queries.
- **File size cap**: el form limita el upload a 50 MB (un ZIP con ~20 thumbnails comprimidas pesa típicamente 5–15 MB; 50 MB deja margen). Protege contra DOS con archivos grandes.
- **File extension cap**: `FileExtensionValidator(allowed_extensions=["zip", "xlsx"])`.
- **ZIP extraction safety**: usamos `zipfile` stdlib con validación de `ZipInfo.filename` — rechazamos entries con paths absolutos o `..` (zip-slip). Validamos `file_size` de cada entry contra un cap por archivo (10 MB/imagen) antes de extraer.
- **Secrets**: nada nuevo.
- **Dependency health**: `openpyxl==3.1.5` — versión estable, activamente mantenida, sin CVEs conocidos al 2026-04-20. License: MIT.

## Observability (P9, P10)

- **Logging estructurado** en la vista import:
  - `logger.info("report_import_started", extra={"user_id", "stage_id", "filename", "size"})` al empezar.
  - `logger.info("report_import_success", extra={"user_id", "stage_id", "report_id", "metrics_count", "destacados_count", "attribution_count"})` al commitear.
  - `logger.warning("report_import_validation_failed", extra={"user_id", "stage_id", "error_count"})` cuando hay errores de validación.
  - `logger.exception("report_import_unexpected_error", extra={"user_id", "stage_id", "filename"})` en excepciones no manejadas.
- **Health check**: las URLs del admin ya están bajo la vista de health genérica. Sin endpoint nuevo.
- **Fail fast + loud**: no atrapamos `Exception` de forma silenciosa — siempre pasa por `logger.exception` antes de mostrar mensaje genérico.

## DRY (P3)

- `excel_writer.build_template()` es el único generador del template. CLI y admin lo reutilizan.
- `schema.py` centraliza el mapping español ↔ Python. Parser y writer comparten los mismos diccionarios de choice labels.
- `ImporterError` es el único tipo de error de la capa — no hay `raise ValueError("...")` dispersos.

## Boundaries (P6, Minimal Surface Area)

- `excel_parser.parse(bytes: bytes, stage_id: int) -> ParsedReport | List[ImporterError]` — única función exportada del parser.
- `excel_writer.build_template() -> BytesIO` — única función exportada del writer.
- `ImporterError` — única clase exportada de errors.
- El módulo `importers/` expone solo estas 3 funciones/clases vía `__init__.py`.

## Testability (P9)

- Parser y writer son funciones puras sin I/O — `pytest` sin `django_db` marker donde se pueda.
- El admin view inyecta el parser/writer como dependencias (default = los reales, override en tests si hiciera falta).
- Fixtures `.xlsx` versionados = tests reproducibles en cualquier máquina.
- Roundtrip test (writer→parser) asegura que cambiar el schema en un lado rompe el test del otro lado.

## CI/CD y deployment (5-stage Impactia)

1. **PR gate** (`.github/workflows/test.yml`): lint + typecheck + `pytest backend/tests/unit/` + `npm run test:unit`. Ya existe — no cambia con este ticket. Los tests nuevos corren en la misma suite.
2. **Build**: el backend se empaqueta con la nueva dep `openpyxl`. Ya está en `requirements.txt` → `docker compose build` en el deploy lo instala.
3. **Branch→env**: `development` → Hetzner staging (producción del piloto).
4. **Post-deploy smoke** (`.github/workflows/deploy.yml`): sumamos `--grep "Admin import"` al Playwright post-deploy para validar que la vista admin levanta en Hetzner. Usa `PLAYWRIGHT_BASE_URL=${{ secrets.DEPLOY_URL }}`.
5. **Rollback**: documentado en `README.md`. Para rollback, `git revert` + redeploy. Sin migración de DB en este ticket → rollback trivial.

### Secrets

- No se agregan.
- El superuser del admin ya existe (creado en setup).
- Si se necesita uno nuevo para el E2E post-deploy: agregar `DJANGO_SUPERUSER_PASSWORD` a `docs/ENV.md` con owner asignado.

## Git Health & Docs (P8, Hygiene)

- Commits atómicos siguiendo conventional commits: `feat(reports):`, `test(reports):`, `docs(reports):`.
- Archivos nuevos ≤ 300 líneas cada uno (por diseño el parser está dividido por hojas: helper por hoja).
- Actualizar `README.md` con:
  - Nueva sección "Importar reporte desde Excel" con link al template.
  - Comando `dump_report_template` en la tabla de management commands.
- Actualizar `docs/ENV.md` si hay secrets nuevos (no debería).
- Archivar este spec + plan en `docs/superpowers/specs/` y `docs/superpowers/plans/completed/` al cerrar el ticket.

## Frontend Quality

**No aplica** — este ticket es 100% backend (Django admin). Todo el frontend es Django templates del admin, no Next.js. Skip dimensión 11.

## Complexity & Docs

- Ningún archivo generado supera 300 líneas por diseño:
  - `excel_parser.py`: ~200 líneas (un helper por hoja + `parse()`).
  - `excel_writer.py`: ~150 líneas.
  - `schema.py`: ~80 líneas (mappings).
  - `errors.py`: ~30 líneas (dataclass).
- 0 TODOs/FIXMEs se introducen.
- Docstrings en las funciones públicas (parser, writer, command).

## Principios resumidos

- **P1 TDD**: todo test primero.
- **P2 SRP**: 4 archivos, cada uno con una responsabilidad.
- **P3 DRY**: builder único, schema centralizado.
- **P5 DIP**: admin inyecta parser/writer.
- **P6 Minimal Surface**: 3 funciones/clases exportadas.
- **P7 Security**: perms, file validation, size cap, dep health.
- **P9 Fail fast + loud**: todos los errores van por `logger`.
- **P10 Simplicity**: 1 archivo = 1 reporte, sin preview, sin thumbnails en Excel.

## Acceptance criteria (DoD)

**Etapa 1 — Template + ejemplo**:

- [ ] `openpyxl==3.1.5` agregado a `requirements.txt`.
- [ ] `schema.py` con los mappings de choice labels y field names para los 8 block types.
- [ ] `excel_writer.build_template()` genera workbook con 10 hojas (orden fijo), headers, dropdowns y hoja `Instrucciones` formateada.
- [ ] Comando `python manage.py dump_report_template` escribe `reporte-template.xlsx`.
- [ ] `excel_exporter.export(report)` genera workbook con la misma shape que el template, poblado con data de un Report existente.
- [ ] Comando `python manage.py dump_report_example [--report <id>]` escribe el ejemplo.
- [ ] Ejecutando `dump_report_example` sin args sobre DB con seed demo → produce un xlsx con los 11 blocks del report Abril.
- [ ] Unit test roundtrip: `build_template()` → `excel_exporter.export()` → shape diffing → assert hojas y headers coinciden.
- [ ] Review con Julián/Euge del xlsx vacío + ejemplo Abril → sign-off del formato antes de Etapa 2.

**Etapa 2 — Parser + admin + import**:

- [ ] Admin changelist de `Report` tiene botones "Descargar template" e "Importar desde Excel".
- [ ] Change form de `Report` tiene botón "Descargar como Excel" (usa `excel_exporter`).
- [ ] Form de import acepta `.zip` (xlsx + `images/`) y `.xlsx` pelado.
- [ ] Parser valida estructura, dropdowns, cross-reference Layout ↔ hojas de blocks, agrupación por `nombre`, consistencia de fields del parent en rows denormalizadas.
- [ ] Errores se muestran en tabla por `(hoja, fila, columna, razón)`; stacktrace crudo nunca llega al usuario.
- [ ] `transaction.atomic()`: si cualquier cosa falla, rollback completo (DB intacta, imágenes no persistidas).
- [ ] Todas las imágenes del ZIP (4 campos) se persisten vía `ImageField.save()` dentro de la transacción.
- [ ] Post-import redirect a change form con todo populado.
- [ ] Unit tests pasan (`pytest -q`).
- [ ] E2E smoke pasa (`npm run test:e2e:smoke`).
- [ ] `docker compose build && docker compose up -d` en local funciona sin breaking changes.
- [ ] CI verde en PR.

## Risks

| Riesgo | Mitigación |
|---|---|
| Excel corrupto crashea el parser | `try/except` genérico en la view + `logger.exception` |
| Julián llena mal dropdowns | DataValidation en el template + mensajes de error precisos por celda |
| openpyxl cambia API en mayor | Pin exacto `3.1.5`, roundtrip test que detecta regresiones |
| Archivo muy grande → OOM | Cap de 5 MB en el form |
| Conflict: mismo Stage + período + kind importado 2 veces | El modelo no tiene `unique_together` en eso — crea duplicado, Julián lo detecta y borra en admin. Si se vuelve problema, se agrega unique constraint en ticket aparte |

## Image-carrying blocks (inventario)

Post DEV-116 + DEV-129 + DEV-130, el modelo tipado tiene **4 lugares donde se guarda una imagen**, los 4 cubiertos por Fase 1:

| Modelo | Campo | Obligatorio | Hoja Excel |
|---|---|---|---|
| `ImageBlock.image` | `image` | ✅ sí | `Imagenes` |
| `TextImageBlock.image` | `image` | opcional | `TextImage` |
| `TopContentItem.thumbnail` | `thumbnail` | opcional | `TopContents` |
| `TopCreatorItem.thumbnail` | `thumbnail` | opcional | `TopCreators` |

Los 4 resuelven imagen por el mismo mecanismo: celda `imagen` en la hoja correspondiente → filename relativo a `images/` del ZIP.

## Open questions

Ninguna — todas resueltas en la revisión del 2026-04-24 (ZIP bundle, 10 hojas, `nombre` como ID, denormalización de blocks con items, los 4 image-carrying blocks incluidos, staged delivery template-first).
