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
