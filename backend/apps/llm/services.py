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

    if job is None:
        job = LLMJob.objects.create(
            consumer=prompt.consumer or "ad_hoc",
            handler_path="apps.llm.services.run_prompt",
            status=LLMJob.Status.RUNNING,
        )

    rendered = _jinja.from_string(pv.body).render(**inputs)
    messages = _build_messages(rendered, images=images)

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

    response_format = (
        {"type": "json_object"} if pv.response_format == "json_object" else None
    )

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
