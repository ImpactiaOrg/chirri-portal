# LLM integration · `apps/llm/` + use case A (PDF parser)

**Linear:** TBD (a crear cuando se restablezca el MCP de Linear)
**Status:** Draft
**Owner:** Daniel Zacharias
**Date:** 2026-04-25

## Contexto

Hoy Chirri Portal no tiene integración con modelos AI. Tres use cases identificados a corto/mediano plazo:

- **A — Parser de PDFs legacy a `ParsedReport`** (inmediato). Extiende DEV-83: el builder/admin/`ParsedReport` ya existen, falta el parser que use vision LLM. Se subió la primera prueba manual con el bundle P10 April 2025; ahora queremos automatizar.
- **B — Generator de reportes desde fuentes externas** (pronto). Recibe un `ReportTemplate` (DEV-118) + un período y va a Metricool/GA4/OneLink/etc. para llenar los blocks automáticamente. Agentic, con tool calling.
- **C — Análisis ad-hoc sobre data interna** (más tarde). Ej: "rankear influencers de esta campaña por performance"; output texto/markdown, no necesariamente structured.

Este ticket implementa **solo A** + el módulo compartido `apps/llm/` que va a sostener B y C cuando lleguen, sin refactor mayor.

## Goals

- Integrar Fireworks AI (Kimi K2 vision) para parsear PDFs legacy y crear Reports DRAFT.
- Dejar la base (`apps/llm/`) lista para B (agentic generation) y C (ad-hoc analysis): cliente OpenAI-compatible, prompts versionados en DB, audit log de calls/cost, jobs async via Celery.
- UX que Julián pueda usar solo: subir PDF → ver progreso → ver reporte creado.
- Auditoría completa: cada call queda persistida con tokens, costo, prompt version, error si lo hubo.

## Non-goals

- No usar `arc-sdk` (decisión del owner, no para este sprint).
- No copiar la arquitectura de Siga (`apps/llm/` con 7 providers, LLMRegistry singleton, hot-swap por DB) — overkill para nuestro scope.
- No multi-provider en MVP — solo Fireworks. La abstracción del cliente queda lo suficientemente fina como para sumar Anthropic/OpenAI directos en el futuro sin reescribir.
- No implementar B ni C en este ticket (se diseñan en sus propios spec/plan).
- No prompt injection defense específico — el admin es staff-only, los inputs son archivos de cliente conocido.
- No hard cap de costo diario org-wide (sí cap por call y por job, ver Failure Handling).
- No alertas externas (Slack/email) en errores — el admin es el dashboard.

## Architecture

### Componentes y boundaries

```
backend/apps/llm/                           # infra compartida, domain-agnostic
  __init__.py
  client.py              — wrapper único OpenAI(base_url=fireworks)
  pricing.py             — dict {model: (input_per_1m, output_per_1m)} en USD
  services.py            — API pública: run_prompt() + dispatch_job()
  handlers.py            — registry de Celery handlers (string → import path)
  models/
    prompt.py            — Prompt + PromptVersion
    call.py              — LLMCall (audit log, 1 row por API call)
    job.py               — LLMJob (1 row por user request, agrupa N calls)
  tasks.py               — Celery: run_llm_job(job_id) resuelve handler y ejecuta
  admin.py               — UI Prompts (editar/versionar) + listado read-only Jobs/Calls
  management/commands/
    seed_prompts.py      — carga inicial de prompts desde apps/llm/seed/*.md a DB
  seed/
    parse_pdf_report.md  — system prompt v1 para use case A
  migrations/

backend/apps/reports/importers/             # consumer del use case A
  pdf_parser.py          — submit_pdf() (admin-facing) + _run_pdf_parse(job) (handler)
                           Reusa builder, errors, parsed.py de DEV-83.

backend/apps/reports/templates/admin/reports/report/
  change_list.html       — sumar botón "🤖 Importar desde PDF (AI)"
  import_pdf.html        — form cascade Cliente→Brand→Campaña→Etapa + FileField .pdf
```

**Reglas de boundary**:

- `apps/llm/` no importa nada de `apps/reports/` ni de `apps/influencers/`. Es infra agnóstica.
- Los consumers (pdf_parser ahora; futuro generator y analyzer) viven en su propio app, importan de `apps/llm/services` y le pasan un `prompt_key` + un dict de inputs.
- Cada consumer registra su handler en `apps/llm/handlers.py` como un string `"apps.reports.importers.pdf_parser._run_pdf_parse"`. La Celery task lo resuelve con `importlib`.

### Data flow (use case A)

```
Julián → /admin/reports/report/
       → click "🤖 Importar desde PDF (AI)"
       → form (Cascade Cliente→Brand→Campaña→Etapa + .pdf)
       → submit_pdf(pdf_bytes, filename, stage_id, user)
            ↓
       crea LLMJob(consumer="reports.pdf_parser", status=PENDING)
            ↓
       encolea Celery task run_llm_job(job_id)
            ↓
       redirect a /admin/llm/llmjob/<id>/  (status page con poll JS cada 2s)

Celery worker:
  run_llm_job(job_id):
    → resuelve handler "_run_pdf_parse" via apps.llm.handlers
    → marca status=RUNNING, started_at=now
    → handler:
        → render PDF a list[bytes] PNG por página (con pdf2image)
        → run_prompt("parse_pdf_report", inputs={"filename": ...},
                     job=job, images=pages_png)
            → resuelve PromptVersion activa
            → renderiza body con inputs (Jinja2)
            → llama Fireworks via client.chat()
            → valida JSON contra prompt.json_schema (Pydantic)
            → persiste LLMCall(job=job, prompt_version, model, tokens, cost, ...)
            → si JSON inválido → 1 retry con mensaje correctivo
            → returns LLMResponse(content, parsed, call)
        → ParsedReport.from_dict(response.parsed)
        → build_report(parsed, images={}, stage_id) → Report(status=DRAFT)
        → job.result = report  (GenericForeignKey)
        → job.output_metadata = {"report_id": ..., "blocks": ...}
        → job.status = SUCCESS, finished_at = now, save
    → si excepción: job.status=FAILED, error_message=str(exc), logger.error
```

## Data model

### `apps/llm/models/prompt.py`

```python
class Prompt(models.Model):
    key = models.SlugField(unique=True, max_length=100)
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    consumer = models.CharField(max_length=100)
    # informativo: "reports.pdf_parser", "reports.generator", "influencers.analyzer"
    active_version = models.ForeignKey(
        "PromptVersion", on_delete=models.PROTECT,
        related_name="active_for", null=True, blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class PromptVersion(models.Model):
    prompt = models.ForeignKey(Prompt, related_name="versions", on_delete=models.CASCADE)
    version = models.PositiveIntegerField()
    body = models.TextField()
    notes = models.CharField(max_length=300, blank=True)
    model_hint = models.CharField(max_length=100, blank=True)
    response_format = models.CharField(
        max_length=20, default="text",
        choices=[("text", "Text"), ("json_object", "JSON Object")],
    )
    json_schema = models.JSONField(null=True, blank=True)
    # Pydantic-compatible JSON Schema. Si está set + response_format=json_object,
    # services.run_prompt valida la respuesta contra esto post-call.
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [("prompt", "version")]
        ordering = ["-version"]

    def save(self, *args, **kwargs):
        if not self.version:
            last = self.prompt.versions.order_by("-version").first()
            self.version = (last.version + 1) if last else 1
        super().save(*args, **kwargs)
```

### `apps/llm/models/job.py`

```python
class LLMJob(models.Model):
    """1 row = 1 user-triggered request. Agrupa N LLMCalls."""
    class Status(models.TextChoices):
        PENDING = "PENDING", "Pendiente"
        RUNNING = "RUNNING", "En curso"
        SUCCESS = "SUCCESS", "Éxito"
        FAILED = "FAILED", "Fallido"

    consumer = models.CharField(max_length=100, db_index=True)
    handler_path = models.CharField(max_length=200)
    # ej. "apps.reports.importers.pdf_parser._run_pdf_parse"
    triggered_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True,
    )
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.PENDING,
        db_index=True,
    )

    input_metadata = models.JSONField(default=dict)
    output_metadata = models.JSONField(default=dict)
    error_message = models.TextField(blank=True)

    # Denormalizado de los LLMCalls (actualizado en LLMCall.save())
    total_input_tokens = models.PositiveIntegerField(default=0)
    total_output_tokens = models.PositiveIntegerField(default=0)
    total_cost_usd = models.DecimalField(max_digits=10, decimal_places=6, default=0)

    # Polymorphic FK al objeto producido (Report, AnalysisRun, etc.)
    result_content_type = models.ForeignKey(
        "contenttypes.ContentType", on_delete=models.SET_NULL, null=True, blank=True,
    )
    result_object_id = models.PositiveIntegerField(null=True, blank=True)
    result = GenericForeignKey("result_content_type", "result_object_id")

    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status", "-created_at"]),
            models.Index(fields=["consumer", "-created_at"]),
        ]
```

### `apps/llm/models/call.py`

```python
class LLMCall(models.Model):
    """1 row = 1 API call a Fireworks. N calls agrupadas en 1 LLMJob."""
    job = models.ForeignKey(
        LLMJob, related_name="calls", on_delete=models.CASCADE,
    )
    prompt_version = models.ForeignKey(PromptVersion, on_delete=models.PROTECT)

    provider = models.CharField(max_length=20, default="fireworks")
    model = models.CharField(max_length=100)

    input_tokens = models.PositiveIntegerField(default=0)
    output_tokens = models.PositiveIntegerField(default=0)
    duration_ms = models.PositiveIntegerField(default=0)
    cost_usd = models.DecimalField(max_digits=10, decimal_places=6, default=0)

    success = models.BooleanField(default=True)
    error_type = models.CharField(max_length=50, blank=True)
    # "json_decode" | "schema_validation" | "rate_limit" | "timeout" |
    # "provider_unavailable" | "payload_too_large" | "cost_exceeded" |
    # "invalid_api_key" | "content_policy" | ...
    error_message = models.TextField(blank=True)

    # Solo se llena en error (decisión: ahorrar storage en path feliz):
    request_payload = models.JSONField(null=True, blank=True)
    response_payload = models.JSONField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["job", "-created_at"]),
            models.Index(fields=["-created_at"]),
            models.Index(fields=["model", "-created_at"]),
        ]

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        # Actualizar denormalizado en LLMJob
        self.job.total_input_tokens = self.job.calls.aggregate(
            Sum("input_tokens"))["input_tokens__sum"] or 0
        self.job.total_output_tokens = self.job.calls.aggregate(
            Sum("output_tokens"))["output_tokens__sum"] or 0
        self.job.total_cost_usd = self.job.calls.aggregate(
            Sum("cost_usd"))["cost_usd__sum"] or 0
        self.job.save(update_fields=[
            "total_input_tokens", "total_output_tokens", "total_cost_usd",
        ])
```

### `apps/llm/pricing.py`

```python
# Precios en USD por 1M tokens. Actualizar manualmente cuando Fireworks cambie.
# Source: https://fireworks.ai/pricing (cacheado 2026-04-25)
MODEL_PRICING = {
    "accounts/fireworks/models/kimi-k2-instruct-0905": {
        "input_per_1m": Decimal("0.6"),
        "output_per_1m": Decimal("2.5"),
    },
    "accounts/fireworks/models/kimi-k2p5": {
        "input_per_1m": Decimal("0.6"),
        "output_per_1m": Decimal("2.5"),
    },
    # Sumar más modelos cuando se usen.
}

DEFAULT_PRICING = {"input_per_1m": Decimal("0"), "output_per_1m": Decimal("0")}

def calculate_cost(model: str, input_tokens: int, output_tokens: int) -> Decimal:
    p = MODEL_PRICING.get(model, DEFAULT_PRICING)
    return (
        (Decimal(input_tokens) / Decimal(1_000_000)) * p["input_per_1m"]
        + (Decimal(output_tokens) / Decimal(1_000_000)) * p["output_per_1m"]
    ).quantize(Decimal("0.000001"))
```

## Python API

`apps/llm/services.py` expone exactamente 2 funciones públicas:

```python
@dataclass
class LLMResponse:
    content: str               # texto crudo
    parsed: dict | None        # si hubo json_schema, ya validado
    call: LLMCall              # row guardada


def run_prompt(
    prompt_key: str,
    inputs: dict,
    *,
    job: LLMJob | None = None,
    images: list[bytes] | None = None,
    model_override: str | None = None,
    max_retries: int = 1,
) -> LLMResponse:
    """
    1. Resuelve Prompt(key=prompt_key).active_version.
    2. Renderiza prompt.body con `inputs` (Jinja2).
    3. Llama Fireworks via apps.llm.client (chat completion).
       - response_format según prompt_version.response_format.
       - images se pasan como image_url[base64] en messages.
    4. Si response_format=json_object y prompt.json_schema set:
       valida con jsonschema.validate(); si falla y retries > 0,
       retry con mensaje correctivo. Si después de retries falla,
       LLMCall.error_type="schema_validation", raise LLMValidationError.
    5. Persiste LLMCall(job, prompt_version, model, tokens, cost,
       success, error_type, error_message).
    6. Si payload > LLM_MAX_TOKENS_PER_CALL → bloquea ANTES del call,
       LLMCall.error_type="payload_too_large".
    7. Si job.total_cost_usd + cost_estimate > LLM_MAX_COST_PER_JOB_USD →
       bloquea, LLMCall.error_type="cost_exceeded".
    """


def dispatch_job(
    consumer: str,
    handler_path: str,
    input_metadata: dict,
    triggered_by: User | None = None,
) -> LLMJob:
    """
    1. Crea LLMJob(consumer, handler_path, input_metadata, status=PENDING).
    2. Encolea Celery task run_llm_job.delay(job.pk).
    3. Retorna el job (caller redirige a /admin/llm/llmjob/<id>/).
    """
```

`apps/llm/tasks.py`:

```python
@shared_task(bind=True, max_retries=0)  # retries los maneja services.run_prompt
def run_llm_job(self, job_id: int):
    job = LLMJob.objects.get(pk=job_id)
    job.status = LLMJob.Status.RUNNING
    job.started_at = timezone.now()
    job.save()
    try:
        handler = import_string(job.handler_path)
        handler(job)  # handler actualiza output_metadata, result, etc.
        job.status = LLMJob.Status.SUCCESS
    except Exception as exc:
        logger.exception("llm.job_failed", extra={
            "job_id": job_id, "consumer": job.consumer,
        })
        job.status = LLMJob.Status.FAILED
        job.error_message = str(exc)
    finally:
        job.finished_at = timezone.now()
        job.save()
```

## Consumer del use case A · `apps/reports/importers/pdf_parser.py`

```python
from apps.llm.services import dispatch_job, run_prompt
from .builder import build_report
from .parsed import ParsedReport

CONSUMER = "reports.pdf_parser"
HANDLER = "apps.reports.importers.pdf_parser._run_pdf_parse"


def submit_pdf(pdf_bytes: bytes, filename: str, stage_id: int, user) -> LLMJob:
    """Llamado desde admin view. Guarda PDF, crea Job, redirige."""
    pdf_path = _save_to_media(pdf_bytes, filename)
    return dispatch_job(
        consumer=CONSUMER,
        handler_path=HANDLER,
        input_metadata={
            "pdf_path": pdf_path,
            "stage_id": stage_id,
            "filename": filename,
            "size_bytes": len(pdf_bytes),
        },
        triggered_by=user,
    )


def _run_pdf_parse(job: LLMJob) -> None:
    """Corre dentro de Celery worker."""
    pdf_path = job.input_metadata["pdf_path"]
    stage_id = job.input_metadata["stage_id"]
    filename = job.input_metadata["filename"]

    # 1. Render PDF → list[bytes PNG] (pdf2image, requires poppler).
    pages_png = _render_pdf_to_pngs(pdf_path)
    if not pages_png:
        raise ValueError("PDF inválido o vacío — 0 páginas renderizadas.")

    # 2. Llamada al LLM con vision.
    response = run_prompt(
        prompt_key="parse_pdf_report",
        inputs={"filename": filename},
        job=job,
        images=pages_png,
    )

    # 3. Validar y materializar.
    parsed = ParsedReport.from_dict(response.parsed)
    report = build_report(parsed, images={}, stage_id=stage_id)
    # (sin imágenes en bundle — el PDF parser de Fase 1 no extrae imágenes
    # del PDF aún; se agregan manualmente en admin si hace falta.)

    # 4. Linkear y completar job.
    job.result = report
    job.output_metadata = {
        "report_id": report.pk,
        "blocks": report.blocks.count(),
        "title": report.title,
    }
    job.save()
```

Dependencia nueva: `pdf2image` (requiere `poppler-utils` instalado en el container; agregamos al Dockerfile).

## Admin UX

### Trigger del PDF parser (en `apps/reports/admin.py`)

Sumar tercer botón a `/admin/reports/report/` changelist:

- **🤖 Importar desde PDF (AI)** → `/admin/reports/report/import-pdf/`

Form: cascade Cliente→Brand→Campaña→Etapa (reusa el JS del importer xlsx) + `FileField` (`.pdf` only, cap 50 MB). Submit → llama `pdf_parser.submit_pdf()` → redirect a `/admin/llm/llmjob/<id>/`.

### Status page del job (custom view en `apps/llm/admin.py`)

Override `change_view` de `LLMJobAdmin` para renderizar template custom con poll JS cada 2s. Vista:

- Header: status badge (PENDING/RUNNING/SUCCESS/FAILED), elapsed time, triggered_by, consumer.
- Input metadata (ej. filename, stage info).
- Tabla de LLMCalls (uno por fila): model, success, tokens, duration, cost, error_type si aplica.
- Footer: total tokens, total cost.
- Si SUCCESS: botón "Ver resultado →" usando `result` GFK.
- Si FAILED: error_message + botón "Reintentar" que crea nuevo Job con mismo input_metadata.

### Edición de prompts (`/admin/llm/prompt/`)

- **List**: `key`, `name`, `consumer`, `active_version.version`, `active_version.created_by`, `active_version.created_at`. Filtros por consumer.
- **Detail**: form name/description (editable) + tabla read-only de PromptVersions (versión, autor, fecha, notes, [Set active], [View], [Diff vs activa]).
- **Botón "Nueva versión"**: form con textarea body (prefilled con activa), notes, model_hint, response_format, json_schema (`JSONField` widget). Submit crea nueva versión (NO la activa automáticamente — explicit "Set active" en otro paso).
- **Diff view**: side-by-side con `difflib.HtmlDiff` (stdlib).

### Audit (read-only, para devs)

- **`/admin/llm/llmjob/`**: list con filtros status/consumer/triggered_by. Detail = la status page de arriba.
- **`/admin/llm/llmcall/`**: list con filtros model/success/error_type. Detail muestra payload completo si hubo error.
- Permission `llm.view_llmcall` solo para superuser (puede contener PII).

### Permisos custom

- `llm.view_costs` (custom permission, opt-in): controla si `total_cost_usd` y `LLMCall.cost_usd` son visibles. Default solo superuser. Julián ve estado pero no necesariamente costos.

## Failure handling

### Tres buckets de error con estrategia diferente

| Bucket | Errores | Retry |
|---|---|---|
| **Transient** | HTTP 5xx, 429 (rate limit), network timeout | 2 retries con exp. backoff. 429 respeta `Retry-After`. |
| **Output inválido** | JSON parse error, schema validation error | 1 retry con mensaje correctivo (ej. "Tu respuesta anterior no fue JSON válido. Devolvé exactamente un objeto JSON sin texto adicional."). |
| **Permanent** | HTTP 401/403 (key inválida), HTTP 400 (bug en código), content policy violation, PDF unreadable | NO retry. FAILED inmediatamente. |

Domain validation errors (ej. `nombre` referenciado en Layout no existe en blocks) → NO retry, FAILED. Es error de la lógica del LLM, no del formato.

### Cost guardrails (configurable via Django settings)

- `LLM_MAX_TOKENS_PER_CALL = 500_000` — bloquea calls oversize antes de enviar.
- `LLM_MAX_COST_PER_JOB_USD = Decimal("2.00")` — bloquea calls que llevarían el job sobre el cap.

Defienden contra runaway cost. No hay cap diario org-wide en MVP.

### Timeouts del job entero

- Celery beat task `mark_stuck_jobs_as_failed` corre cada minuto, marca como FAILED jobs RUNNING > 10 min con `error_type="timeout"`.
- En la status page del admin, mensaje "Esto está tardando más de lo esperado..." cuando RUNNING > 60s.

### Logging

- `logger.error("llm.job_failed", extra={...})` en cada FAILED.
- `logger.info("llm.call_success", extra={...})` en cada call exitoso.
- Sin alertas externas (Slack/email) en MVP.

## Testing strategy (3 capas)

### Capa 1 · Unit tests con mocks (target ≥90% coverage)

`@patch('apps.llm.client.OpenAI')` para mockear el SDK. Fixtures de respuesta canned en `backend/tests/fixtures/llm_responses/*.json`.

Cobertura mínima:

```
apps/llm/client tests:
- test_client_retries_on_5xx
- test_client_retries_on_429_respects_retry_after
- test_client_no_retry_on_400
- test_json_parse_error_triggers_correction_retry
- test_schema_validation_error_triggers_correction_retry
- test_cost_calculated_from_token_usage_and_pricing_table
- test_call_payload_persisted_only_on_failure

apps/llm/models/ tests:
- test_prompt_version_autoincrements_per_prompt
- test_set_active_updates_prompt_pointer
- test_save_prompt_version_does_not_auto_activate
- test_llmjob_total_cost_denormalized_from_calls
- test_diff_renders_via_difflib

apps/llm/services/ tests:
- test_run_prompt_resolves_active_version
- test_run_prompt_renders_inputs_into_body  (Jinja2)
- test_run_prompt_validates_against_json_schema
- test_run_prompt_associates_call_to_job
- test_run_prompt_supports_images_for_vision_models
- test_dispatch_job_creates_pending_and_queues_task
- test_run_llm_job_resolves_handler_via_importlib
- test_run_llm_job_marks_failed_on_handler_exception
- test_cost_cap_per_call_blocks_oversize_payload
- test_cost_cap_per_job_blocks_when_exceeded
```

### Capa 2 · Consumer integration (use case A)

```
apps/reports/importers/pdf_parser tests:
- test_submit_pdf_creates_job_and_queues_task
- test_handler_renders_pdf_pages_to_pngs
- test_handler_calls_run_prompt_with_pages_as_images
- test_handler_builds_report_with_parsed_output
- test_handler_marks_job_success_with_report_id_and_blocks_count
- test_handler_failure_rollback_keeps_db_clean
- test_handler_failure_persists_error_to_job
```

Fixtures:
- `backend/tests/fixtures/sample.pdf` — 2-3 páginas, contenido conocido.
- `backend/tests/fixtures/llm_responses/parsed_report_minimal.json` — ParsedReport JSON canned.

### Capa 3 · E2E Playwright (1 smoke)

`frontend/tests/admin-import-pdf.spec.ts`:

- Login → `/admin/reports/report/`.
- Click "Importar desde PDF (AI)".
- Cascade Cliente → Brand → Campaña → Etapa.
- Subir `sample.pdf`.
- Verificar redirect a `/admin/llm/llmjob/<id>/`.
- Mockear Fireworks via `page.route('https://api.fireworks.ai/**', ...)` con respuesta canned.
- Esperar status SUCCESS (poll detecta en ≤5s con la respuesta inmediata).
- Click "Ver resultado →" → verificar Report existe con título esperado.

### Lo que NO testeamos

- No hay live test contra Fireworks real (alineado con cómo no lo hace Siga). Si la API rompe contrato, lo veremos por errores en `LLMCall.error_type` y reaccionamos.
- No testeamos calidad de outputs del LLM — eso es trabajo manual de eyeballing prompts. La automatización empieza si establecemos un eval set.

## Security (P7)

- **API key**: env var `FIREWORKS_API_KEY` solamente. Carga al boot via `settings.LLM_FIREWORKS_API_KEY`. Nunca en DB. En Hetzner queda en el secret manager cuando exista deploy.
- **Permissions**: 
  - `llm.add_prompt`, `llm.change_prompt`: staff (Euge/devs editan prompts).
  - `llm.view_llmjob`: staff con el permiso de su consumer (ej. `reports.add_report` para ver jobs del PDF parser).
  - `llm.view_llmcall`: solo superuser (PII risk en payloads).
  - `llm.view_costs` (custom): solo superuser por default.
- **Tenant scope**: el job's `result` (Report creado) hereda del Stage elegido por Julián, que ya pasa por permisos de Stage existentes. Sin nuevos paths de leak.
- **Input validation**: `FileExtensionValidator(['pdf'])` + cap 50MB en el form.
- **Cost guardrails** (también es seguridad financiera): `LLM_MAX_TOKENS_PER_CALL`, `LLM_MAX_COST_PER_JOB_USD`.
- **Logging**: nunca loggear `request_payload`/`response_payload` por stdout — solo persistir en DB y solo en errores.
- **Dependency health**: `openai==1.x` (ya tenemos para el cliente OpenAI-compatible), `pdf2image==1.x`, `Pillow` (ya está), `jsonschema==4.x`, `Jinja2` (ya está como dep de Django). Sin CVEs conocidos al 2026-04-25.

## Observability (P9, P10)

- `logger.info("llm.call_success", extra={"call_id", "model", "input_tokens", "output_tokens", "cost_usd", "duration_ms"})` por cada call OK.
- `logger.warning("llm.call_retry", extra={"call_id", "error_type", "attempt"})` por retry.
- `logger.error("llm.call_failed", extra={"call_id", "error_type", "error_message"})` por call FAILED.
- `logger.error("llm.job_failed", extra={"job_id", "consumer", "error_type", "error_message"})` por job FAILED.
- Metric implícito: `LLMCall` table es el dashboard de uso/costo. Admin tiene una list view con totales por día (group by `DATE(created_at)`, sum cost_usd).

## DRY (P3)

- `apps.llm.client` es el único punto que llama al SDK de OpenAI/Fireworks.
- `apps.llm.pricing.calculate_cost` es la única función que conoce precios.
- `apps.llm.services.run_prompt` es la única forma de llamar al LLM (consumers nunca tocan client directo).
- Cascade Cliente→Brand→Campaña→Etapa del form de PDF reusa el componente JS del importer xlsx.

## Boundaries (P6, Minimal Surface Area)

`apps/llm/__init__.py` exporta solo:
- `services.run_prompt`
- `services.dispatch_job`
- `services.LLMResponse`
- `models.Prompt`, `models.PromptVersion`, `models.LLMJob`, `models.LLMCall`

Todo lo demás es interno (`client`, `pricing`, `tasks`, `handlers`).

## Testability (P9)

- `client` es función pura sobre `OpenAI` SDK — mockeable con `@patch`.
- `services` solo orquesta — todos los I/O son via `client` y `models`, mockeables.
- `dispatch_job` retorna el `LLMJob` antes de encolar — los tests pueden invocar la task directo (`run_llm_job(job.pk)` síncronamente con `CELERY_TASK_ALWAYS_EAGER=True`).
- Fixtures versionadas en `backend/tests/fixtures/llm_responses/` aseguran tests deterministas.

## CI/CD y deployment

1. **PR gate** (`test.yml`): los tests nuevos corren en la suite existente. Coverage check bloqueante para `apps/llm/`.
2. **Build**: el backend agrega `pdf2image`, `jsonschema` a `requirements.txt`, y `poppler-utils` al Dockerfile (`apt-get install poppler-utils`). `docker compose build` lo recoge.
3. **Migrations**: 1 migración nueva con los 3 modelos (`Prompt`, `PromptVersion`, `LLMJob`, `LLMCall`).
4. **Seed**: `python manage.py seed_prompts` se corre post-deploy (idempotente, agrega prompts faltantes sin tocar los existentes).
5. **Env**: agregar `FIREWORKS_API_KEY` a `docs/ENV.md` y `.env.example`. Sin la key, los tests pasan (mockeados) pero el feature no funciona en runtime.
6. **Rollback**: `git revert` + redeploy. Las migraciones son aditivas (sin `RemoveField`), rollback no destruye data.

## Git Health & Docs (P8)

- Commits atómicos: `feat(llm):`, `feat(reports):`, `test(llm):`, `docs(llm):`.
- Archivos nuevos ≤ 300 líneas:
  - `client.py` ~150 líneas.
  - `services.py` ~200 líneas.
  - `tasks.py` ~50 líneas.
  - `models/{prompt,job,call}.py` ~80 líneas cada uno.
  - `pdf_parser.py` ~150 líneas.
- Actualizar `README.md` con sección "AI integration": cómo correr `seed_prompts`, dónde editar prompts, cómo trigger el PDF parser.
- Actualizar `docs/ENV.md` con `FIREWORKS_API_KEY`.

## Acceptance criteria (DoD)

- [ ] `apps/llm/` con los 4 módulos (`client`, `services`, `tasks`, `pricing`) y 3 modelos (`Prompt`, `LLMJob`, `LLMCall`).
- [ ] Migración aplicable sin errores; rollback testeable (`migrate llm zero`).
- [ ] `seed_prompts` carga la versión 1 de `parse_pdf_report` desde `apps/llm/seed/parse_pdf_report.md` a DB. Idempotente.
- [ ] `dump_report_template` y `dump_report_example` siguen funcionando (no rompemos nada de DEV-83).
- [ ] Botón "🤖 Importar desde PDF (AI)" en `/admin/reports/report/` changelist.
- [ ] Form con cascade + FileField `.pdf` valida extensión y tamaño.
- [ ] Submit crea `LLMJob`, encolea Celery task, redirige a `/admin/llm/llmjob/<id>/`.
- [ ] Status page con poll JS cada 2s muestra status, calls, cost. Cuando SUCCESS aparece "Ver reporte →".
- [ ] Reintentar (FAILED) crea nuevo Job con mismo input_metadata.
- [ ] Edit prompt en admin crea PromptVersion nueva (auto-incremento), no activa automáticamente. "Set active" actualiza el pointer.
- [ ] Diff view side-by-side entre dos versiones de un prompt.
- [ ] Cap por call y por job bloquean antes de enviar al LLM.
- [ ] LLMCall stores payload solo en errores.
- [ ] Permission `llm.view_costs` controla visibilidad de cost en admin.
- [ ] `logger.exception` en cada error inesperado; el usuario nunca ve stacktrace crudo.
- [ ] Unit tests pasan (≥90% coverage en `apps/llm/`).
- [ ] Consumer tests pasan (`apps/reports/importers/pdf_parser`).
- [ ] E2E smoke pasa con Fireworks mockeado via `page.route()`.
- [ ] CI verde en PR.
- [ ] `docker compose build && docker compose up -d` funciona local con `poppler-utils` agregado.

## Risks

| Riesgo | Mitigación |
|---|---|
| Costo runaway por bug en código (loop infinito de calls) | `LLM_MAX_COST_PER_JOB_USD` bloquea, audit log permite ver el patrón rápido |
| Fireworks cambia contrato de API silenciosamente | `LLMCall.error_type="schema_validation"` aumenta su tasa, monitoring en admin lo detecta |
| Prompt nuevo (vN) rompe outputs en prod | rollback es 1 click ("Set active" sobre vN-1). Cada `LLMCall.prompt_version_id` muestra qué versión causó qué tasa de error |
| PDF muy grande (100 páginas) cuesta $50 en un call | `LLM_MAX_TOKENS_PER_CALL` bloquea antes; mensaje claro al usuario |
| Celery worker se queda colgado mid-call | beat task `mark_stuck_jobs_as_failed` cada 60s, cap 10min |
| API key leak por logs | request/response solo persistidos en DB (no stdout) y solo en errores; admin LLMCall solo superuser |
| Concurrencia de prompt edits (dos admins guardan a la vez) | sin conflicto: cada save crea row separada (PromptVersion); "set active" es explícito |
| `pdf2image` requiere `poppler-utils` system-level | documentado en Dockerfile + README; build falla loud si falta |
| LLM alucina ParsedReport con `nombre` que no matchea Layout | domain validation en `excel_parser` (reusable) detecta y FAILED el job con mensaje claro |
| LLM referencia imágenes que no podemos fulfillar (Fase 1 no extrae imágenes del PDF) | Prompt explícitamente instruye al LLM a dejar todos los campos `imagen` vacíos. Builder acepta `images={}` ya hoy. Imágenes se agregan manualmente en admin post-import |

## Open questions

Ninguna — todas resueltas en el brainstorming del 2026-04-25.

## Future work (no en este ticket)

- **Use case B** (generator desde Metricool/GA4): nuevo ticket. Reusa `apps/llm/`. Suma `apps/reports/generators/` con fetchers + planner agentic + per-block generators. Probable: function calling de Fireworks, multi-call por job.
- **Use case C** (análisis ad-hoc): nuevo ticket. Reusa `apps/llm/`. Vive en el app de dominio (`apps/influencers/analyzers/`).
- **Eval set + automated quality regression**: cuando tengamos N reportes parseados, podemos armar un "golden set" y correr el prompt contra ellos en CI para detectar regressions de calidad.
- **Live contract test**: si Fireworks rompe contrato y nos morde, agregamos un `@pytest.mark.live` test nightly.
- **Hot-swap de provider via admin**: si llega el día que rotamos providers seguido o queremos A/B testing entre Fireworks/Anthropic/etc., migramos a modelo `LLMSettings` estilo Siga (con cifrado Fernet, no plain text).
- **Cost dashboard frontend** (Next.js): si los costos se vuelven significativos, mover el dashboard del admin a una vista Next.js con charts.
- **Prompt eval UI**: vista en admin que corre un prompt sobre un input fijo y muestra outputs lado a lado de las últimas N versiones — útil para iterar prompts sin trigger jobs reales.
