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
