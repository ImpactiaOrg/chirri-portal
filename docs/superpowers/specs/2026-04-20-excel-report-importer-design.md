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
- Import de thumbnails desde el Excel (se suben después desde los inlines del admin).

## Architecture

### Componentes

Todos dentro de `apps/reports/`:

```
apps/reports/importers/
  __init__.py
  excel_parser.py      — pure function: bytes → (ParsedReport, List[ImporterError])
  excel_writer.py      — pure function: () → BytesIO (template vacío)
  errors.py            — ImporterError(sheet, row, column, reason)
  schema.py            — mapping español → Python field names, enums, validaciones

apps/reports/admin.py  (extendido) — vista custom `import/`, botón en changelist,
                                     TopContentInline, OneLinkAttributionInline
apps/reports/management/commands/
  dump_report_template.py          — CLI wrapper de excel_writer.build_template()
```

**Principios de separación (P2 SRP, P5 DIP):**

- `excel_parser` no importa nada de Django ni de modelos — trabaja con dicts y dataclasses. Facilita test unitario puro.
- `excel_writer` genera un workbook sin tocar DB ni filesystem — retorna `BytesIO`, el caller decide dónde escribirlo.
- `errors.py` es la única clase de error estructurada — el admin serializa `List[ImporterError]` para renderizar la tabla.
- `schema.py` centraliza el mapping español↔Python para que no haya strings mágicos dispersos.
- El admin es un **thin wrapper**: recibe el upload, llama al parser, si hay errores los muestra, si no, crea rows en `transaction.atomic()` y redirige.

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

## Excel template

### Hojas (en este orden)

| Hoja | Shape | Modelo mapeado |
|---|---|---|
| `Reporte` | key-value (2 col) | `Report` (fields escalares) |
| `Metricas` | tabular | `ReportMetric` (1:N) |
| `Destacados` | tabular | `TopContent` (1:N) |
| `InfluencerAttribution` | tabular | `OneLinkAttribution` (1:N) |
| `_LEEME` | texto plano | instrucciones de llenado |

Las hojas se buscan por nombre (orden no importa). Hoja faltante = error estructural único.

### Hoja `Reporte` (key-value)

| Campo | Tipo | Obligatorio | Valor ejemplo |
|---|---|---|---|
| tipo | enum | sí | `Mensual` |
| fecha_inicio | fecha | sí | `01/03/2026` |
| fecha_fin | fecha | sí | `31/03/2026` |
| titulo | texto | no | `Reporte general · Marzo` |
| intro | texto | no | `Marzo fue el mes…` |
| conclusiones | texto | no | `El carrusel de los 5 errores…` |

- `tipo` dropdown: `Influencer / General / Quincenal / Mensual / Cierre de etapa`.
- Fechas: aceptamos `DD/MM/YYYY`, `DD-MM-YYYY`, ISO `YYYY-MM-DD`. Normalizamos a `date`.
- `titulo` vacío = se usa `display_title` auto-generado del modelo.

### Hoja `Metricas` (tabular)

| red | origen | metrica | valor | comparacion |
|---|---|---|---|---|
| Instagram | Orgánico | reach | 284000 | 6.1 |
| Instagram | Pauta | reach | 512000 | |
| TikTok | Influencer | engagement_rate | 4.8 | 0.3 |

- Dropdown `red`: `Instagram / TikTok / X`.
- Dropdown `origen`: `Orgánico / Influencer / Pauta`.
- `metrica`: texto libre. Convención: snake_case. Ejemplos comunes: `reach`, `impressions`, `engagement_rate`, `followers_gained`.
- `valor`: número (decimal). Obligatorio.
- `comparacion`: delta % vs período anterior. Opcional.

### Hoja `Destacados` (tabular)

| tipo | red | origen | ranking | handle | caption | url_post | metricas_json |
|---|---|---|---|---|---|---|---|
| Post | Instagram | Orgánico | 1 | | Contenido destacado #1 | https://... | `{"likes":500,"reach":10000}` |
| Creator | Instagram | Influencer | 1 | @sofi.gonet | | https://... | `{}` |

- Dropdown `tipo`: `Post / Creator`.
- `handle` obligatorio si `tipo = Creator`.
- `metricas_json`: JSON plano. Vacío = `{}`. Usado por el render del carrusel en el portal.
- `ranking` es 1-based. Se usa para ordenar dentro de `(tipo, red)`.
- Thumbnails **no** van acá — se suben después desde el inline de Destacados en el admin.

### Hoja `InfluencerAttribution` (tabular)

| handle | clicks | descargas_app |
|---|---|---|
| @sofi.gonet | 1200 | 180 |

Mapea 1:1 a `OneLinkAttribution`. Solo aplica a marcas con app mobile. Para marcas sin app, se deja vacía.

### Hoja `_LEEME`

Texto plano con:

- Qué es cada hoja y cuándo llenarla.
- Qué valores acepta cada dropdown.
- Convenciones: fechas, handles con `@`, JSON.
- Cómo regenerar el template: `python manage.py dump_report_template`.
- Advertencia: thumbnails y `BrandFollowerSnapshot` no van en el Excel.

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
        label="Archivo Excel (.xlsx)",
        validators=[FileExtensionValidator(allowed_extensions=["xlsx"])],
    )
```

El autocomplete muestra `"{Brand} · {Campaña} · {Etapa}"`. Django admin ya ofrece `autocomplete_fields` — reutilizamos.

### Inlines en `ReportAdmin` (nuevos)

```python
class TopContentInline(admin.TabularInline):
    model = TopContent
    extra = 0
    fields = ("kind", "network", "source_type", "rank", "handle", "caption", "post_url", "thumbnail", "metrics")

class OneLinkAttributionInline(admin.TabularInline):
    model = OneLinkAttribution
    extra = 0
    fields = ("influencer_handle", "clicks", "app_downloads")

class ReportAdmin(admin.ModelAdmin):
    inlines = [ReportMetricInline, TopContentInline, OneLinkAttributionInline]  # ya existía ReportMetricInline
```

Post-import, Julián cae en el change form y ve las 3 tablas inline, con file picker de thumbnail en cada row de Destacados.

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

## Template generation — `dump_report_template`

```bash
$ python manage.py dump_report_template
Template escrito en reporte-template.xlsx (5 hojas)

$ python manage.py dump_report_template --out /tmp/test.xlsx
Template escrito en /tmp/test.xlsx (5 hojas)
```

El command invoca `excel_writer.build_template()` — la misma función que usa la vista admin. Garantiza que CLI y admin generan exactamente el mismo archivo.

## Testing strategy (P1, TDD)

### Unit tests — `backend/tests/unit/`

12 tests, cada uno TDD (failing test → minimal impl → passing):

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

- `backend/tests/fixtures/reporte_valido.xlsx` — template lleno con data de Marzo (reusa valores del seed).
- `backend/tests/fixtures/reporte_invalido_enum.xlsx` — mismo pero con `red=Instagrma` en row 3.
- `backend/tests/fixtures/reporte_faltan_hojas.xlsx` — sin hoja `Metricas`.

Generados por `backend/tests/fixtures/generate_excel_fixtures.py` (script versionado junto a los .xlsx). Se regeneran si openpyxl sube mayor.

### Coverage target

≥ 90% en `apps/reports/importers/`. Los `views.py` y `admin.py` extensions alcanzados por los tests del #9-11.

## Security (P7)

- **Permissions**: las nuevas URLs del admin requieren `reports.add_report` (mismo permiso que el botón "Add report" del admin).
- **Tenant scope**: el autocomplete de Stage usa `autocomplete_fields` de Django, que ya respeta los permissions del `StageAdmin` actual. Un user no-superuser sin perms de `campaigns.view_stage` no puede elegir Stages ajenos al cliente.
- **Input validation**: el parser valida todo antes de tocar DB. Sin raw SQL, sin f-strings en queries.
- **File size cap**: el form limita el upload a 5 MB (un template lleno pesa < 100 KB — 5 MB deja margen). Protege contra DOS con archivos grandes.
- **File extension cap**: `FileExtensionValidator(allowed_extensions=["xlsx"])`.
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

- [ ] Template `.xlsx` documentado en `backend/tests/fixtures/reporte_valido.xlsx` + entrada en README.
- [ ] Comando `python manage.py dump_report_template` genera el Excel vacío con 5 hojas, dropdowns, y hoja `_LEEME`.
- [ ] Admin changelist de `Report` tiene botones "Descargar template" e "Importar desde Excel".
- [ ] `ReportAdmin` tiene los 3 inlines (Metric + TopContent + OneLinkAttribution).
- [ ] Form de import valida Excel, muestra errores claros en tabla por (hoja, fila, columna, razón).
- [ ] Stacktrace crudo **nunca** llega al usuario — siempre pasa por `logger.exception` + mensaje genérico.
- [ ] Transacción atómica: si cualquier cosa falla, rollback completo.
- [ ] Post-import redirect a change form con todo populado.
- [ ] 12 unit tests en `backend/tests/unit/` pasan (`pytest -q`).
- [ ] 1 E2E test en `frontend/tests/admin-import.spec.ts` pasa (`npm run test:e2e:smoke`).
- [ ] `openpyxl==3.1.5` agregado a `requirements.txt`.
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

## Open questions

Ninguna.
