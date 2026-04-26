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
