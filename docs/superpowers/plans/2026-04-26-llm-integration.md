# LLM Integration (DEV-84) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build `apps/llm/` (provider-agnostic LLM infra: prompts in DB, audit log of calls/cost, async jobs via Celery) and ship use case A — a Django admin PDF importer that calls Fireworks Kimi K2 vision and creates a `Report` DRAFT.

**Architecture:** New Django app `apps/llm/` exposes a 2-function API (`run_prompt`, `dispatch_job`) on top of an OpenAI-compatible HTTP client with a `PROVIDERS` registry. Consumers (starting with `apps/reports/importers/pdf_parser.py`) register a Celery handler, persist their own domain object, and link it via `LLMJob.result` (GenericForeignKey). Admin UX: Julián clicks "🤖 Importar desde PDF (AI)" → dispatch → status-page polls every 2s → "Ver reporte →".

**Tech Stack:** Django 5 · Celery 5 · openai 1.x SDK (Fireworks via `base_url`) · pdf2image + poppler-utils · jsonschema · Jinja2 · pytest · Playwright. Existing project conventions preserved (admin cascade JS, polymorphic blocks, ContentFile uploads, `image_bytes={}` for now).

**Spec:** `docs/superpowers/specs/2026-04-25-llm-integration-design.md` — read it before starting, especially "Architecture" and "Failure handling".

---

## File Structure

### New (created in this plan)

```
backend/apps/llm/
  __init__.py                       # exports public surface (services + models)
  apps.py                           # AppConfig
  client.py                         # PROVIDERS registry + get_client + chat()
  pricing.py                        # MODEL_PRICING + calculate_cost + get_provider
  services.py                       # run_prompt + dispatch_job + LLMResponse
  handlers.py                       # registry of consumer handler paths (informational)
  tasks.py                          # Celery: run_llm_job + mark_stuck_jobs_as_failed
  exceptions.py                     # LLMConfigError, LLMValidationError, LLMCostExceededError
  admin.py                          # Prompt/Version CRUD, Job/Call read-only, status page
  models/
    __init__.py
    prompt.py                       # Prompt + PromptVersion
    job.py                          # LLMJob
    call.py                         # LLMCall
  migrations/
    __init__.py
    0001_initial.py                 # produced by makemigrations
  management/
    __init__.py
    commands/
      __init__.py
      seed_prompts.py               # idempotent loader from seed/*.md
  seed/
    parse_pdf_report.md             # system prompt v1 for use case A
  templates/admin/llm/llmjob/
    change_form.html                # custom status page with 2s poll JS
  tests/
    __init__.py
    factories.py                    # make_prompt, make_job, make_call helpers
    test_models.py
    test_pricing.py
    test_client.py
    test_services.py
    test_tasks.py
    test_admin_prompt.py
    test_admin_jobs.py
    test_seed_prompts.py
    test_celery_stuck_jobs.py

backend/apps/reports/importers/pdf_parser.py     # use case A consumer
backend/apps/reports/templates/admin/reports/report/import_pdf.html
backend/apps/reports/tests/test_pdf_parser.py    # consumer integration tests

backend/tests/fixtures/llm_responses/parsed_report_minimal.json
backend/tests/fixtures/sample.pdf                # 2-page PDF for handler tests

frontend/tests/admin-import-pdf.spec.ts          # E2E smoke (mocks Fireworks)
```

### Modified

- `backend/requirements.txt` — add `openai`, `pdf2image`, `jsonschema`, `Jinja2`.
- `backend/Dockerfile` — `apt-get install poppler-utils`.
- `backend/config/settings/base.py` — `INSTALLED_APPS += ["apps.llm"]`, LLM_* settings, Celery beat schedule.
- `backend/apps/reports/admin.py` — add `import-pdf/` URLs + view + button.
- `backend/apps/reports/templates/admin/reports/report/change_list.html` — third button.
- `backend/tests/conftest.py` — `superuser` fixture moved here so consumer tests can reuse (only if not already shared; today it's defined per-file).
- `.env.example` — `LLM_FIREWORKS_API_KEY=`.
- `docs/ENV.md` — document the new env var.
- `README.md` — short "AI integration" section.

---

## Conventions used in this plan

- **Tests use `pytest-django`.** DB tests get the `db` fixture or `@pytest.mark.django_db`.
- **The OpenAI SDK is mocked** in unit tests via `mocker.patch("apps.llm.client.OpenAI")` (pytest-mock) or `unittest.mock.patch`. Already used elsewhere — pytest-mock isn't in requirements but `unittest.mock` is stdlib; we'll use that.
- **`build_report` signature is `build_report(parsed, image_bytes, *, stage_id)`** — positional 2nd arg, not `images=`. Spec is slightly off; plan calls it as `build_report(parsed, {}, stage_id=stage_id)`.
- **Cascade JS** for the import form is reused from `templates/admin/reports/report/import.html` (lines 80-140) — the new template inlines the same script.
- **Commits** use the existing project convention: `feat(llm): ...`, `feat(reports): ...`, `test(llm): ...`, `chore(deps): ...`.
- **No `--no-verify`.** Pre-commit hooks must pass.
- **No premature DRY across tables.** Per existing memory: keep LLMJob and LLMCall as separate tables even though both have `created_at`/`error_message` — distinct identities.

---

## Task 1: Dependencies, Dockerfile, settings, app skeleton

**Files:**
- Modify: `backend/requirements.txt`
- Modify: `backend/Dockerfile`
- Modify: `backend/config/settings/base.py`
- Modify: `.env.example`
- Create: `backend/apps/llm/__init__.py`
- Create: `backend/apps/llm/apps.py`
- Create: `backend/apps/llm/exceptions.py`

- [ ] **Step 1: Add Python dependencies**

Edit `backend/requirements.txt`, add (alphabetical-ish, grouped with other libs):

```
Jinja2==3.1.4
jsonschema==4.23.0
openai==1.54.0
pdf2image==1.17.0
```

- [ ] **Step 2: Add `poppler-utils` to Dockerfile**

Edit `backend/Dockerfile` line 9-11:

```dockerfile
RUN apt-get update && apt-get install -y --no-install-recommends \
      build-essential libpq-dev curl poppler-utils \
    && rm -rf /var/lib/apt/lists/*
```

- [ ] **Step 3: Create app skeleton**

`backend/apps/llm/__init__.py`:

```python
default_app_config = "apps.llm.apps.LlmConfig"
```

`backend/apps/llm/apps.py`:

```python
from django.apps import AppConfig


class LlmConfig(AppConfig):
    name = "apps.llm"
    label = "llm"
    verbose_name = "LLM"
    default_auto_field = "django.db.models.BigAutoField"
```

`backend/apps/llm/exceptions.py`:

```python
class LLMError(Exception):
    """Base for all apps.llm exceptions."""


class LLMConfigError(LLMError):
    """Provider misconfigured (missing API key, unknown SDK, etc.)."""


class LLMValidationError(LLMError):
    """Output failed JSON parsing or schema validation after retries."""


class LLMCostExceededError(LLMError):
    """Call would exceed LLM_MAX_TOKENS_PER_CALL or LLM_MAX_COST_PER_JOB_USD."""
```

- [ ] **Step 4: Wire app + settings**

Edit `backend/config/settings/base.py`:

a) Add to `INSTALLED_APPS` (after `"apps.reports"`):

```python
    "apps.llm",
```

b) After the Celery block (end of file), append:

```python
from decimal import Decimal  # noqa: E402

# LLM integration (DEV-84)
LLM_FIREWORKS_API_KEY = os.environ.get("LLM_FIREWORKS_API_KEY", "")
LLM_MAX_TOKENS_PER_CALL = int(os.environ.get("LLM_MAX_TOKENS_PER_CALL", "500000"))
LLM_MAX_COST_PER_JOB_USD = Decimal(os.environ.get("LLM_MAX_COST_PER_JOB_USD", "2.00"))
LLM_DEFAULT_MAX_RETRIES = 1

CELERY_BEAT_SCHEDULE = {
    "llm-mark-stuck-jobs": {
        "task": "apps.llm.tasks.mark_stuck_jobs_as_failed",
        "schedule": 60.0,  # every minute
    },
}
```

c) Edit `.env.example` — add at the end:

```
# LLM (DEV-84)
LLM_FIREWORKS_API_KEY=
LLM_MAX_TOKENS_PER_CALL=500000
LLM_MAX_COST_PER_JOB_USD=2.00
```

- [ ] **Step 5: Verify the app loads**

Run: `docker compose exec backend python manage.py check`
Expected: `System check identified no issues (0 silenced).`

- [ ] **Step 6: Commit**

```bash
git add backend/requirements.txt backend/Dockerfile \
  backend/apps/llm/__init__.py backend/apps/llm/apps.py \
  backend/apps/llm/exceptions.py \
  backend/config/settings/base.py .env.example
git commit -m "feat(llm): add app skeleton + deps + settings (DEV-84 task 1)"
```

---

## Task 2: `Prompt` + `PromptVersion` models

**Files:**
- Create: `backend/apps/llm/models/__init__.py`
- Create: `backend/apps/llm/models/prompt.py`
- Create: `backend/apps/llm/tests/__init__.py`
- Create: `backend/apps/llm/tests/factories.py`
- Create: `backend/apps/llm/tests/test_models.py`

- [ ] **Step 1: Write failing model tests**

`backend/apps/llm/tests/__init__.py`: empty file.

`backend/apps/llm/tests/factories.py`:

```python
"""Factories for apps.llm tests."""
from apps.llm.models import Prompt, PromptVersion


def make_prompt(*, key="parse_pdf_report", consumer="reports.pdf_parser",
                with_version=True, body="System prompt body.",
                model_hint="accounts/fireworks/models/kimi-k2-instruct-0905",
                response_format="json_object", json_schema=None):
    p = Prompt.objects.create(key=key, name=key.replace("_", " ").title(),
                              consumer=consumer)
    if with_version:
        v = PromptVersion.objects.create(
            prompt=p, body=body, model_hint=model_hint,
            response_format=response_format, json_schema=json_schema,
        )
        p.active_version = v
        p.save()
    return p
```

`backend/apps/llm/tests/test_models.py`:

```python
import pytest

from apps.llm.models import Prompt, PromptVersion


@pytest.mark.django_db
def test_prompt_version_autoincrements_per_prompt():
    p = Prompt.objects.create(key="x", name="X", consumer="c")
    v1 = PromptVersion.objects.create(prompt=p, body="v1")
    v2 = PromptVersion.objects.create(prompt=p, body="v2")
    assert (v1.version, v2.version) == (1, 2)


@pytest.mark.django_db
def test_prompt_version_autoincrement_independent_per_prompt():
    a = Prompt.objects.create(key="a", name="A", consumer="c")
    b = Prompt.objects.create(key="b", name="B", consumer="c")
    PromptVersion.objects.create(prompt=a, body="va1")
    PromptVersion.objects.create(prompt=a, body="va2")
    vb1 = PromptVersion.objects.create(prompt=b, body="vb1")
    assert vb1.version == 1


@pytest.mark.django_db
def test_save_prompt_version_does_not_auto_activate():
    p = Prompt.objects.create(key="x", name="X", consumer="c")
    v1 = PromptVersion.objects.create(prompt=p, body="v1")
    assert p.active_version_id is None  # explicit set required
    p.active_version = v1
    p.save()
    p.refresh_from_db()
    assert p.active_version_id == v1.pk


@pytest.mark.django_db
def test_prompt_version_unique_per_prompt():
    p = Prompt.objects.create(key="x", name="X", consumer="c")
    PromptVersion.objects.create(prompt=p, body="v1", version=1)
    with pytest.raises(Exception):
        PromptVersion.objects.create(prompt=p, body="dup", version=1)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `docker compose exec backend pytest apps/llm/tests/test_models.py -v`
Expected: FAIL with `ImportError: cannot import name 'Prompt' from 'apps.llm.models'`.

- [ ] **Step 3: Write minimal models**

`backend/apps/llm/models/__init__.py`:

```python
from .prompt import Prompt, PromptVersion

__all__ = ["Prompt", "PromptVersion"]
```

`backend/apps/llm/models/prompt.py`:

```python
from django.conf import settings
from django.db import models


class Prompt(models.Model):
    """A named prompt (e.g. 'parse_pdf_report'). Has N versions; one is active."""
    key = models.SlugField(unique=True, max_length=100)
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    consumer = models.CharField(
        max_length=100,
        help_text="Informational. e.g. 'reports.pdf_parser'.",
    )
    active_version = models.ForeignKey(
        "PromptVersion", on_delete=models.PROTECT,
        related_name="active_for", null=True, blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["key"]

    def __str__(self):
        return self.key


class PromptVersion(models.Model):
    """An immutable snapshot of a Prompt body. Auto-increments per Prompt."""
    RESPONSE_FORMAT_CHOICES = [
        ("text", "Text"),
        ("json_object", "JSON Object"),
    ]

    prompt = models.ForeignKey(
        Prompt, related_name="versions", on_delete=models.CASCADE,
    )
    version = models.PositiveIntegerField()
    body = models.TextField()
    notes = models.CharField(max_length=300, blank=True)
    model_hint = models.CharField(max_length=100, blank=True)
    response_format = models.CharField(
        max_length=20, default="text", choices=RESPONSE_FORMAT_CHOICES,
    )
    json_schema = models.JSONField(null=True, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [("prompt", "version")]
        ordering = ["-version"]

    def __str__(self):
        return f"{self.prompt.key}@v{self.version}"

    def save(self, *args, **kwargs):
        if not self.version:
            last = self.prompt.versions.order_by("-version").first()
            self.version = (last.version + 1) if last else 1
        super().save(*args, **kwargs)
```

- [ ] **Step 4: Generate migration**

Run: `docker compose exec backend python manage.py makemigrations llm`
Expected: `Migrations for 'llm': llm/migrations/0001_initial.py - Create model Prompt - Create model PromptVersion - Add field active_version to prompt`.

- [ ] **Step 5: Apply migration & re-run tests**

Run:
```
docker compose exec backend python manage.py migrate llm
docker compose exec backend pytest apps/llm/tests/test_models.py -v
```
Expected: 4 PASSED.

- [ ] **Step 6: Commit**

```bash
git add backend/apps/llm/models/ backend/apps/llm/tests/__init__.py \
  backend/apps/llm/tests/factories.py backend/apps/llm/tests/test_models.py \
  backend/apps/llm/migrations/
git commit -m "feat(llm): add Prompt + PromptVersion models (DEV-84 task 2)"
```

---

## Task 3: `LLMJob` + `LLMCall` models with denormalized totals

**Files:**
- Create: `backend/apps/llm/models/job.py`
- Create: `backend/apps/llm/models/call.py`
- Modify: `backend/apps/llm/models/__init__.py`
- Modify: `backend/apps/llm/tests/test_models.py`
- Modify: `backend/apps/llm/tests/factories.py`

- [ ] **Step 1: Extend factories**

Edit `backend/apps/llm/tests/factories.py`, append:

```python
from decimal import Decimal

from apps.llm.models import LLMCall, LLMJob


def make_job(*, consumer="reports.pdf_parser",
             handler_path="apps.reports.importers.pdf_parser._run_pdf_parse",
             status=LLMJob.Status.PENDING, triggered_by=None,
             input_metadata=None):
    return LLMJob.objects.create(
        consumer=consumer, handler_path=handler_path, status=status,
        triggered_by=triggered_by, input_metadata=input_metadata or {},
    )


def make_call(*, job=None, prompt_version=None, model="x", input_tokens=100,
              output_tokens=50, cost_usd=Decimal("0.001"), success=True):
    if job is None:
        job = make_job()
    if prompt_version is None:
        prompt = make_prompt()
        prompt_version = prompt.active_version
    return LLMCall.objects.create(
        job=job, prompt_version=prompt_version, model=model,
        input_tokens=input_tokens, output_tokens=output_tokens,
        cost_usd=cost_usd, success=success,
    )
```

- [ ] **Step 2: Write failing tests for denormalization**

Append to `backend/apps/llm/tests/test_models.py`:

```python
from decimal import Decimal

from apps.llm.models import LLMCall, LLMJob
from apps.llm.tests.factories import make_call, make_job, make_prompt


@pytest.mark.django_db
def test_llmjob_total_cost_denormalized_from_calls():
    prompt = make_prompt()
    job = make_job()
    make_call(job=job, prompt_version=prompt.active_version,
              input_tokens=100, output_tokens=200, cost_usd=Decimal("0.01"))
    make_call(job=job, prompt_version=prompt.active_version,
              input_tokens=50, output_tokens=25, cost_usd=Decimal("0.005"))
    job.refresh_from_db()
    assert job.total_input_tokens == 150
    assert job.total_output_tokens == 225
    assert job.total_cost_usd == Decimal("0.015000")


@pytest.mark.django_db
def test_llmjob_status_default_is_pending():
    job = make_job()
    assert job.status == LLMJob.Status.PENDING


@pytest.mark.django_db
def test_llmcall_only_persists_payload_on_failure_default():
    """request_payload/response_payload are nullable; we set them only on errors."""
    call = make_call()
    assert call.request_payload is None
    assert call.response_payload is None
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `docker compose exec backend pytest apps/llm/tests/test_models.py -v -k "llmjob or llmcall"`
Expected: FAIL with `ImportError`.

- [ ] **Step 4: Implement `LLMJob`**

`backend/apps/llm/models/job.py`:

```python
from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.db import models


class LLMJob(models.Model):
    """1 row = 1 user-triggered request. Aggregates N LLMCalls."""

    class Status(models.TextChoices):
        PENDING = "PENDING", "Pendiente"
        RUNNING = "RUNNING", "En curso"
        SUCCESS = "SUCCESS", "Éxito"
        FAILED = "FAILED", "Fallido"

    consumer = models.CharField(max_length=100, db_index=True)
    handler_path = models.CharField(max_length=200)
    triggered_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True,
    )
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.PENDING,
        db_index=True,
    )

    input_metadata = models.JSONField(default=dict, blank=True)
    output_metadata = models.JSONField(default=dict, blank=True)
    error_message = models.TextField(blank=True)

    total_input_tokens = models.PositiveIntegerField(default=0)
    total_output_tokens = models.PositiveIntegerField(default=0)
    total_cost_usd = models.DecimalField(
        max_digits=10, decimal_places=6, default=0,
    )

    result_content_type = models.ForeignKey(
        "contenttypes.ContentType", on_delete=models.SET_NULL,
        null=True, blank=True,
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
        permissions = [
            ("view_costs", "Ver costos LLM"),
        ]

    def __str__(self):
        return f"LLMJob#{self.pk} {self.consumer} {self.status}"
```

- [ ] **Step 5: Implement `LLMCall`**

`backend/apps/llm/models/call.py`:

```python
from django.db import models
from django.db.models import Sum

from .job import LLMJob
from .prompt import PromptVersion


class LLMCall(models.Model):
    """1 row = 1 API call. N calls grouped under one LLMJob."""

    job = models.ForeignKey(
        LLMJob, related_name="calls", on_delete=models.CASCADE,
    )
    prompt_version = models.ForeignKey(
        PromptVersion, on_delete=models.PROTECT,
    )

    provider = models.CharField(max_length=20, default="fireworks")
    model = models.CharField(max_length=100)

    input_tokens = models.PositiveIntegerField(default=0)
    output_tokens = models.PositiveIntegerField(default=0)
    duration_ms = models.PositiveIntegerField(default=0)
    cost_usd = models.DecimalField(
        max_digits=10, decimal_places=6, default=0,
    )

    success = models.BooleanField(default=True)
    error_type = models.CharField(max_length=50, blank=True)
    error_message = models.TextField(blank=True)

    # Only filled on errors (saves storage on the happy path).
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

    def __str__(self):
        return f"LLMCall#{self.pk} job={self.job_id} ok={self.success}"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        # Update denormalized totals on the parent job.
        agg = self.job.calls.aggregate(
            inp=Sum("input_tokens"),
            outp=Sum("output_tokens"),
            cost=Sum("cost_usd"),
        )
        LLMJob.objects.filter(pk=self.job_id).update(
            total_input_tokens=agg["inp"] or 0,
            total_output_tokens=agg["outp"] or 0,
            total_cost_usd=agg["cost"] or 0,
        )
```

- [ ] **Step 6: Re-export models**

Edit `backend/apps/llm/models/__init__.py`:

```python
from .call import LLMCall
from .job import LLMJob
from .prompt import Prompt, PromptVersion

__all__ = ["LLMCall", "LLMJob", "Prompt", "PromptVersion"]
```

- [ ] **Step 7: Migration & run tests**

Run:
```
docker compose exec backend python manage.py makemigrations llm
docker compose exec backend python manage.py migrate llm
docker compose exec backend pytest apps/llm/tests/test_models.py -v
```
Expected: 7 PASSED.

- [ ] **Step 8: Commit**

```bash
git add backend/apps/llm/models/ backend/apps/llm/tests/ \
  backend/apps/llm/migrations/
git commit -m "feat(llm): add LLMJob + LLMCall with denormalized totals (DEV-84 task 3)"
```

---

## Task 4: `pricing.py` — model pricing table & cost calculation

**Files:**
- Create: `backend/apps/llm/pricing.py`
- Create: `backend/apps/llm/tests/test_pricing.py`

- [ ] **Step 1: Write failing tests**

`backend/apps/llm/tests/test_pricing.py`:

```python
from decimal import Decimal

from apps.llm.pricing import calculate_cost, get_provider, MODEL_PRICING


def test_get_provider_returns_fireworks_for_kimi():
    assert get_provider("accounts/fireworks/models/kimi-k2-instruct-0905") == "fireworks"


def test_get_provider_unknown_model_returns_default():
    # Default keeps "fireworks" but with zero pricing — we still return a provider
    # so the consumer gets a clear "missing key" error from the client, not a KeyError here.
    assert get_provider("unknown-model-xyz") == "fireworks"


def test_calculate_cost_known_model():
    # Kimi K2: input 0.6 / output 2.5 per 1M.
    cost = calculate_cost(
        "accounts/fireworks/models/kimi-k2-instruct-0905",
        input_tokens=1_000_000, output_tokens=1_000_000,
    )
    assert cost == Decimal("3.100000")


def test_calculate_cost_partial_tokens():
    cost = calculate_cost(
        "accounts/fireworks/models/kimi-k2-instruct-0905",
        input_tokens=500, output_tokens=200,
    )
    # 500/1M * 0.6 + 200/1M * 2.5 = 0.0003 + 0.0005 = 0.0008
    assert cost == Decimal("0.000800")


def test_calculate_cost_unknown_model_is_zero():
    assert calculate_cost("unknown", 1000, 1000) == Decimal("0E-6")


def test_pricing_table_includes_fireworks_kimi_models():
    keys = set(MODEL_PRICING.keys())
    assert "accounts/fireworks/models/kimi-k2-instruct-0905" in keys
    assert "accounts/fireworks/models/kimi-k2p5" in keys
```

- [ ] **Step 2: Run to verify they fail**

Run: `docker compose exec backend pytest apps/llm/tests/test_pricing.py -v`
Expected: FAIL — `ImportError: cannot import name 'calculate_cost'`.

- [ ] **Step 3: Implement pricing**

`backend/apps/llm/pricing.py`:

```python
"""Model pricing table + cost calculator for apps.llm.

USD per 1M tokens. Update manually when a provider changes prices.
Each entry declares its provider so the client knows which SDK/base_url to use.

Sources cached 2026-04-25: fireworks.ai/pricing, openai.com/pricing,
anthropic.com/pricing.
"""
from decimal import Decimal

MODEL_PRICING: dict[str, dict] = {
    # Fireworks
    "accounts/fireworks/models/kimi-k2-instruct-0905": {
        "provider": "fireworks",
        "input_per_1m": Decimal("0.6"),
        "output_per_1m": Decimal("2.5"),
    },
    "accounts/fireworks/models/kimi-k2p5": {
        "provider": "fireworks",
        "input_per_1m": Decimal("0.6"),
        "output_per_1m": Decimal("2.5"),
    },
    # Templates kept commented — uncomment when adding the provider:
    # "gpt-4o": {
    #     "provider": "openai",
    #     "input_per_1m": Decimal("2.5"),
    #     "output_per_1m": Decimal("10.0"),
    # },
    # "claude-sonnet-4-5": {
    #     "provider": "anthropic",
    #     "input_per_1m": Decimal("3.0"),
    #     "output_per_1m": Decimal("15.0"),
    # },
}

# When the model is unknown we still return a provider (fireworks) so the
# pipeline reaches the client and surfaces a clear "missing key" or "unknown
# model" error instead of a KeyError deep in pricing.
DEFAULT_PRICING: dict = {
    "provider": "fireworks",
    "input_per_1m": Decimal("0"),
    "output_per_1m": Decimal("0"),
}


def get_provider(model: str) -> str:
    return MODEL_PRICING.get(model, DEFAULT_PRICING)["provider"]


def calculate_cost(model: str, input_tokens: int, output_tokens: int) -> Decimal:
    p = MODEL_PRICING.get(model, DEFAULT_PRICING)
    return (
        (Decimal(input_tokens) / Decimal(1_000_000)) * p["input_per_1m"]
        + (Decimal(output_tokens) / Decimal(1_000_000)) * p["output_per_1m"]
    ).quantize(Decimal("0.000001"))
```

- [ ] **Step 4: Run tests**

Run: `docker compose exec backend pytest apps/llm/tests/test_pricing.py -v`
Expected: 6 PASSED.

- [ ] **Step 5: Commit**

```bash
git add backend/apps/llm/pricing.py backend/apps/llm/tests/test_pricing.py
git commit -m "feat(llm): pricing table + cost calculator (DEV-84 task 4)"
```

---

## Task 5: `client.py` — `PROVIDERS` registry + OpenAI-compatible chat()

**Files:**
- Create: `backend/apps/llm/client.py`
- Create: `backend/apps/llm/tests/test_client.py`

- [ ] **Step 1: Write failing client tests**

`backend/apps/llm/tests/test_client.py`:

```python
from unittest.mock import MagicMock, patch

import pytest
from django.test import override_settings

from apps.llm.client import (
    ChatResponse,
    PROVIDERS,
    chat,
    get_client,
)
from apps.llm.exceptions import LLMConfigError


def test_providers_registry_has_fireworks():
    assert "fireworks" in PROVIDERS
    assert PROVIDERS["fireworks"]["sdk"] == "openai"
    assert PROVIDERS["fireworks"]["base_url"] == "https://api.fireworks.ai/inference/v1"


@override_settings(LLM_FIREWORKS_API_KEY="")
def test_get_client_raises_when_key_missing():
    with pytest.raises(LLMConfigError):
        get_client("fireworks")


@override_settings(LLM_FIREWORKS_API_KEY="sk-test")
def test_get_client_unknown_provider_raises():
    with pytest.raises(KeyError):
        get_client("nonexistent-provider")


@override_settings(LLM_FIREWORKS_API_KEY="sk-test")
@patch("apps.llm.client.OpenAI")
def test_get_client_returns_openai_with_base_url(mock_openai):
    get_client("fireworks")
    mock_openai.assert_called_once_with(
        api_key="sk-test",
        base_url="https://api.fireworks.ai/inference/v1",
    )


@override_settings(LLM_FIREWORKS_API_KEY="sk-test")
@patch("apps.llm.client.OpenAI")
def test_chat_routes_kimi_to_fireworks(mock_openai):
    fake_completion = MagicMock()
    fake_completion.choices = [MagicMock()]
    fake_completion.choices[0].message.content = "Hello"
    fake_completion.usage.prompt_tokens = 10
    fake_completion.usage.completion_tokens = 5
    mock_openai.return_value.chat.completions.create.return_value = fake_completion

    resp = chat(
        model="accounts/fireworks/models/kimi-k2-instruct-0905",
        messages=[{"role": "user", "content": "hi"}],
    )

    assert isinstance(resp, ChatResponse)
    assert resp.content == "Hello"
    assert resp.input_tokens == 10
    assert resp.output_tokens == 5
    assert resp.duration_ms >= 0
    mock_openai.return_value.chat.completions.create.assert_called_once()


@override_settings(LLM_FIREWORKS_API_KEY="sk-test")
@patch("apps.llm.client.OpenAI")
def test_chat_passes_response_format_when_provided(mock_openai):
    fake = MagicMock()
    fake.choices = [MagicMock()]
    fake.choices[0].message.content = "{}"
    fake.usage.prompt_tokens = 1
    fake.usage.completion_tokens = 1
    mock_openai.return_value.chat.completions.create.return_value = fake

    chat(
        model="accounts/fireworks/models/kimi-k2-instruct-0905",
        messages=[{"role": "user", "content": "hi"}],
        response_format={"type": "json_object"},
    )

    kwargs = mock_openai.return_value.chat.completions.create.call_args.kwargs
    assert kwargs["response_format"] == {"type": "json_object"}
```

- [ ] **Step 2: Run to verify failure**

Run: `docker compose exec backend pytest apps/llm/tests/test_client.py -v`
Expected: FAIL — module not found.

- [ ] **Step 3: Implement client**

`backend/apps/llm/client.py`:

```python
"""Provider-agnostic LLM client with a PROVIDERS registry.

Only Fireworks is active. OpenAI/Groq/Anthropic templates are commented —
adding a new provider = uncomment + add pricing entry + set env var.
Consumers never pick a provider by hand; they pass `model`, and we derive
the provider via apps.llm.pricing.get_provider(model).
"""
from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any

from django.conf import settings
from openai import OpenAI

from . import pricing
from .exceptions import LLMConfigError


PROVIDERS: dict[str, dict] = {
    "fireworks": {
        "base_url": "https://api.fireworks.ai/inference/v1",
        "api_key_setting": "LLM_FIREWORKS_API_KEY",
        "sdk": "openai",
    },
    # Uncomment to enable:
    # "openai": {
    #     "base_url": None,  # default
    #     "api_key_setting": "LLM_OPENAI_API_KEY",
    #     "sdk": "openai",
    # },
    # "groq": {
    #     "base_url": "https://api.groq.com/openai/v1",
    #     "api_key_setting": "LLM_GROQ_API_KEY",
    #     "sdk": "openai",
    # },
    # "anthropic": {
    #     "base_url": None,
    #     "api_key_setting": "LLM_ANTHROPIC_API_KEY",
    #     "sdk": "anthropic",
    # },
}


@dataclass
class ChatResponse:
    content: str
    input_tokens: int
    output_tokens: int
    duration_ms: int
    raw: Any  # the SDK's completion object, for debugging


def get_client(provider: str):
    cfg = PROVIDERS[provider]
    api_key = getattr(settings, cfg["api_key_setting"], "")
    if not api_key:
        raise LLMConfigError(
            f"Provider '{provider}' configured but {cfg['api_key_setting']} is missing"
        )
    if cfg["sdk"] == "openai":
        return OpenAI(api_key=api_key, base_url=cfg["base_url"])
    if cfg["sdk"] == "anthropic":
        from anthropic import Anthropic  # noqa: lazy import
        return Anthropic(api_key=api_key)
    raise LLMConfigError(f"Unknown SDK: {cfg['sdk']}")


def chat(
    *,
    model: str,
    messages: list[dict],
    response_format: dict | None = None,
    timeout: float = 120.0,
) -> ChatResponse:
    """Single LLM call. Provider is derived from model via pricing."""
    provider = pricing.get_provider(model)
    cfg = PROVIDERS[provider]
    client = get_client(provider)

    if cfg["sdk"] == "openai":
        return _chat_openai(client, model, messages, response_format, timeout)
    if cfg["sdk"] == "anthropic":
        return _chat_anthropic(client, model, messages, response_format, timeout)
    raise LLMConfigError(f"Unknown SDK: {cfg['sdk']}")


def _chat_openai(client, model, messages, response_format, timeout) -> ChatResponse:
    kwargs: dict = {"model": model, "messages": messages, "timeout": timeout}
    if response_format is not None:
        kwargs["response_format"] = response_format
    started = time.monotonic()
    completion = client.chat.completions.create(**kwargs)
    duration_ms = int((time.monotonic() - started) * 1000)
    return ChatResponse(
        content=completion.choices[0].message.content or "",
        input_tokens=getattr(completion.usage, "prompt_tokens", 0),
        output_tokens=getattr(completion.usage, "completion_tokens", 0),
        duration_ms=duration_ms,
        raw=completion,
    )


def _chat_anthropic(client, model, messages, response_format, timeout) -> ChatResponse:
    # Stub. The provider isn't enabled in MVP — see PROVIDERS comment above.
    raise LLMConfigError(
        "Anthropic SDK branch not implemented yet. Uncomment the entry "
        "in PROVIDERS and implement _chat_anthropic to enable."
    )
```

- [ ] **Step 4: Run tests**

Run: `docker compose exec backend pytest apps/llm/tests/test_client.py -v`
Expected: 6 PASSED.

- [ ] **Step 5: Commit**

```bash
git add backend/apps/llm/client.py backend/apps/llm/tests/test_client.py
git commit -m "feat(llm): provider-agnostic client with PROVIDERS registry (DEV-84 task 5)"
```

---

## Task 6: `services.run_prompt` — happy path (resolve, render, call, persist)

**Files:**
- Create: `backend/apps/llm/services.py`
- Create: `backend/apps/llm/tests/test_services.py`

- [ ] **Step 1: Write failing test for happy path**

`backend/apps/llm/tests/test_services.py`:

```python
from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest
from django.test import override_settings

from apps.llm.client import ChatResponse
from apps.llm.models import LLMCall
from apps.llm.services import LLMResponse, run_prompt
from apps.llm.tests.factories import make_job, make_prompt


@pytest.fixture
def fireworks_key(settings):
    settings.LLM_FIREWORKS_API_KEY = "sk-test"


def _fake_chat_response(content, input_tokens=100, output_tokens=50):
    return ChatResponse(
        content=content,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        duration_ms=42,
        raw=MagicMock(),
    )


@pytest.mark.django_db
@patch("apps.llm.services.client.chat")
def test_run_prompt_happy_path_persists_call(mock_chat, fireworks_key):
    mock_chat.return_value = _fake_chat_response("Hello world")
    prompt = make_prompt(body="Hello {{ name }}", response_format="text")
    job = make_job()

    resp = run_prompt(prompt_key=prompt.key, inputs={"name": "Dani"}, job=job)

    assert isinstance(resp, LLMResponse)
    assert resp.content == "Hello world"
    assert resp.parsed is None  # response_format="text"
    assert resp.call.success is True
    assert resp.call.input_tokens == 100
    assert resp.call.output_tokens == 50
    assert resp.call.cost_usd > 0
    assert resp.call.prompt_version_id == prompt.active_version_id
    assert resp.call.job_id == job.pk
    # Jinja2 rendering happened: messages was called with rendered body.
    sent_messages = mock_chat.call_args.kwargs["messages"]
    assert any("Hello Dani" in m.get("content", "") for m in sent_messages
               if isinstance(m.get("content"), str))


@pytest.mark.django_db
def test_run_prompt_unknown_key_raises():
    with pytest.raises(Prompt.DoesNotExist):  # type: ignore[name-defined]
        from apps.llm.models import Prompt
        run_prompt(prompt_key="does-not-exist", inputs={})
```

Note: that second test references `Prompt.DoesNotExist` — Django raises `Prompt.DoesNotExist` when `objects.get()` misses. We import inside the test for clarity.

Replace it with this cleaner version:

```python
@pytest.mark.django_db
def test_run_prompt_unknown_key_raises():
    from apps.llm.models import Prompt
    with pytest.raises(Prompt.DoesNotExist):
        run_prompt(prompt_key="does-not-exist", inputs={})
```

- [ ] **Step 2: Run to verify failure**

Run: `docker compose exec backend pytest apps/llm/tests/test_services.py -v`
Expected: FAIL — `ImportError`.

- [ ] **Step 3: Implement services (happy path only)**

`backend/apps/llm/services.py`:

```python
"""Public API for apps.llm: run_prompt + dispatch_job + LLMResponse.

Consumers ONLY import from here (and from .models). They do not import
from .client, .pricing, .tasks, .handlers — that's the boundary."""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from decimal import Decimal

import jsonschema
from django.conf import settings
from django.utils import timezone
from jinja2 import Environment, StrictUndefined

from . import client, pricing
from .exceptions import LLMConfigError, LLMCostExceededError, LLMValidationError
from .models import LLMCall, LLMJob, Prompt, PromptVersion

logger = logging.getLogger(__name__)

_jinja = Environment(undefined=StrictUndefined, autoescape=False)


@dataclass
class LLMResponse:
    content: str
    parsed: dict | None
    call: LLMCall


def run_prompt(
    prompt_key: str,
    inputs: dict,
    *,
    job: LLMJob | None = None,
    images: list[bytes] | None = None,
    model_override: str | None = None,
    max_retries: int | None = None,
) -> LLMResponse:
    prompt = Prompt.objects.select_related("active_version").get(key=prompt_key)
    pv = prompt.active_version
    if pv is None:
        raise LLMConfigError(f"Prompt '{prompt_key}' has no active version")

    model = model_override or pv.model_hint
    if not model:
        raise LLMConfigError(
            f"Prompt '{prompt_key}' has no model_hint and no model_override"
        )

    rendered = _jinja.from_string(pv.body).render(**inputs)
    messages = _build_messages(rendered, images=images)

    response_format = (
        {"type": "json_object"} if pv.response_format == "json_object" else None
    )

    chat_resp = client.chat(
        model=model, messages=messages, response_format=response_format,
    )

    cost = pricing.calculate_cost(
        model, chat_resp.input_tokens, chat_resp.output_tokens,
    )

    call = LLMCall.objects.create(
        job=job, prompt_version=pv,
        provider=pricing.get_provider(model),
        model=model,
        input_tokens=chat_resp.input_tokens,
        output_tokens=chat_resp.output_tokens,
        duration_ms=chat_resp.duration_ms,
        cost_usd=cost,
        success=True,
    )

    parsed = None
    if pv.response_format == "json_object":
        parsed = json.loads(chat_resp.content)

    logger.info("llm.call_success", extra={
        "call_id": call.pk, "job_id": getattr(job, "pk", None),
        "model": model, "input_tokens": chat_resp.input_tokens,
        "output_tokens": chat_resp.output_tokens, "cost_usd": str(cost),
        "duration_ms": chat_resp.duration_ms,
    })

    return LLMResponse(content=chat_resp.content, parsed=parsed, call=call)


def _build_messages(rendered_body: str, *, images: list[bytes] | None) -> list[dict]:
    """Turn the rendered prompt body + optional images into OpenAI-style messages.

    Convention: the rendered body is the SYSTEM prompt; images go in a
    USER message as image_url[base64] entries. If there are no images, we
    still emit a single-character USER message because some providers reject
    system-only conversations.
    """
    import base64
    messages: list[dict] = [{"role": "system", "content": rendered_body}]
    if images:
        content = []
        for img_bytes in images:
            b64 = base64.b64encode(img_bytes).decode("ascii")
            content.append({
                "type": "image_url",
                "image_url": {"url": f"data:image/png;base64,{b64}"},
            })
        messages.append({"role": "user", "content": content})
    else:
        messages.append({"role": "user", "content": "."})
    return messages
```

- [ ] **Step 4: Run tests**

Run: `docker compose exec backend pytest apps/llm/tests/test_services.py -v`
Expected: 2 PASSED.

- [ ] **Step 5: Commit**

```bash
git add backend/apps/llm/services.py backend/apps/llm/tests/test_services.py
git commit -m "feat(llm): services.run_prompt happy path (DEV-84 task 6)"
```

---

## Task 7: `services.run_prompt` — JSON schema validation + 1 correction retry

**Files:**
- Modify: `backend/apps/llm/services.py`
- Modify: `backend/apps/llm/tests/test_services.py`

- [ ] **Step 1: Write failing tests for JSON validation + retry**

Append to `backend/apps/llm/tests/test_services.py`:

```python
from apps.llm.exceptions import LLMValidationError


_SCHEMA_OBJ = {
    "type": "object",
    "properties": {"answer": {"type": "string"}},
    "required": ["answer"],
}


@pytest.mark.django_db
@patch("apps.llm.services.client.chat")
def test_run_prompt_json_object_returns_parsed(mock_chat, fireworks_key):
    mock_chat.return_value = _fake_chat_response('{"answer": "yes"}')
    prompt = make_prompt(response_format="json_object", json_schema=_SCHEMA_OBJ)
    resp = run_prompt(prompt_key=prompt.key, inputs={})
    assert resp.parsed == {"answer": "yes"}


@pytest.mark.django_db
@patch("apps.llm.services.client.chat")
def test_run_prompt_invalid_json_retries_once_then_succeeds(mock_chat, fireworks_key):
    mock_chat.side_effect = [
        _fake_chat_response("not json at all"),
        _fake_chat_response('{"answer": "yes"}'),
    ]
    prompt = make_prompt(response_format="json_object", json_schema=_SCHEMA_OBJ)
    resp = run_prompt(prompt_key=prompt.key, inputs={})
    assert resp.parsed == {"answer": "yes"}
    assert mock_chat.call_count == 2
    # Two LLMCalls persisted: first failed, second succeeded.
    calls = LLMCall.objects.all().order_by("created_at")
    assert calls.count() == 2
    assert calls[0].success is False
    assert calls[0].error_type == "json_decode"
    assert calls[1].success is True


@pytest.mark.django_db
@patch("apps.llm.services.client.chat")
def test_run_prompt_invalid_json_after_retries_raises(mock_chat, fireworks_key):
    mock_chat.return_value = _fake_chat_response("still not json")
    prompt = make_prompt(response_format="json_object", json_schema=_SCHEMA_OBJ)
    with pytest.raises(LLMValidationError):
        run_prompt(prompt_key=prompt.key, inputs={})
    assert mock_chat.call_count == 2  # initial + 1 retry


@pytest.mark.django_db
@patch("apps.llm.services.client.chat")
def test_run_prompt_schema_violation_retries_then_raises(mock_chat, fireworks_key):
    mock_chat.return_value = _fake_chat_response('{"wrong_field": 1}')
    prompt = make_prompt(response_format="json_object", json_schema=_SCHEMA_OBJ)
    with pytest.raises(LLMValidationError):
        run_prompt(prompt_key=prompt.key, inputs={})
    assert mock_chat.call_count == 2
    calls = LLMCall.objects.all()
    assert all(c.error_type == "schema_validation" for c in calls)
```

- [ ] **Step 2: Run to verify failure**

Run: `docker compose exec backend pytest apps/llm/tests/test_services.py -v -k "json or schema"`
Expected: FAIL — retry/validation not implemented.

- [ ] **Step 3: Refactor `run_prompt` with retry loop**

Replace the body of `run_prompt` in `backend/apps/llm/services.py`. Find the section starting `chat_resp = client.chat(...)` and ending `return LLMResponse(...)`, replace with:

```python
    max_retries = (
        max_retries if max_retries is not None
        else settings.LLM_DEFAULT_MAX_RETRIES
    )

    last_call: LLMCall | None = None
    last_error_type: str = ""
    last_error_msg: str = ""
    correction_msg: str | None = None

    for attempt in range(max_retries + 1):
        msgs = list(messages)
        if correction_msg:
            msgs.append({"role": "user", "content": correction_msg})

        chat_resp = client.chat(
            model=model, messages=msgs, response_format=response_format,
        )
        cost = pricing.calculate_cost(
            model, chat_resp.input_tokens, chat_resp.output_tokens,
        )

        # Validate output if json_object.
        parsed: dict | None = None
        error_type = ""
        error_msg = ""
        try:
            if pv.response_format == "json_object":
                parsed = json.loads(chat_resp.content)
                if pv.json_schema:
                    jsonschema.validate(parsed, pv.json_schema)
        except json.JSONDecodeError as exc:
            error_type, error_msg = "json_decode", str(exc)
        except jsonschema.ValidationError as exc:
            error_type, error_msg = "schema_validation", exc.message

        success = error_type == ""

        last_call = LLMCall.objects.create(
            job=job, prompt_version=pv,
            provider=pricing.get_provider(model),
            model=model,
            input_tokens=chat_resp.input_tokens,
            output_tokens=chat_resp.output_tokens,
            duration_ms=chat_resp.duration_ms,
            cost_usd=cost,
            success=success,
            error_type=error_type,
            error_message=error_msg,
            response_payload=(
                {"content": chat_resp.content} if not success else None
            ),
        )

        if success:
            logger.info("llm.call_success", extra={
                "call_id": last_call.pk, "job_id": getattr(job, "pk", None),
                "model": model, "input_tokens": chat_resp.input_tokens,
                "output_tokens": chat_resp.output_tokens,
                "cost_usd": str(cost), "duration_ms": chat_resp.duration_ms,
            })
            return LLMResponse(
                content=chat_resp.content, parsed=parsed, call=last_call,
            )

        last_error_type, last_error_msg = error_type, error_msg
        logger.warning("llm.call_retry", extra={
            "call_id": last_call.pk, "error_type": error_type, "attempt": attempt,
        })
        correction_msg = _correction_message(error_type, error_msg)

    raise LLMValidationError(
        f"After {max_retries + 1} attempts, last error: "
        f"{last_error_type}: {last_error_msg}"
    )
```

Add the helper `_correction_message` at module level:

```python
def _correction_message(error_type: str, error_msg: str) -> str:
    if error_type == "json_decode":
        return (
            "Tu respuesta anterior no fue JSON válido. Devolvé exactamente "
            "un objeto JSON, sin texto adicional, sin ```json fences. "
            f"Error: {error_msg}"
        )
    if error_type == "schema_validation":
        return (
            "Tu respuesta JSON no respetó el schema. Corregí los campos "
            f"que falten o sean del tipo incorrecto. Error: {error_msg}"
        )
    return f"Tu respuesta anterior tuvo un error: {error_msg}. Reintentá."
```

- [ ] **Step 4: Run tests**

Run: `docker compose exec backend pytest apps/llm/tests/test_services.py -v`
Expected: 6 PASSED (2 from task 6 + 4 new).

- [ ] **Step 5: Commit**

```bash
git add backend/apps/llm/services.py backend/apps/llm/tests/test_services.py
git commit -m "feat(llm): JSON schema validation + 1 correction retry (DEV-84 task 7)"
```

---

## Task 8: `services.run_prompt` — cost guardrails (per-call & per-job)

**Files:**
- Modify: `backend/apps/llm/services.py`
- Modify: `backend/apps/llm/tests/test_services.py`

- [ ] **Step 1: Write failing tests for caps**

Append to `backend/apps/llm/tests/test_services.py`:

```python
from apps.llm.exceptions import LLMCostExceededError


@pytest.mark.django_db
@patch("apps.llm.services.client.chat")
def test_run_prompt_blocks_when_payload_exceeds_token_cap(mock_chat, settings):
    settings.LLM_FIREWORKS_API_KEY = "sk-test"
    settings.LLM_MAX_TOKENS_PER_CALL = 10
    prompt = make_prompt(body="X" * 100_000)  # huge prompt
    with pytest.raises(LLMCostExceededError):
        run_prompt(prompt_key=prompt.key, inputs={})
    mock_chat.assert_not_called()
    # A failed LLMCall row was persisted with error_type=payload_too_large.
    call = LLMCall.objects.get()
    assert call.error_type == "payload_too_large"
    assert call.success is False


@pytest.mark.django_db
@patch("apps.llm.services.client.chat")
def test_run_prompt_blocks_when_job_total_cost_exceeds_cap(mock_chat, settings):
    settings.LLM_FIREWORKS_API_KEY = "sk-test"
    settings.LLM_MAX_COST_PER_JOB_USD = Decimal("0.001")
    prompt = make_prompt()
    job = make_job()
    # Pre-load cost on the job above the cap.
    job.total_cost_usd = Decimal("0.005")
    job.save()
    with pytest.raises(LLMCostExceededError):
        run_prompt(prompt_key=prompt.key, inputs={}, job=job)
    mock_chat.assert_not_called()
    call = job.calls.get()
    assert call.error_type == "cost_exceeded"
```

- [ ] **Step 2: Run to verify failure**

Run: `docker compose exec backend pytest apps/llm/tests/test_services.py -v -k "cost or token_cap or payload"`
Expected: FAIL — caps not implemented.

- [ ] **Step 3: Add the guardrails**

Edit `backend/apps/llm/services.py`. After the line that builds `messages = _build_messages(...)`, **before** the retry loop, insert:

```python
    # Token cap (rough estimate: ~4 chars per token for English; we use 3
    # as a safer rule of thumb to avoid undercount on prompts with code/JSON).
    rendered_chars = sum(_message_char_count(m) for m in messages)
    estimated_tokens = rendered_chars // 3
    if estimated_tokens > settings.LLM_MAX_TOKENS_PER_CALL:
        _record_blocked_call(
            pv=pv, job=job, model=model,
            error_type="payload_too_large",
            error_message=(
                f"Estimated {estimated_tokens} tokens > cap "
                f"{settings.LLM_MAX_TOKENS_PER_CALL}"
            ),
        )
        raise LLMCostExceededError(
            f"Payload too large: ~{estimated_tokens} tokens > "
            f"{settings.LLM_MAX_TOKENS_PER_CALL}"
        )

    if job is not None and job.total_cost_usd >= settings.LLM_MAX_COST_PER_JOB_USD:
        _record_blocked_call(
            pv=pv, job=job, model=model,
            error_type="cost_exceeded",
            error_message=(
                f"Job total {job.total_cost_usd} USD already at/above cap "
                f"{settings.LLM_MAX_COST_PER_JOB_USD}"
            ),
        )
        raise LLMCostExceededError(
            f"Job cost {job.total_cost_usd} USD exceeds cap "
            f"{settings.LLM_MAX_COST_PER_JOB_USD}"
        )
```

Add helpers at module level:

```python
def _message_char_count(message: dict) -> int:
    content = message.get("content")
    if isinstance(content, str):
        return len(content)
    if isinstance(content, list):
        # image_url entries — count the base64 string length.
        total = 0
        for chunk in content:
            if chunk.get("type") == "image_url":
                total += len(chunk.get("image_url", {}).get("url", ""))
        return total
    return 0


def _record_blocked_call(*, pv, job, model, error_type, error_message):
    LLMCall.objects.create(
        job=job, prompt_version=pv,
        provider=pricing.get_provider(model),
        model=model, input_tokens=0, output_tokens=0,
        duration_ms=0, cost_usd=Decimal("0"),
        success=False, error_type=error_type, error_message=error_message,
    )
```

- [ ] **Step 4: Run tests**

Run: `docker compose exec backend pytest apps/llm/tests/test_services.py -v`
Expected: 8 PASSED.

- [ ] **Step 5: Commit**

```bash
git add backend/apps/llm/services.py backend/apps/llm/tests/test_services.py
git commit -m "feat(llm): per-call and per-job cost guardrails (DEV-84 task 8)"
```

---

## Task 9: `dispatch_job` + Celery task `run_llm_job` + handler resolution

**Files:**
- Modify: `backend/apps/llm/services.py`
- Create: `backend/apps/llm/handlers.py`
- Create: `backend/apps/llm/tasks.py`
- Create: `backend/apps/llm/tests/test_tasks.py`

- [ ] **Step 1: Write failing tests for dispatch + run**

`backend/apps/llm/tests/test_tasks.py`:

```python
from unittest.mock import patch

import pytest
from django.test import override_settings

from apps.llm.models import LLMJob
from apps.llm.services import dispatch_job
from apps.llm.tasks import run_llm_job
from apps.llm.tests.factories import make_job


# Synchronous celery for tests.
@override_settings(CELERY_TASK_ALWAYS_EAGER=True)
@pytest.mark.django_db
def test_dispatch_job_creates_pending_and_queues(monkeypatch):
    called = {}

    def fake_delay(job_id):
        called["job_id"] = job_id

    monkeypatch.setattr("apps.llm.services.run_llm_job.delay", fake_delay)

    job = dispatch_job(
        consumer="test.consumer",
        handler_path="apps.llm.tests.test_tasks._noop_handler",
        input_metadata={"a": 1},
    )
    assert job.status == LLMJob.Status.PENDING
    assert job.consumer == "test.consumer"
    assert called == {"job_id": job.pk}


def _noop_handler(job):
    job.output_metadata = {"ok": True}
    job.save()


def _failing_handler(job):
    raise RuntimeError("boom")


@pytest.mark.django_db
def test_run_llm_job_resolves_handler_and_marks_success():
    job = make_job(handler_path="apps.llm.tests.test_tasks._noop_handler")
    run_llm_job(job.pk)
    job.refresh_from_db()
    assert job.status == LLMJob.Status.SUCCESS
    assert job.output_metadata == {"ok": True}
    assert job.started_at is not None
    assert job.finished_at is not None


@pytest.mark.django_db
def test_run_llm_job_marks_failed_on_handler_exception():
    job = make_job(handler_path="apps.llm.tests.test_tasks._failing_handler")
    run_llm_job(job.pk)
    job.refresh_from_db()
    assert job.status == LLMJob.Status.FAILED
    assert "boom" in job.error_message
    assert job.finished_at is not None
```

- [ ] **Step 2: Run to verify failure**

Run: `docker compose exec backend pytest apps/llm/tests/test_tasks.py -v`
Expected: FAIL — `dispatch_job` and `run_llm_job` not defined.

- [ ] **Step 3: Implement `dispatch_job`**

Append to `backend/apps/llm/services.py`:

```python
def dispatch_job(
    *,
    consumer: str,
    handler_path: str,
    input_metadata: dict | None = None,
    triggered_by=None,
) -> LLMJob:
    """Create a PENDING LLMJob and enqueue the worker. Returns the job."""
    job = LLMJob.objects.create(
        consumer=consumer,
        handler_path=handler_path,
        input_metadata=input_metadata or {},
        triggered_by=triggered_by,
        status=LLMJob.Status.PENDING,
    )
    # Lazy import to avoid Celery touching settings at module import.
    from .tasks import run_llm_job
    run_llm_job.delay(job.pk)
    return job
```

- [ ] **Step 4: Implement Celery task**

`backend/apps/llm/handlers.py`:

```python
"""Informational registry of consumer handler paths.

Keys are consumer names; values are dotted paths to the handler callable.
The Celery task uses django.utils.module_loading.import_string to resolve
LLMJob.handler_path directly, so this registry is for documentation / debug
only. New consumers register here for discoverability."""

REGISTRY: dict[str, str] = {
    "reports.pdf_parser": "apps.reports.importers.pdf_parser._run_pdf_parse",
}
```

`backend/apps/llm/tasks.py`:

```python
"""Celery tasks for apps.llm.

run_llm_job: resolve and execute a consumer handler.
mark_stuck_jobs_as_failed: scheduled cleanup of RUNNING jobs > 10min.
"""
from __future__ import annotations

import logging
from datetime import timedelta

from celery import shared_task
from django.utils import timezone
from django.utils.module_loading import import_string

from .models import LLMJob

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=0)
def run_llm_job(self, job_id: int) -> None:
    """Resolve LLMJob.handler_path and run it. Retry policy is inside services."""
    try:
        job = LLMJob.objects.get(pk=job_id)
    except LLMJob.DoesNotExist:
        logger.error("llm.job_not_found", extra={"job_id": job_id})
        return

    job.status = LLMJob.Status.RUNNING
    job.started_at = timezone.now()
    job.save(update_fields=["status", "started_at"])

    try:
        handler = import_string(job.handler_path)
        handler(job)
        job.refresh_from_db()
        job.status = LLMJob.Status.SUCCESS
    except Exception as exc:  # noqa: BLE001 — capture all to mark FAILED
        logger.exception("llm.job_failed", extra={
            "job_id": job_id, "consumer": job.consumer,
        })
        job.refresh_from_db()
        job.status = LLMJob.Status.FAILED
        job.error_message = f"{type(exc).__name__}: {exc}"
    finally:
        job.finished_at = timezone.now()
        job.save()


@shared_task
def mark_stuck_jobs_as_failed(threshold_minutes: int = 10) -> int:
    """Beat task: mark RUNNING jobs older than `threshold_minutes` as FAILED."""
    cutoff = timezone.now() - timedelta(minutes=threshold_minutes)
    qs = LLMJob.objects.filter(
        status=LLMJob.Status.RUNNING, started_at__lt=cutoff,
    )
    count = qs.count()
    qs.update(
        status=LLMJob.Status.FAILED,
        finished_at=timezone.now(),
        error_message=f"Job stuck > {threshold_minutes} minutes — auto-failed",
    )
    if count:
        logger.warning("llm.stuck_jobs_marked_failed", extra={"count": count})
    return count
```

- [ ] **Step 5: Run tests**

Run: `docker compose exec backend pytest apps/llm/tests/test_tasks.py -v`
Expected: 3 PASSED.

- [ ] **Step 6: Commit**

```bash
git add backend/apps/llm/services.py backend/apps/llm/handlers.py \
  backend/apps/llm/tasks.py backend/apps/llm/tests/test_tasks.py
git commit -m "feat(llm): dispatch_job + Celery handler resolution (DEV-84 task 9)"
```

---

## Task 10: Beat task — `mark_stuck_jobs_as_failed` (test in isolation)

**Files:**
- Create: `backend/apps/llm/tests/test_celery_stuck_jobs.py`

- [ ] **Step 1: Write failing tests**

`backend/apps/llm/tests/test_celery_stuck_jobs.py`:

```python
from datetime import timedelta

import pytest
from django.utils import timezone

from apps.llm.models import LLMJob
from apps.llm.tasks import mark_stuck_jobs_as_failed
from apps.llm.tests.factories import make_job


@pytest.mark.django_db
def test_marks_running_jobs_older_than_threshold():
    fresh = make_job(status=LLMJob.Status.RUNNING)
    fresh.started_at = timezone.now() - timedelta(minutes=2)
    fresh.save()

    stuck = make_job(status=LLMJob.Status.RUNNING)
    stuck.started_at = timezone.now() - timedelta(minutes=15)
    stuck.save()

    count = mark_stuck_jobs_as_failed(threshold_minutes=10)

    assert count == 1
    fresh.refresh_from_db()
    stuck.refresh_from_db()
    assert fresh.status == LLMJob.Status.RUNNING
    assert stuck.status == LLMJob.Status.FAILED
    assert "auto-failed" in stuck.error_message


@pytest.mark.django_db
def test_does_not_touch_pending_or_success_or_failed_jobs():
    pending = make_job(status=LLMJob.Status.PENDING)
    success = make_job(status=LLMJob.Status.SUCCESS)
    failed = make_job(status=LLMJob.Status.FAILED)
    for j in (pending, success, failed):
        j.started_at = timezone.now() - timedelta(hours=1)
        j.save()

    mark_stuck_jobs_as_failed(threshold_minutes=10)

    pending.refresh_from_db()
    success.refresh_from_db()
    failed.refresh_from_db()
    assert pending.status == LLMJob.Status.PENDING
    assert success.status == LLMJob.Status.SUCCESS
    assert failed.status == LLMJob.Status.FAILED
```

- [ ] **Step 2: Run to verify pass (impl already exists from task 9)**

Run: `docker compose exec backend pytest apps/llm/tests/test_celery_stuck_jobs.py -v`
Expected: 2 PASSED.

- [ ] **Step 3: Commit**

```bash
git add backend/apps/llm/tests/test_celery_stuck_jobs.py
git commit -m "test(llm): coverage for mark_stuck_jobs_as_failed (DEV-84 task 10)"
```

---

## Task 11: Admin — `Prompt` + `PromptVersion` (list, edit, new version, set-active, diff)

**Files:**
- Create: `backend/apps/llm/admin.py`
- Create: `backend/apps/llm/tests/test_admin_prompt.py`

- [ ] **Step 1: Write failing admin tests**

`backend/apps/llm/tests/test_admin_prompt.py`:

```python
import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse

from apps.llm.models import Prompt, PromptVersion
from apps.llm.tests.factories import make_prompt


@pytest.fixture
def superuser(db):
    return get_user_model().objects.create_superuser(
        email="su-llm-admin@x.com", password="pass",
    )


@pytest.mark.django_db
def test_changelist_renders_for_superuser(client, superuser):
    make_prompt()
    client.force_login(superuser)
    resp = client.get(reverse("admin:llm_prompt_changelist"))
    assert resp.status_code == 200
    assert b"parse_pdf_report" in resp.content


@pytest.mark.django_db
def test_new_version_view_creates_inactive_version(client, superuser):
    p = make_prompt()
    client.force_login(superuser)
    resp = client.post(
        reverse("admin:llm_prompt_new_version", args=[p.pk]),
        {
            "body": "Updated body",
            "notes": "tweaked",
            "model_hint": "accounts/fireworks/models/kimi-k2p5",
            "response_format": "json_object",
            "json_schema": "",
        },
    )
    assert resp.status_code in (302, 303)
    p.refresh_from_db()
    assert p.versions.count() == 2
    new_v = p.versions.order_by("-version").first()
    assert new_v.body == "Updated body"
    # Did NOT auto-activate.
    assert p.active_version_id != new_v.pk


@pytest.mark.django_db
def test_set_active_updates_pointer(client, superuser):
    p = make_prompt()
    v2 = PromptVersion.objects.create(prompt=p, body="v2")
    client.force_login(superuser)
    resp = client.post(
        reverse("admin:llm_prompt_set_active", args=[p.pk, v2.pk])
    )
    assert resp.status_code in (302, 303)
    p.refresh_from_db()
    assert p.active_version_id == v2.pk


@pytest.mark.django_db
def test_diff_view_renders_html_diff(client, superuser):
    p = make_prompt(body="line one\nline two")
    v2 = PromptVersion.objects.create(prompt=p, body="line one\nline TWO")
    client.force_login(superuser)
    url = reverse("admin:llm_prompt_diff", args=[p.pk, p.active_version.pk, v2.pk])
    resp = client.get(url)
    assert resp.status_code == 200
    assert b"line two" in resp.content
    assert b"line TWO" in resp.content


@pytest.mark.django_db
def test_anon_blocked_from_admin(client):
    p = make_prompt()
    resp = client.get(reverse("admin:llm_prompt_changelist"))
    # Django redirects to login.
    assert resp.status_code == 302
```

- [ ] **Step 2: Run to verify failure**

Run: `docker compose exec backend pytest apps/llm/tests/test_admin_prompt.py -v`
Expected: FAIL — admin not registered.

- [ ] **Step 3: Implement Prompt admin**

`backend/apps/llm/admin.py`:

```python
"""Admin for apps.llm.

PromptAdmin: name/description editable, list of versions read-only,
new-version + set-active + diff actions.
LLMJobAdmin / LLMCallAdmin: read-only audit + status page.
"""
import difflib
import json
import logging

from django.contrib import admin, messages
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import path, reverse

from .models import LLMCall, LLMJob, Prompt, PromptVersion

logger = logging.getLogger(__name__)


class PromptVersionInline(admin.TabularInline):
    model = PromptVersion
    extra = 0
    fields = ("version", "model_hint", "response_format", "notes",
              "created_by", "created_at")
    readonly_fields = fields
    can_delete = False
    show_change_link = True

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Prompt)
class PromptAdmin(admin.ModelAdmin):
    list_display = ("key", "name", "consumer", "active_version_display",
                    "updated_at")
    list_filter = ("consumer",)
    search_fields = ("key", "name", "description", "consumer")
    fieldsets = (
        (None, {"fields": ("key", "name", "description", "consumer",
                           "active_version_display_ro")}),
    )
    readonly_fields = ("active_version_display_ro",)
    inlines = [PromptVersionInline]

    @admin.display(description="Versión activa")
    def active_version_display(self, obj):
        return f"v{obj.active_version.version}" if obj.active_version else "—"

    @admin.display(description="Versión activa")
    def active_version_display_ro(self, obj):
        return self.active_version_display(obj)

    def get_urls(self):
        urls = super().get_urls()
        custom = [
            path("<int:prompt_id>/new-version/",
                 self.admin_site.admin_view(self.new_version_view),
                 name="llm_prompt_new_version"),
            path("<int:prompt_id>/set-active/<int:version_id>/",
                 self.admin_site.admin_view(self.set_active_view),
                 name="llm_prompt_set_active"),
            path("<int:prompt_id>/diff/<int:a_id>/<int:b_id>/",
                 self.admin_site.admin_view(self.diff_view),
                 name="llm_prompt_diff"),
        ]
        return custom + urls

    def new_version_view(self, request, prompt_id: int):
        p = get_object_or_404(Prompt, pk=prompt_id)
        if request.method == "POST":
            schema_raw = request.POST.get("json_schema", "").strip()
            try:
                schema = json.loads(schema_raw) if schema_raw else None
            except json.JSONDecodeError as exc:
                messages.error(request, f"json_schema inválido: {exc}")
                return redirect(reverse(
                    "admin:llm_prompt_change", args=[prompt_id],
                ))
            v = PromptVersion.objects.create(
                prompt=p,
                body=request.POST.get("body", ""),
                notes=request.POST.get("notes", "")[:300],
                model_hint=request.POST.get("model_hint", "")[:100],
                response_format=request.POST.get("response_format", "text"),
                json_schema=schema,
                created_by=request.user,
            )
            messages.success(request,
                             f"Creada {p.key}@v{v.version} (no activada).")
            return redirect(reverse(
                "admin:llm_prompt_change", args=[prompt_id],
            ))
        # GET: render a small form template inline.
        return render(request, "admin/llm/prompt/new_version.html", {
            **self.admin_site.each_context(request),
            "prompt": p,
            "active": p.active_version,
            "opts": self.model._meta,
        })

    def set_active_view(self, request, prompt_id: int, version_id: int):
        p = get_object_or_404(Prompt, pk=prompt_id)
        v = get_object_or_404(PromptVersion, pk=version_id, prompt=p)
        p.active_version = v
        p.save()
        messages.success(request, f"{p.key}@v{v.version} ahora es la versión activa.")
        return redirect(reverse("admin:llm_prompt_change", args=[prompt_id]))

    def diff_view(self, request, prompt_id: int, a_id: int, b_id: int):
        p = get_object_or_404(Prompt, pk=prompt_id)
        a = get_object_or_404(PromptVersion, pk=a_id, prompt=p)
        b = get_object_or_404(PromptVersion, pk=b_id, prompt=p)
        diff_html = difflib.HtmlDiff(wrapcolumn=80).make_table(
            a.body.splitlines(), b.body.splitlines(),
            fromdesc=f"v{a.version}", todesc=f"v{b.version}",
            context=False,
        )
        return render(request, "admin/llm/prompt/diff.html", {
            **self.admin_site.each_context(request),
            "prompt": p, "a": a, "b": b, "diff_html": diff_html,
            "opts": self.model._meta,
        })


@admin.register(PromptVersion)
class PromptVersionAdmin(admin.ModelAdmin):
    list_display = ("prompt", "version", "model_hint", "response_format",
                    "created_by", "created_at")
    list_filter = ("response_format", "prompt__consumer")
    search_fields = ("prompt__key", "notes", "body")
    readonly_fields = ("prompt", "version", "body", "notes", "model_hint",
                       "response_format", "json_schema", "created_by", "created_at")

    def has_add_permission(self, request):
        return False
```

- [ ] **Step 4: Create the admin templates**

`backend/apps/llm/templates/admin/llm/prompt/new_version.html`:

```html
{% extends "admin/base_site.html" %}
{% block content %}
<h1>Nueva versión de {{ prompt.key }}</h1>
<p>Versión activa actual: v{{ active.version|default:"—" }}.
   Esta nueva versión NO se va a activar automáticamente.</p>
<form method="post">
  {% csrf_token %}
  <fieldset class="module aligned">
    <div class="form-row">
      <label for="id_body">Body</label>
      <textarea id="id_body" name="body" rows="20" cols="100">{{ active.body }}</textarea>
    </div>
    <div class="form-row">
      <label for="id_notes">Notas</label>
      <input type="text" id="id_notes" name="notes" maxlength="300">
    </div>
    <div class="form-row">
      <label for="id_model_hint">Model hint</label>
      <input type="text" id="id_model_hint" name="model_hint" maxlength="100"
             value="{{ active.model_hint }}">
    </div>
    <div class="form-row">
      <label for="id_response_format">Formato</label>
      <select name="response_format" id="id_response_format">
        <option value="text" {% if active.response_format == 'text' %}selected{% endif %}>text</option>
        <option value="json_object" {% if active.response_format == 'json_object' %}selected{% endif %}>json_object</option>
      </select>
    </div>
    <div class="form-row">
      <label for="id_json_schema">JSON schema (opcional)</label>
      <textarea id="id_json_schema" name="json_schema" rows="6" cols="100">{% if active.json_schema %}{{ active.json_schema|safe }}{% endif %}</textarea>
    </div>
  </fieldset>
  <div class="submit-row">
    <input type="submit" class="default" value="Crear versión">
  </div>
</form>
{% endblock %}
```

`backend/apps/llm/templates/admin/llm/prompt/diff.html`:

```html
{% extends "admin/base_site.html" %}
{% block content %}
<h1>Diff: {{ prompt.key }} v{{ a.version }} ↔ v{{ b.version }}</h1>
{{ diff_html|safe }}
<p style="margin-top:1em;">
  <a href="{% url 'admin:llm_prompt_change' prompt.pk %}">← Volver</a>
</p>
{% endblock %}
```

- [ ] **Step 5: Run tests**

Run: `docker compose exec backend pytest apps/llm/tests/test_admin_prompt.py -v`
Expected: 5 PASSED.

- [ ] **Step 6: Commit**

```bash
git add backend/apps/llm/admin.py \
  backend/apps/llm/templates/admin/llm/prompt/ \
  backend/apps/llm/tests/test_admin_prompt.py
git commit -m "feat(llm): admin for prompts (new version, set active, diff) (DEV-84 task 11)"
```

---

## Task 12: Admin — `LLMJob` & `LLMCall` read-only audit + cost permission

**Files:**
- Modify: `backend/apps/llm/admin.py`
- Create: `backend/apps/llm/tests/test_admin_jobs.py`

- [ ] **Step 1: Write failing tests**

`backend/apps/llm/tests/test_admin_jobs.py`:

```python
import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse

from apps.llm.models import LLMJob
from apps.llm.tests.factories import make_call, make_job, make_prompt


@pytest.fixture
def superuser(db):
    return get_user_model().objects.create_superuser(
        email="su-llm-jobs@x.com", password="pass",
    )


@pytest.fixture
def staff(db):
    return get_user_model().objects.create_user(
        email="staff-llm@x.com", password="pass", is_staff=True,
    )


@pytest.mark.django_db
def test_jobs_changelist_renders(client, superuser):
    job = make_job(status=LLMJob.Status.SUCCESS)
    client.force_login(superuser)
    resp = client.get(reverse("admin:llm_llmjob_changelist"))
    assert resp.status_code == 200
    assert str(job.pk).encode() in resp.content


@pytest.mark.django_db
def test_calls_changelist_only_for_superuser(client, staff):
    """LLMCall.view permission is restricted to superuser by spec."""
    client.force_login(staff)
    resp = client.get(reverse("admin:llm_llmcall_changelist"))
    assert resp.status_code in (302, 403)


@pytest.mark.django_db
def test_calls_changelist_visible_to_superuser(client, superuser):
    prompt = make_prompt()
    job = make_job()
    make_call(job=job, prompt_version=prompt.active_version)
    client.force_login(superuser)
    resp = client.get(reverse("admin:llm_llmcall_changelist"))
    assert resp.status_code == 200
```

- [ ] **Step 2: Run to verify failure**

Run: `docker compose exec backend pytest apps/llm/tests/test_admin_jobs.py -v`
Expected: FAIL — admins not registered.

- [ ] **Step 3: Add Job + Call admins**

Append to `backend/apps/llm/admin.py`:

```python
@admin.register(LLMJob)
class LLMJobAdmin(admin.ModelAdmin):
    list_display = ("pk", "consumer", "status", "triggered_by",
                    "total_cost_display", "created_at", "finished_at")
    list_filter = ("status", "consumer")
    search_fields = ("consumer", "handler_path", "error_message")
    readonly_fields = (
        "consumer", "handler_path", "triggered_by", "status",
        "input_metadata", "output_metadata", "error_message",
        "total_input_tokens", "total_output_tokens", "total_cost_display",
        "started_at", "finished_at", "created_at",
        "result_content_type", "result_object_id",
    )
    fieldsets = (
        (None, {"fields": (
            "consumer", "handler_path", "triggered_by", "status",
            "input_metadata", "output_metadata", "error_message",
            "total_input_tokens", "total_output_tokens", "total_cost_display",
            "started_at", "finished_at", "created_at",
            "result_content_type", "result_object_id",
        )}),
    )

    @admin.display(description="Costo USD")
    def total_cost_display(self, obj):
        # Hide costs unless user has the custom permission (or is superuser).
        request = getattr(self, "_current_request", None)
        if request is not None and not _user_can_view_costs(request.user):
            return "—"
        return f"${obj.total_cost_usd}"

    def get_queryset(self, request):
        self._current_request = request
        return super().get_queryset(request)

    def has_add_permission(self, request):
        return False


@admin.register(LLMCall)
class LLMCallAdmin(admin.ModelAdmin):
    list_display = ("pk", "job", "model", "success", "input_tokens",
                    "output_tokens", "cost_display", "duration_ms", "created_at")
    list_filter = ("success", "error_type", "model")
    search_fields = ("model", "error_message", "job__consumer")
    readonly_fields = (
        "job", "prompt_version", "provider", "model",
        "input_tokens", "output_tokens", "duration_ms", "cost_display",
        "success", "error_type", "error_message",
        "request_payload", "response_payload", "created_at",
    )

    @admin.display(description="Costo USD")
    def cost_display(self, obj):
        request = getattr(self, "_current_request", None)
        if request is not None and not _user_can_view_costs(request.user):
            return "—"
        return f"${obj.cost_usd}"

    def get_queryset(self, request):
        self._current_request = request
        return super().get_queryset(request)

    def has_module_permission(self, request):
        # Restrict the entire LLMCall admin to superusers (PII risk in payloads).
        return request.user.is_superuser

    def has_view_permission(self, request, obj=None):
        return request.user.is_superuser

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


def _user_can_view_costs(user) -> bool:
    return user.is_superuser or user.has_perm("llm.view_costs")
```

- [ ] **Step 4: Run tests**

Run: `docker compose exec backend pytest apps/llm/tests/test_admin_jobs.py -v`
Expected: 3 PASSED.

- [ ] **Step 5: Commit**

```bash
git add backend/apps/llm/admin.py backend/apps/llm/tests/test_admin_jobs.py
git commit -m "feat(llm): read-only admin for LLMJob/LLMCall + cost permission (DEV-84 task 12)"
```

---

## Task 13: LLMJob status page (custom change_view + 2s poll JS)

**Files:**
- Modify: `backend/apps/llm/admin.py`
- Create: `backend/apps/llm/templates/admin/llm/llmjob/change_form.html`
- Modify: `backend/apps/llm/tests/test_admin_jobs.py`

- [ ] **Step 1: Write failing test**

Append to `backend/apps/llm/tests/test_admin_jobs.py`:

```python
@pytest.mark.django_db
def test_status_endpoint_returns_json_with_progress(client, superuser):
    job = make_job(status=LLMJob.Status.RUNNING)
    prompt = make_prompt()
    make_call(job=job, prompt_version=prompt.active_version)
    client.force_login(superuser)
    resp = client.get(reverse("admin:llm_llmjob_status", args=[job.pk]))
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["status"] == "RUNNING"
    assert payload["calls_count"] == 1
    assert "total_cost_usd" in payload


@pytest.mark.django_db
def test_status_page_renders_for_superuser(client, superuser):
    job = make_job()
    client.force_login(superuser)
    resp = client.get(reverse("admin:llm_llmjob_change", args=[job.pk]))
    assert resp.status_code == 200
    # Custom template includes the poll script marker.
    assert b"data-llm-job-status" in resp.content
```

- [ ] **Step 2: Run to verify failure**

Run: `docker compose exec backend pytest apps/llm/tests/test_admin_jobs.py -v -k "status"`
Expected: FAIL — endpoint not registered, custom template missing.

- [ ] **Step 3: Add custom URL + status endpoint to LLMJobAdmin**

Edit `backend/apps/llm/admin.py`. Inside `LLMJobAdmin`, add:

```python
    change_form_template = "admin/llm/llmjob/change_form.html"

    def get_urls(self):
        urls = super().get_urls()
        custom = [
            path("<int:job_id>/status/",
                 self.admin_site.admin_view(self.status_view),
                 name="llm_llmjob_status"),
        ]
        return custom + urls

    def status_view(self, request, job_id: int):
        job = get_object_or_404(LLMJob, pk=job_id)
        calls = list(job.calls.all().values(
            "pk", "model", "success", "error_type", "input_tokens",
            "output_tokens", "duration_ms", "cost_usd",
        ))
        for c in calls:
            c["cost_usd"] = (
                f"${c['cost_usd']}"
                if _user_can_view_costs(request.user) else "—"
            )
        return JsonResponse({
            "status": job.status,
            "calls_count": len(calls),
            "calls": calls,
            "total_input_tokens": job.total_input_tokens,
            "total_output_tokens": job.total_output_tokens,
            "total_cost_usd": (
                f"${job.total_cost_usd}"
                if _user_can_view_costs(request.user) else "—"
            ),
            "result_url": _result_url(job),
            "error_message": job.error_message,
            "started_at": job.started_at.isoformat() if job.started_at else None,
            "finished_at": job.finished_at.isoformat() if job.finished_at else None,
        })


def _result_url(job: LLMJob) -> str | None:
    if not (job.result_content_type_id and job.result_object_id):
        return None
    ct = job.result_content_type
    try:
        return reverse(
            f"admin:{ct.app_label}_{ct.model}_change",
            args=[job.result_object_id],
        )
    except Exception:
        return None
```

Note: `JsonResponse` is already imported at the top of admin.py from Django (we added it in step 3 of task 11). Confirm the import block has `from django.http import JsonResponse`.

- [ ] **Step 4: Add the custom template**

`backend/apps/llm/templates/admin/llm/llmjob/change_form.html`:

```html
{% extends "admin/change_form.html" %}
{% block field_sets %}
  {{ block.super }}

  <div class="module" data-llm-job-status data-job-id="{{ original.pk }}"
       data-status-url="{% url 'admin:llm_llmjob_status' original.pk %}">
    <h2>Estado del job</h2>
    <p>Status: <strong id="llm-job-status">{{ original.status }}</strong>
       — elapsed: <span id="llm-job-elapsed">…</span></p>
    <p id="llm-job-result-link" style="display:none;">
      <a class="button" id="llm-job-result-anchor" href="#">Ver resultado →</a>
    </p>
    <table id="llm-job-calls-table"
           style="border-collapse:collapse; margin-top:1em; width:100%;">
      <thead>
        <tr>
          <th style="border:1px solid #ddd; padding:4px 8px;">#</th>
          <th style="border:1px solid #ddd; padding:4px 8px;">Modelo</th>
          <th style="border:1px solid #ddd; padding:4px 8px;">OK</th>
          <th style="border:1px solid #ddd; padding:4px 8px;">In</th>
          <th style="border:1px solid #ddd; padding:4px 8px;">Out</th>
          <th style="border:1px solid #ddd; padding:4px 8px;">ms</th>
          <th style="border:1px solid #ddd; padding:4px 8px;">$</th>
          <th style="border:1px solid #ddd; padding:4px 8px;">Error</th>
        </tr>
      </thead>
      <tbody></tbody>
    </table>
    <p>Total: <span id="llm-job-totals">…</span></p>
    <p id="llm-job-slow-warning" style="display:none; color:#a04;">
      Esto está tardando más de lo esperado. Si se queda en RUNNING > 10 min,
      se va a marcar como FAILED automáticamente.
    </p>
  </div>

  <script>
  (function () {
    const el = document.querySelector("[data-llm-job-status]");
    if (!el) return;
    const statusUrl = el.dataset.statusUrl;
    const startedAt = Date.now();
    const tbody = el.querySelector("#llm-job-calls-table tbody");
    let timer = null;

    async function tick() {
      const resp = await fetch(statusUrl, {credentials: "same-origin"});
      if (!resp.ok) return;
      const data = await resp.json();
      el.querySelector("#llm-job-status").textContent = data.status;
      el.querySelector("#llm-job-totals").textContent =
        `${data.total_input_tokens} in / ${data.total_output_tokens} out · ${data.total_cost_usd}`;
      tbody.innerHTML = data.calls.map((c, i) => `
        <tr>
          <td style="border:1px solid #ddd; padding:4px 8px;">${i + 1}</td>
          <td style="border:1px solid #ddd; padding:4px 8px;">${c.model}</td>
          <td style="border:1px solid #ddd; padding:4px 8px;">${c.success ? "✓" : "✗"}</td>
          <td style="border:1px solid #ddd; padding:4px 8px;">${c.input_tokens}</td>
          <td style="border:1px solid #ddd; padding:4px 8px;">${c.output_tokens}</td>
          <td style="border:1px solid #ddd; padding:4px 8px;">${c.duration_ms}</td>
          <td style="border:1px solid #ddd; padding:4px 8px;">${c.cost_usd}</td>
          <td style="border:1px solid #ddd; padding:4px 8px;">${c.error_type || ""}</td>
        </tr>`).join("");
      const elapsedSec = Math.floor((Date.now() - startedAt) / 1000);
      el.querySelector("#llm-job-elapsed").textContent = `${elapsedSec}s`;
      if (elapsedSec > 60) {
        el.querySelector("#llm-job-slow-warning").style.display = "block";
      }
      if (data.status === "SUCCESS" && data.result_url) {
        const link = el.querySelector("#llm-job-result-link");
        link.style.display = "block";
        link.querySelector("#llm-job-result-anchor").href = data.result_url;
      }
      if (data.status === "SUCCESS" || data.status === "FAILED") {
        clearInterval(timer);
      }
    }

    tick();
    timer = setInterval(tick, 2000);
  })();
  </script>
{% endblock %}
```

- [ ] **Step 5: Run tests**

Run: `docker compose exec backend pytest apps/llm/tests/test_admin_jobs.py -v`
Expected: 5 PASSED.

- [ ] **Step 6: Commit**

```bash
git add backend/apps/llm/admin.py \
  backend/apps/llm/templates/admin/llm/llmjob/ \
  backend/apps/llm/tests/test_admin_jobs.py
git commit -m "feat(llm): admin status page with 2s poll for LLMJob (DEV-84 task 13)"
```

---

## Task 14: `seed_prompts` management command + `parse_pdf_report.md` seed

**Files:**
- Create: `backend/apps/llm/management/__init__.py`
- Create: `backend/apps/llm/management/commands/__init__.py`
- Create: `backend/apps/llm/management/commands/seed_prompts.py`
- Create: `backend/apps/llm/seed/parse_pdf_report.md`
- Create: `backend/apps/llm/tests/test_seed_prompts.py`

- [ ] **Step 1: Write failing test**

`backend/apps/llm/tests/test_seed_prompts.py`:

```python
import pytest
from django.core.management import call_command

from apps.llm.models import Prompt, PromptVersion


@pytest.mark.django_db
def test_seed_prompts_creates_parse_pdf_report():
    call_command("seed_prompts")
    p = Prompt.objects.get(key="parse_pdf_report")
    assert p.active_version is not None
    assert p.active_version.response_format == "json_object"
    assert p.active_version.json_schema is not None
    assert "ParsedReport" in p.active_version.body or "report" in p.active_version.body.lower()


@pytest.mark.django_db
def test_seed_prompts_is_idempotent():
    call_command("seed_prompts")
    call_command("seed_prompts")
    p = Prompt.objects.get(key="parse_pdf_report")
    assert PromptVersion.objects.filter(prompt=p).count() == 1
```

- [ ] **Step 2: Run to verify failure**

Run: `docker compose exec backend pytest apps/llm/tests/test_seed_prompts.py -v`
Expected: FAIL — command does not exist.

- [ ] **Step 3: Create the seed prompt body**

`backend/apps/llm/seed/parse_pdf_report.md`:

```markdown
Sos un parser estructurado de reportes de marketing en PDF. Recibís las páginas
del PDF como imágenes y devolvés un JSON que cumple el schema de `ParsedReport`.

REGLAS DURAS:

1. Devolvés SOLO un objeto JSON. Nada de prosa, nada de ```json fences,
   nada de comentarios.
2. NUNCA referencies imágenes en el output. Todos los campos `imagen` deben
   quedar como string vacío. Las imágenes se agregan después manualmente.
3. Identificá el `kind` del reporte: "MENSUAL" si el reporte cubre un mes
   calendario, "FINAL" si es un cierre de campaña, "VALIDACION" si es una
   validación inicial. Si dudás, "MENSUAL".
4. `period_start` y `period_end` son ISO date YYYY-MM-DD. Si solo tenés mes,
   asumí día 1 al último día del mes.
5. `layout` debe listar los blocks en el mismo orden que aparecen en el PDF.
   Cada block referenciado en `layout` DEBE existir en `blocks`.
6. Tipos válidos de block (campo `type_name`):
   - TextImageBlock — un párrafo con título e (opcional) imagen
   - KpiGridBlock — grilla de KPIs (tiles con label/value/comparación)
   - MetricsTableBlock — tabla de métricas (filas con metric_name/value)
   - TopContentsBlock — top de posts (caption + métricas + thumbnail vacío)
   - TopCreatorsBlock — top de creadores (handle + métricas + thumbnail vacío)
   - AttributionTableBlock — tabla de OneLink attribution (handle + clicks + downloads)
   - ChartBlock — gráfico (con datapoints label/value)
7. Si una métrica numérica no aparece, devolvé `null` (no inventes).
8. `nombre` de cada block debe ser único dentro del reporte.

Filename de origen: {{ filename }}
```

- [ ] **Step 4: Implement `seed_prompts`**

`backend/apps/llm/management/__init__.py`: empty.
`backend/apps/llm/management/commands/__init__.py`: empty.

`backend/apps/llm/management/commands/seed_prompts.py`:

```python
"""Idempotent loader of seed prompts into the DB.

Reads .md files from apps/llm/seed/ and creates a Prompt + a v1 PromptVersion
for each. If the prompt already exists, does nothing (does NOT bump the version
or overwrite the body — explicit prompt edits go via admin).
"""
from pathlib import Path

from django.core.management.base import BaseCommand

from apps.llm.models import Prompt, PromptVersion

SEED_DIR = Path(__file__).resolve().parent.parent.parent / "seed"

# Per-prompt metadata not present in the .md file body.
PROMPT_META = {
    "parse_pdf_report": {
        "name": "Parse PDF Report",
        "description": (
            "Parser de PDFs legacy a ParsedReport (use case A, DEV-84). "
            "Recibe páginas como imágenes, devuelve JSON estructurado."
        ),
        "consumer": "reports.pdf_parser",
        "model_hint": "accounts/fireworks/models/kimi-k2-instruct-0905",
        "response_format": "json_object",
        "json_schema": {
            "type": "object",
            "properties": {
                "kind": {"type": "string"},
                "period_start": {"type": "string"},
                "period_end": {"type": "string"},
                "title": {"type": "string"},
                "intro_text": {"type": "string"},
                "conclusions_text": {"type": "string"},
                "layout": {
                    "type": "array",
                    "items": {
                        "type": "array",
                        "items": [
                            {"type": "integer"}, {"type": "string"},
                        ],
                        "minItems": 2, "maxItems": 2,
                    },
                },
                "blocks": {"type": "object"},
            },
            "required": ["kind", "period_start", "period_end", "title",
                         "layout", "blocks"],
        },
    },
}


class Command(BaseCommand):
    help = "Seed prompts from apps/llm/seed/*.md (idempotent)."

    def handle(self, *args, **options):
        created = skipped = 0
        for md in sorted(SEED_DIR.glob("*.md")):
            key = md.stem
            meta = PROMPT_META.get(key)
            if meta is None:
                self.stdout.write(self.style.WARNING(
                    f"skip {key}: no PROMPT_META entry"
                ))
                continue
            if Prompt.objects.filter(key=key).exists():
                skipped += 1
                continue
            p = Prompt.objects.create(
                key=key, name=meta["name"], description=meta["description"],
                consumer=meta["consumer"],
            )
            v1 = PromptVersion.objects.create(
                prompt=p, body=md.read_text(encoding="utf-8"),
                model_hint=meta["model_hint"],
                response_format=meta["response_format"],
                json_schema=meta["json_schema"],
                notes="seed v1",
            )
            p.active_version = v1
            p.save()
            created += 1

        self.stdout.write(self.style.SUCCESS(
            f"seed_prompts: created={created} skipped={skipped}"
        ))
```

- [ ] **Step 5: Run tests**

Run: `docker compose exec backend pytest apps/llm/tests/test_seed_prompts.py -v`
Expected: 2 PASSED.

- [ ] **Step 6: Commit**

```bash
git add backend/apps/llm/management/ backend/apps/llm/seed/ \
  backend/apps/llm/tests/test_seed_prompts.py
git commit -m "feat(llm): seed_prompts command + parse_pdf_report v1 (DEV-84 task 14)"
```

---

## Task 15: Use case A consumer — `pdf_parser._run_pdf_parse` handler

**Files:**
- Create: `backend/apps/reports/importers/pdf_parser.py`
- Create: `backend/tests/fixtures/llm_responses/parsed_report_minimal.json`
- Create: `backend/tests/fixtures/sample.pdf`
- Create: `backend/apps/reports/tests/test_pdf_parser.py`

- [ ] **Step 1: Create test fixtures**

`backend/tests/fixtures/llm_responses/parsed_report_minimal.json`:

```json
{
  "kind": "MENSUAL",
  "period_start": "2026-04-01",
  "period_end": "2026-04-30",
  "title": "Reporte mensual de prueba",
  "intro_text": "",
  "conclusions_text": "Cerramos bien.",
  "layout": [[1, "intro"]],
  "blocks": {
    "intro": {
      "type_name": "TextImageBlock",
      "nombre": "intro",
      "fields": {
        "title": "Bienvenida",
        "body": "Cuerpo del bloque.",
        "image_alt": "",
        "image_position": "top",
        "columns": 1,
        "imagen": ""
      },
      "items": []
    }
  }
}
```

For `backend/tests/fixtures/sample.pdf` we need a real 2-page PDF. Generate it inside the container so it's deterministic:

Run:
```
docker compose exec backend python -c "
from PIL import Image
import io
imgs = [Image.new('RGB', (200, 200), color=(i*120, 100, 100)) for i in (1, 2)]
buf = io.BytesIO()
imgs[0].save(buf, format='PDF', save_all=True, append_images=imgs[1:])
open('/app/tests/fixtures/sample.pdf', 'wb').write(buf.getvalue())
print('wrote sample.pdf')
"
```

Expected: `wrote sample.pdf` and a 2-page PDF in `backend/tests/fixtures/sample.pdf`.

- [ ] **Step 2: Write failing handler tests**

`backend/apps/reports/tests/test_pdf_parser.py`:

```python
"""Use case A — apps.reports.importers.pdf_parser tests."""
import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from apps.llm.client import ChatResponse
from apps.llm.models import LLMJob
from apps.llm.tests.factories import make_prompt
from apps.reports.importers import pdf_parser
from apps.reports.tests.factories import make_stage

FIXTURES = Path(__file__).resolve().parents[3] / "tests" / "fixtures"


def _seed_prompt():
    """Create the parse_pdf_report prompt the way seed_prompts would."""
    return make_prompt(
        key="parse_pdf_report",
        consumer="reports.pdf_parser",
        body="Sos un parser. {{ filename }}",
        model_hint="accounts/fireworks/models/kimi-k2-instruct-0905",
        response_format="json_object",
        json_schema={"type": "object", "required": ["title"]},
    )


def _fake_llm_response(parsed_dict):
    return ChatResponse(
        content=json.dumps(parsed_dict),
        input_tokens=100, output_tokens=200,
        duration_ms=42, raw=MagicMock(),
    )


@pytest.mark.django_db
def test_render_pdf_to_pngs_returns_one_per_page():
    pdf_bytes = (FIXTURES / "sample.pdf").read_bytes()
    pages = pdf_parser._render_pdf_to_pngs(pdf_bytes)
    assert len(pages) == 2
    assert all(isinstance(p, bytes) for p in pages)
    assert all(p[:4] == b"\x89PNG" for p in pages)  # PNG magic


@pytest.mark.django_db
@patch("apps.llm.services.client.chat")
def test_run_pdf_parse_creates_report_and_links_to_job(mock_chat, settings):
    settings.LLM_FIREWORKS_API_KEY = "sk-test"
    parsed = json.loads((FIXTURES / "llm_responses" / "parsed_report_minimal.json").read_text())
    mock_chat.return_value = _fake_llm_response(parsed)

    _seed_prompt()
    stage = make_stage()

    pdf_bytes = (FIXTURES / "sample.pdf").read_bytes()
    job = LLMJob.objects.create(
        consumer=pdf_parser.CONSUMER, handler_path=pdf_parser.HANDLER,
        input_metadata={
            "pdf_bytes_b64": __import__("base64").b64encode(pdf_bytes).decode(),
            "stage_id": stage.pk,
            "filename": "sample.pdf",
            "size_bytes": len(pdf_bytes),
        },
    )
    pdf_parser._run_pdf_parse(job)

    job.refresh_from_db()
    from apps.reports.models import Report
    report = Report.objects.get()
    assert report.title == "Reporte mensual de prueba"
    assert report.status == Report.Status.DRAFT
    assert job.result_object_id == report.pk
    assert job.output_metadata["report_id"] == report.pk
    assert job.output_metadata["blocks"] == 1
    assert job.output_metadata["title"] == report.title


@pytest.mark.django_db
def test_run_pdf_parse_invalid_pdf_raises(settings):
    settings.LLM_FIREWORKS_API_KEY = "sk-test"
    _seed_prompt()
    stage = make_stage()
    job = LLMJob.objects.create(
        consumer=pdf_parser.CONSUMER, handler_path=pdf_parser.HANDLER,
        input_metadata={
            "pdf_bytes_b64": __import__("base64").b64encode(b"not a pdf").decode(),
            "stage_id": stage.pk,
            "filename": "broken.pdf",
            "size_bytes": 9,
        },
    )
    with pytest.raises(Exception):
        pdf_parser._run_pdf_parse(job)
```

- [ ] **Step 3: Run to verify failure**

Run: `docker compose exec backend pytest apps/reports/tests/test_pdf_parser.py -v`
Expected: FAIL — module not found.

- [ ] **Step 4: Implement the consumer**

`backend/apps/reports/importers/pdf_parser.py`:

```python
"""Use case A: PDF → ParsedReport → Report DRAFT (DEV-84).

Two entrypoints:
  - submit_pdf(pdf_bytes, filename, stage_id, user) — admin-facing, creates
    an LLMJob and queues the Celery task.
  - _run_pdf_parse(job) — runs in the Celery worker. Reads the PDF from
    job.input_metadata, calls the LLM via apps.llm.services.run_prompt,
    builds the Report, links it via job.result GFK.

The PDF is stashed in input_metadata as base64 (small PDFs only — capped
at 50 MB by the form). Pulling from media storage is also viable but adds
a write/read round-trip; b64 keeps the job self-contained.
"""
from __future__ import annotations

import base64
import io
import logging

from apps.llm.models import LLMJob
from apps.llm.services import dispatch_job, run_prompt

from .builder import build_report
from .parsed import ParsedReport, ParsedBlock

logger = logging.getLogger(__name__)

CONSUMER = "reports.pdf_parser"
HANDLER = "apps.reports.importers.pdf_parser._run_pdf_parse"


def submit_pdf(*, pdf_bytes: bytes, filename: str, stage_id: int, user) -> LLMJob:
    """Called from the admin view. Creates an LLMJob and queues processing."""
    return dispatch_job(
        consumer=CONSUMER,
        handler_path=HANDLER,
        input_metadata={
            "pdf_bytes_b64": base64.b64encode(pdf_bytes).decode("ascii"),
            "stage_id": stage_id,
            "filename": filename,
            "size_bytes": len(pdf_bytes),
        },
        triggered_by=user,
    )


def _run_pdf_parse(job: LLMJob) -> None:
    """Runs inside the Celery worker."""
    pdf_b64 = job.input_metadata["pdf_bytes_b64"]
    stage_id = job.input_metadata["stage_id"]
    filename = job.input_metadata["filename"]
    pdf_bytes = base64.b64decode(pdf_b64)

    pages_png = _render_pdf_to_pngs(pdf_bytes)
    if not pages_png:
        raise ValueError("PDF inválido o vacío — 0 páginas renderizadas.")

    response = run_prompt(
        prompt_key="parse_pdf_report",
        inputs={"filename": filename},
        job=job,
        images=pages_png,
    )

    parsed = _parsed_report_from_dict(response.parsed, stage_id=stage_id)
    report = build_report(parsed, {}, stage_id=stage_id)

    job.result = report
    job.output_metadata = {
        "report_id": report.pk,
        "blocks": report.blocks.count(),
        "title": report.title,
    }
    job.save()


def _render_pdf_to_pngs(pdf_bytes: bytes) -> list[bytes]:
    """Render every PDF page to a PNG byte string. Requires poppler-utils."""
    from pdf2image import convert_from_bytes
    images = convert_from_bytes(pdf_bytes, fmt="png")
    out: list[bytes] = []
    for img in images:
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        out.append(buf.getvalue())
    return out


def _parsed_report_from_dict(d: dict, *, stage_id: int) -> ParsedReport:
    """Convert the LLM JSON output into the ParsedReport dataclass.

    The LLM mirrors the ParsedReport shape directly, so this is mostly a
    1:1 copy with the tuple casting that JSON loses.
    """
    from datetime import date as _date
    blocks = {
        nombre: ParsedBlock(
            type_name=b["type_name"], nombre=nombre,
            fields=b.get("fields", {}), items=b.get("items", []),
        )
        for nombre, b in d["blocks"].items()
    }
    return ParsedReport(
        stage_id=stage_id,
        kind=d["kind"],
        period_start=_date.fromisoformat(d["period_start"]),
        period_end=_date.fromisoformat(d["period_end"]),
        title=d["title"],
        intro_text=d.get("intro_text", ""),
        conclusions_text=d.get("conclusions_text", ""),
        layout=[(int(o), n) for o, n in d["layout"]],
        blocks=blocks,
    )
```

- [ ] **Step 5: Register the handler in `apps/llm/handlers.py` (already done in task 9 — verify)**

Open `backend/apps/llm/handlers.py` and confirm:

```python
REGISTRY: dict[str, str] = {
    "reports.pdf_parser": "apps.reports.importers.pdf_parser._run_pdf_parse",
}
```

- [ ] **Step 6: Run tests**

Run: `docker compose exec backend pytest apps/reports/tests/test_pdf_parser.py -v`
Expected: 3 PASSED.

- [ ] **Step 7: Commit**

```bash
git add backend/apps/reports/importers/pdf_parser.py \
  backend/apps/reports/tests/test_pdf_parser.py \
  backend/tests/fixtures/llm_responses/ \
  backend/tests/fixtures/sample.pdf
git commit -m "feat(reports): pdf_parser handler creates Report from LLM output (DEV-84 task 15)"
```

---

## Task 16: Admin — "Importar desde PDF (AI)" view + form + template + button

**Files:**
- Modify: `backend/apps/reports/admin.py`
- Modify: `backend/apps/reports/templates/admin/reports/report/change_list.html`
- Create: `backend/apps/reports/templates/admin/reports/report/import_pdf.html`
- Create: `backend/apps/reports/importers/pdf_form.py`
- Modify: `backend/apps/reports/tests/test_pdf_parser.py`

- [ ] **Step 1: Write failing admin test**

Append to `backend/apps/reports/tests/test_pdf_parser.py`:

```python
import io as _io

from django.contrib.auth import get_user_model
from django.urls import reverse


@pytest.fixture
def superuser(db):
    return get_user_model().objects.create_superuser(
        email="su-pdf@x.com", password="pass",
    )


@pytest.mark.django_db
def test_import_pdf_form_renders(client, superuser):
    client.force_login(superuser)
    resp = client.get(reverse("admin:reports_report_import_pdf"))
    assert resp.status_code == 200
    assert b"Importar desde PDF" in resp.content
    assert b"<input type=\"file\"" in resp.content


@pytest.mark.django_db
@patch("apps.llm.services.run_llm_job.delay")
def test_import_pdf_submit_creates_job_and_redirects(mock_delay, client, superuser, settings):
    settings.LLM_FIREWORKS_API_KEY = "sk-test"
    _seed_prompt()
    stage = make_stage()
    client.force_login(superuser)

    pdf_bytes = (FIXTURES / "sample.pdf").read_bytes()
    resp = client.post(
        reverse("admin:reports_report_import_pdf"),
        {
            "client": stage.campaign.brand.client_id,
            "brand": stage.campaign.brand_id,
            "campaign": stage.campaign_id,
            "stage": stage.pk,
            "file": _io.BytesIO(pdf_bytes),
        },
        format="multipart",
    )

    # Form fields use FileField; we need SimpleUploadedFile semantics.
```

The above test sketch is incomplete — Django test client expects `SimpleUploadedFile`. Replace the body with this complete version:

```python
@pytest.mark.django_db
@patch("apps.llm.services.run_llm_job.delay")
def test_import_pdf_submit_creates_job_and_redirects(mock_delay, client, superuser, settings):
    from django.core.files.uploadedfile import SimpleUploadedFile
    settings.LLM_FIREWORKS_API_KEY = "sk-test"
    _seed_prompt()
    stage = make_stage()
    client.force_login(superuser)

    pdf_bytes = (FIXTURES / "sample.pdf").read_bytes()
    upload = SimpleUploadedFile("sample.pdf", pdf_bytes,
                                content_type="application/pdf")

    resp = client.post(
        reverse("admin:reports_report_import_pdf"),
        {
            "client": stage.campaign.brand.client_id,
            "brand": stage.campaign.brand_id,
            "campaign": stage.campaign_id,
            "stage": stage.pk,
            "file": upload,
        },
    )
    assert resp.status_code in (302, 303)
    # Redirected to the LLMJob status page.
    assert "/admin/llm/llmjob/" in resp.url
    assert mock_delay.called


@pytest.mark.django_db
def test_changelist_has_pdf_import_button(client, superuser):
    client.force_login(superuser)
    resp = client.get(reverse("admin:reports_report_changelist"))
    assert resp.status_code == 200
    assert b"Importar desde PDF (AI)" in resp.content
```

- [ ] **Step 2: Run to verify failure**

Run: `docker compose exec backend pytest apps/reports/tests/test_pdf_parser.py -v -k "import_pdf or changelist"`
Expected: FAIL — URL/view/button not present.

- [ ] **Step 3: Add the form**

`backend/apps/reports/importers/pdf_form.py`:

```python
"""Form for the PDF importer (DEV-84). Mirrors ImportReportForm but for .pdf only."""
from django import forms
from django.core.validators import FileExtensionValidator

from apps.campaigns.models import Campaign, Stage
from apps.tenants.models import Brand, Client


MAX_PDF_SIZE = 50 * 1024 * 1024  # 50 MB


class ImportPdfForm(forms.Form):
    client = forms.ModelChoiceField(
        queryset=Client.objects.order_by("name"), label="Cliente",
    )
    brand = forms.ModelChoiceField(
        queryset=Brand.objects.select_related("client").order_by("name"),
        label="Brand",
    )
    campaign = forms.ModelChoiceField(
        queryset=Campaign.objects.select_related("brand").order_by("name"),
        label="Campaña",
    )
    stage = forms.ModelChoiceField(
        queryset=Stage.objects.select_related("campaign__brand__client").order_by(
            "campaign__name", "order",
        ),
        label="Etapa",
    )
    file = forms.FileField(
        label="PDF del reporte legacy",
        validators=[FileExtensionValidator(allowed_extensions=["pdf"])],
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name in ("client", "brand", "campaign", "stage"):
            attrs = self.fields[name].widget.attrs
            attrs["class"] = (attrs.get("class", "") + " report-import-cascade").strip()
            attrs["data-cascade-level"] = name

    def clean_file(self):
        f = self.cleaned_data["file"]
        if f.size > MAX_PDF_SIZE:
            raise forms.ValidationError(
                f"PDF muy grande ({f.size // (1024 * 1024)} MB). "
                f"Máximo: {MAX_PDF_SIZE // (1024 * 1024)} MB."
            )
        return f

    def clean(self):
        cleaned = super().clean()
        client = cleaned.get("client")
        brand = cleaned.get("brand")
        campaign = cleaned.get("campaign")
        stage = cleaned.get("stage")
        if brand and client and brand.client_id != client.pk:
            self.add_error("brand", "El brand no pertenece al cliente elegido.")
        if campaign and brand and campaign.brand_id != brand.pk:
            self.add_error("campaign", "La campaña no pertenece al brand elegido.")
        if stage and campaign and stage.campaign_id != campaign.pk:
            self.add_error("stage", "La etapa no pertenece a la campaña elegida.")
        return cleaned
```

- [ ] **Step 4: Add the URL + view to ReportAdmin**

Edit `backend/apps/reports/admin.py`. In the imports section near the top, add:

```python
from .importers.pdf_form import ImportPdfForm
from .importers.pdf_parser import submit_pdf as submit_pdf_parser
```

Inside `ReportAdmin.get_urls()` (the `custom = [...]` list), add a new entry:

```python
            path(
                "import-pdf/",
                self.admin_site.admin_view(self.import_pdf_view),
                name="reports_report_import_pdf",
            ),
```

Add the view method to `ReportAdmin` (right after `import_view`):

```python
    def import_pdf_view(self, request):
        if not request.user.has_perm("reports.add_report"):
            return HttpResponse(status=403)
        if request.method == "POST":
            form = ImportPdfForm(request.POST, request.FILES)
            if form.is_valid():
                stage = form.cleaned_data["stage"]
                upload = form.cleaned_data["file"]
                logger.info(
                    "report_pdf_import_started",
                    extra={
                        "user_id": request.user.pk,
                        "stage_id": stage.pk,
                        "filename": upload.name,
                        "size": upload.size,
                    },
                )
                job = submit_pdf_parser(
                    pdf_bytes=upload.read(),
                    filename=upload.name,
                    stage_id=stage.pk,
                    user=request.user,
                )
                return redirect(reverse(
                    "admin:llm_llmjob_change", args=[job.pk],
                ))
        else:
            form = ImportPdfForm()

        return render(request, "admin/reports/report/import_pdf.html", {
            **self.admin_site.each_context(request),
            "form": form,
            "opts": self.model._meta,
        })
```

- [ ] **Step 5: Add the changelist button**

Edit `backend/apps/reports/templates/admin/reports/report/change_list.html`, add a third `<li>` before `{{ block.super }}`:

```html
  <li>
    <a href="{% url 'admin:reports_report_import_pdf' %}" class="addlink">
      🤖 Importar desde PDF (AI)
    </a>
  </li>
```

- [ ] **Step 6: Add the import_pdf template**

`backend/apps/reports/templates/admin/reports/report/import_pdf.html`:

```html
{% extends "admin/base_site.html" %}
{% load i18n admin_urls %}

{% block title %}Importar reporte desde PDF (AI) | {{ site_title|default:_("Django site admin") }}{% endblock %}

{% block breadcrumbs %}
  <div class="breadcrumbs">
    <a href="{% url 'admin:index' %}">{% trans "Home" %}</a>
    &rsaquo; <a href="{% url 'admin:app_list' app_label='reports' %}">Reports</a>
    &rsaquo; <a href="{% url 'admin:reports_report_changelist' %}">Reports</a>
    &rsaquo; Importar desde PDF (AI)
  </div>
{% endblock %}

{% block content %}
  <h1>🤖 Importar reporte desde PDF (AI)</h1>

  <p>
    Subí un PDF del reporte legacy. El sistema lo manda a Fireworks (Kimi K2
    vision), parsea el contenido y crea un Report en estado DRAFT que después
    podés revisar/editar/publicar como cualquier otro.
  </p>
  <p>
    <strong>Las imágenes se agregan después manualmente</strong> desde el admin
    del reporte — esta primera versión no extrae imágenes del PDF.
  </p>

  <form method="post" enctype="multipart/form-data">
    {% csrf_token %}
    <fieldset class="module aligned">
      {% for field in form %}
        <div class="form-row">
          {{ field.label_tag }}
          {{ field }}
          {% if field.help_text %}<div class="help">{{ field.help_text|safe }}</div>{% endif %}
          {% if field.errors %}
            <ul class="errorlist">
              {% for e in field.errors %}<li>{{ e }}</li>{% endfor %}
            </ul>
          {% endif %}
        </div>
      {% endfor %}
    </fieldset>
    <div class="submit-row">
      <input type="submit" class="default" value="Importar PDF">
    </div>
  </form>

  <script>
    (function () {
      const cascadeUrl = "{% url 'admin:reports_report_import_cascade' 'LEVEL' %}";
      const levels = ["client", "brand", "campaign", "stage"];
      const selects = {};
      levels.forEach(l => { selects[l] = document.querySelector(`select[name="${l}"]`); });

      function repopulate(select, results, placeholderText) {
        select.innerHTML = "";
        const placeholder = document.createElement("option");
        placeholder.value = ""; placeholder.textContent = placeholderText;
        select.appendChild(placeholder);
        results.forEach(r => {
          const opt = document.createElement("option");
          opt.value = r.id; opt.textContent = r.text;
          select.appendChild(opt);
        });
        select.disabled = results.length === 0;
      }

      async function reload(level, parentId) {
        if (!selects[level]) return;
        if (!parentId) { repopulate(selects[level], [], "— primero elegí el padre —"); return; }
        const url = cascadeUrl.replace("LEVEL", level) + "?parent=" + encodeURIComponent(parentId);
        const resp = await fetch(url, {credentials: "same-origin"});
        if (!resp.ok) return;
        const data = await resp.json();
        repopulate(selects[level], data.results, "— elegir —");
      }

      function onChange(parentLevel) {
        const childMap = {client: "brand", brand: "campaign", campaign: "stage"};
        const child = childMap[parentLevel];
        if (!child) return;
        reload(child, selects[parentLevel].value);
        const downstream = levels.slice(levels.indexOf(child) + 1);
        downstream.forEach(l => repopulate(selects[l], [], "— primero elegí el padre —"));
      }

      ["client", "brand", "campaign"].forEach(l => {
        if (!selects[l]) return;
        selects[l].addEventListener("change", () => onChange(l));
      });

      if (selects.client && !selects.client.value) {
        ["brand", "campaign", "stage"].forEach(l =>
          repopulate(selects[l], [], "— primero elegí el padre —")
        );
      }
    })();
  </script>
{% endblock %}
```

- [ ] **Step 7: Run tests**

Run:
```
docker compose exec backend pytest apps/reports/tests/test_pdf_parser.py apps/llm/tests/ -v
docker compose exec backend pytest backend/tests/unit/test_reports_admin_import.py -v
```
Expected: all PASSED (the second command verifies we didn't break DEV-83 endpoints).

- [ ] **Step 8: Commit**

```bash
git add backend/apps/reports/admin.py \
  backend/apps/reports/importers/pdf_form.py \
  backend/apps/reports/templates/admin/reports/report/change_list.html \
  backend/apps/reports/templates/admin/reports/report/import_pdf.html \
  backend/apps/reports/tests/test_pdf_parser.py
git commit -m "feat(reports): admin import-from-PDF (AI) view + button (DEV-84 task 16)"
```

---

## Task 17: E2E Playwright smoke (mocks Fireworks via `page.route()`)

**Files:**
- Create: `frontend/tests/admin-import-pdf.spec.ts`

- [ ] **Step 1: Write the smoke test**

`frontend/tests/admin-import-pdf.spec.ts`:

```typescript
import { test, expect } from "@playwright/test";
import * as fs from "fs";
import * as path from "path";

/**
 * Smoke for the PDF importer admin view (DEV-84).
 *
 * Requires a superuser to exist (same convention as admin-import.spec.ts).
 * Mocks the Fireworks endpoint via page.route — no real LLM call.
 */

const ADMIN_BASE = process.env.ADMIN_BASE_URL || "http://localhost:8000";
const ADMIN_USER = process.env.ADMIN_SUPERUSER_EMAIL || "admin@chirri.local";
const ADMIN_PASS = process.env.ADMIN_SUPERUSER_PASSWORD || "admin";

const PARSED = {
  kind: "MENSUAL",
  period_start: "2026-04-01",
  period_end: "2026-04-30",
  title: "Reporte E2E PDF",
  intro_text: "",
  conclusions_text: "OK",
  layout: [[1, "intro"]],
  blocks: {
    intro: {
      type_name: "TextImageBlock",
      nombre: "intro",
      fields: {
        title: "Hola", body: "Body", image_alt: "",
        image_position: "top", columns: 1, imagen: "",
      },
      items: [],
    },
  },
};

test.describe("Admin import PDF (AI) smoke", () => {
  test("superuser sube un PDF, ve el job pollear, y aterriza en el Report", async ({ page }) => {
    // 1) Mock Fireworks BEFORE login (page.route persists across nav).
    await page.route("**/api.fireworks.ai/**", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          id: "x", object: "chat.completion", created: 0, model: "kimi",
          choices: [{
            index: 0, finish_reason: "stop",
            message: { role: "assistant", content: JSON.stringify(PARSED) },
          }],
          usage: { prompt_tokens: 100, completion_tokens: 200, total_tokens: 300 },
        }),
      });
    });

    // 2) Login.
    const loginResp = await page.goto(`${ADMIN_BASE}/admin/login/?next=/admin/reports/report/import-pdf/`);
    if (loginResp && loginResp.status() >= 500) test.skip(true, "Admin no disponible");
    const usernameField = page.locator("input#id_username, input[name=username]");
    if (await usernameField.count() === 0) test.skip(true, "Login form missing");
    await usernameField.fill(ADMIN_USER);
    await page.locator("input[name=password]").fill(ADMIN_PASS);
    await page.locator("input[type=submit]").click();
    if (page.url().includes("/login/")) test.skip(true, "No superuser configured");

    // 3) Form should be visible.
    await expect(page.getByRole("heading", { name: /Importar reporte desde PDF/i })).toBeVisible();

    // 4) Pick the first available stage (cascade Client → Brand → Campaign → Stage).
    const clientSelect = page.locator("select[name=client]");
    await clientSelect.selectOption({ index: 1 });
    await page.locator("select[name=brand] option:not([value=''])").first().waitFor();
    await page.locator("select[name=brand]").selectOption({ index: 1 });
    await page.locator("select[name=campaign] option:not([value=''])").first().waitFor();
    await page.locator("select[name=campaign]").selectOption({ index: 1 });
    await page.locator("select[name=stage] option:not([value=''])").first().waitFor();
    await page.locator("select[name=stage]").selectOption({ index: 1 });

    // 5) Upload a tiny PDF generated on the fly.
    const tmpPdf = path.join(__dirname, "tmp-sample.pdf");
    if (!fs.existsSync(tmpPdf)) {
      // Minimal 1-page PDF (hand-crafted, valid).
      fs.writeFileSync(tmpPdf, Buffer.from(
        "%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n" +
        "2 0 obj<</Type/Pages/Count 1/Kids[3 0 R]>>endobj\n" +
        "3 0 obj<</Type/Page/Parent 2 0 R/MediaBox[0 0 100 100]>>endobj\n" +
        "xref\n0 4\n0000000000 65535 f \n0000000009 00000 n \n" +
        "0000000053 00000 n \n0000000098 00000 n \n" +
        "trailer<</Size 4/Root 1 0 R>>\nstartxref\n149\n%%EOF\n",
        "binary",
      ));
    }
    await page.locator("input[type=file]").setInputFiles(tmpPdf);
    await page.locator("input[type=submit]").click();

    // 6) Should land on /admin/llm/llmjob/<id>/
    await expect(page).toHaveURL(/\/admin\/llm\/llmjob\/\d+\/$/);

    // 7) Wait for SUCCESS (CELERY_TASK_ALWAYS_EAGER in dev makes this fast).
    await expect(page.locator("#llm-job-status")).toHaveText(/SUCCESS|FAILED/, {
      timeout: 30_000,
    });
    await expect(page.locator("#llm-job-status")).toHaveText("SUCCESS");

    // 8) "Ver resultado →" link visible and points to the new report.
    await expect(page.locator("#llm-job-result-link")).toBeVisible();
    await expect(page.locator("#llm-job-result-anchor"))
      .toHaveAttribute("href", /\/admin\/reports\/report\/\d+\/change\/$/);
  });
});
```

- [ ] **Step 2: Run the smoke test (skipped automatically if no superuser)**

Run: `npm run test:e2e:smoke`
Expected: PASS (or SKIPPED if no superuser exists in dev). If the dev stack has a superuser configured, the test should pass end-to-end.

- [ ] **Step 3: Commit**

```bash
git add frontend/tests/admin-import-pdf.spec.ts
git commit -m "test(e2e): smoke for admin PDF import via mocked Fireworks (DEV-84 task 17)"
```

---

## Task 18: Docs — README section + ENV var + link the spec

**Files:**
- Modify: `README.md`
- Modify: `docs/ENV.md` (create if absent)
- Modify: `backend/apps/llm/__init__.py` (export public surface)

- [ ] **Step 1: Export public surface from `apps.llm`**

Edit `backend/apps/llm/__init__.py`:

```python
default_app_config = "apps.llm.apps.LlmConfig"

# Public surface — consumers should import from here only.
# (services / models, NOT client / pricing / tasks / handlers.)
```

The actual exports stay in `services` and `models` — we don't re-export at the package root because Django's app registry doesn't tolerate eager model imports during settings load. The comment documents the boundary.

- [ ] **Step 2: README section**

Edit `README.md`. Find a sensible spot (e.g. after the deployment / commands section) and add:

```markdown
## AI integration (DEV-84)

`apps/llm/` provides the LLM infrastructure (provider-agnostic client,
prompt versioning in DB, audit log of calls/cost, async jobs via Celery).

### Use case A — PDF importer

Julián sube un PDF legacy desde `/admin/reports/report/` → click
"🤖 Importar desde PDF (AI)" → pick Cliente/Brand/Campaña/Etapa → upload.
El sistema crea un `LLMJob`, encolea Celery, parsea con Fireworks Kimi K2
vision, y crea un Report DRAFT.

### Setup

1. `LLM_FIREWORKS_API_KEY=...` en `.env` (ver `docs/ENV.md`).
2. `docker compose exec backend python manage.py seed_prompts` para cargar
   los prompts a la DB (idempotente).
3. `docker compose exec backend python manage.py migrate` si es la primera vez.

### Editar prompts

`/admin/llm/prompt/` → click el prompt → "Nueva versión" → edit body +
notes → guardar → "Set active" cuando estés listo. Diff side-by-side
disponible para comparar versiones.

### Spec & plan

- Spec: `docs/superpowers/specs/2026-04-25-llm-integration-design.md`
- Plan: `docs/superpowers/plans/2026-04-26-llm-integration.md`
```

- [ ] **Step 3: ENV.md**

Check whether `docs/ENV.md` exists:

Run: `ls docs/ENV.md 2>&1 || echo "missing"`

If missing, create `docs/ENV.md` with:

```markdown
# Environment variables

| Variable | Required | Default | Notes |
|---|---|---|---|
| `DJANGO_SECRET_KEY` | prod | (random per run in dev) | Required in production. |
| `POSTGRES_*` | yes | dev defaults | DB connection. |
| `REDIS_URL` | yes | `redis://redis:6379/0` | Celery broker + result backend. |
| `LLM_FIREWORKS_API_KEY` | for AI features | empty | Fireworks API key. Without it the PDF importer raises `LLMConfigError`. Tests are mocked so they pass without the key. |
| `LLM_MAX_TOKENS_PER_CALL` | no | `500000` | Hard cap per LLM call. |
| `LLM_MAX_COST_PER_JOB_USD` | no | `2.00` | Hard cap per LLM job (USD). |
```

If `docs/ENV.md` already exists, append the LLM rows to its table.

- [ ] **Step 4: Verify everything builds**

Run:
```
docker compose build backend
docker compose exec backend python manage.py check
docker compose exec backend python manage.py seed_prompts
docker compose exec backend pytest apps/llm/ apps/reports/tests/test_pdf_parser.py -v
```
Expected: build succeeds (poppler-utils installs), check passes, seed creates the prompt, all tests green.

- [ ] **Step 5: Commit**

```bash
git add README.md docs/ENV.md backend/apps/llm/__init__.py
git commit -m "docs(llm): README section + ENV docs for DEV-84 (DEV-84 task 18)"
```

---

## Acceptance verification (run all at the end before finishing-a-development-branch)

- [ ] `docker compose build` and `docker compose up -d` work cleanly.
- [ ] `docker compose exec backend python manage.py migrate` applies cleanly.
- [ ] `docker compose exec backend python manage.py seed_prompts` is idempotent.
- [ ] `docker compose exec backend pytest` — full unit suite green; coverage on `apps/llm/` ≥ 90%.
- [ ] `npm run test:e2e:smoke` — green (or skipped where no superuser).
- [ ] `dump_report_template` and `dump_report_example` still work (DEV-83 not regressed).
- [ ] Manual smoke (with valid `LLM_FIREWORKS_API_KEY`): upload a small real PDF, watch the job poll, see the Report appear.

If any of the above fail, fix in-place and re-run before opening the PR.

---

## Self-review (skill checklist, performed before saving)

**Spec coverage:**

| Spec section | Task |
|---|---|
| Architecture · `apps/llm/` skeleton | Task 1 |
| Data model · Prompt + PromptVersion | Task 2 |
| Data model · LLMJob + LLMCall | Task 3 |
| pricing.py | Task 4 |
| client.py with PROVIDERS registry | Task 5 |
| services.run_prompt happy path | Task 6 |
| services.run_prompt JSON validation + retry | Task 7 |
| services.run_prompt cost guardrails | Task 8 |
| services.dispatch_job + Celery tasks | Task 9 |
| Beat: mark_stuck_jobs_as_failed | Task 10 |
| Admin · Prompt CRUD + diff | Task 11 |
| Admin · LLMJob/LLMCall audit + cost permission | Task 12 |
| Admin · status page with poll | Task 13 |
| seed_prompts + parse_pdf_report.md | Task 14 |
| Consumer pdf_parser handler + image rendering | Task 15 |
| Admin import-pdf view + form + template + button | Task 16 |
| E2E smoke | Task 17 |
| README + ENV.md | Task 18 |

**Placeholder scan:** done. No "TBD", no "implement later", no "similar to Task N", no "add validation" without code.

**Type consistency:** `dispatch_job` takes keyword-only args (`consumer=`, `handler_path=`, `input_metadata=`, `triggered_by=`) consistently in tests and impl. `run_prompt` takes `prompt_key` (positional) + `inputs` (positional) + keyword-only extras. `submit_pdf` takes keyword-only args. Tests match impl.

**Spec deviations (intentional, all minor):**

- Spec says `build_report(parsed, images={}, stage_id=...)`. Real signature is `build_report(parsed, image_bytes, *, stage_id)` (positional 2nd arg). Plan calls it as `build_report(parsed, {}, stage_id=stage_id)`.
- Spec sketches retry as "1 retry on json error". Plan honors `LLM_DEFAULT_MAX_RETRIES = 1` (configurable) and the loop is correctness-equivalent.
- Spec stashes PDF in media; plan keeps it base64 in `input_metadata` for self-contained jobs (no media write/read race).

---

**Plan complete and saved to `docs/superpowers/plans/2026-04-26-llm-integration.md`. Two execution options:**

**1. Subagent-Driven (recommended)** — I dispatch a fresh subagent per task, review between tasks, fast iteration.

**2. Inline Execution** — Execute tasks in this session using executing-plans, batch execution with checkpoints.

**Which approach?**
