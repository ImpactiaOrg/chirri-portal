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
