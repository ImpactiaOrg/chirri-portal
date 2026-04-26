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
    from apps.llm.models import Prompt
    with pytest.raises(Prompt.DoesNotExist):
        run_prompt(prompt_key="does-not-exist", inputs={})


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
