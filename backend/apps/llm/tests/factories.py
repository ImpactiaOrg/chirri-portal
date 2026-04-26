"""Factories for apps.llm tests."""
from decimal import Decimal

from apps.llm.models import LLMCall, LLMJob, Prompt, PromptVersion


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
