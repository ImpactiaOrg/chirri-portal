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
