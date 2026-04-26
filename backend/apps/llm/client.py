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
