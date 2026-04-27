"""Use case A: PDF -> ParsedReport -> Report DRAFT (DEV-84).

Two entrypoints:
  - submit_pdf(pdf_bytes, filename, stage_id, user) - admin-facing, creates
    an LLMJob and queues the Celery task.
  - _run_pdf_parse(job) - runs in the Celery worker. Reads the PDF from
    job.input_metadata, calls the LLM via apps.llm.services.run_prompt,
    builds the Report, links it via job.result GFK.

The PDF is stashed in input_metadata as base64 (small PDFs only - capped
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
from .parsed import ParsedReport, ParsedSection, ParsedWidget

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
        "sections": report.sections.count(),
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

    Expected LLM JSON shape (Sections + Widgets):
    {
      "kind": "MENSUAL",
      "period_start": "2026-03-01",
      "period_end": "2026-03-31",
      "title": "...",
      "intro_text": "...",
      "conclusions_text": "...",
      "sections": [
        {
          "nombre": "kpis",
          "title": "KPIs del mes",
          "layout": "stack",
          "order": 1,
          "instructions": ""
        },
        ...
      ],
      "widgets": [
        {
          "type_name": "KpiGridWidget",
          "section_nombre": "kpis",
          "widget_orden": 1,
          "widget_title": "",
          "fields": {},
          "items": [
            {"label": "Reach", "value": "2840000", "unit": "", ...},
            ...
          ]
        },
        ...
      ]
    }
    """
    from datetime import date as _date

    sections = [
        ParsedSection(
            nombre=sec["nombre"],
            title=sec["title"],
            layout=sec.get("layout", "stack"),
            order=int(sec["order"]),
            instructions=sec.get("instructions", ""),
        )
        for sec in d.get("sections", [])
    ]

    widgets_by_section: dict[str, list[ParsedWidget]] = {}
    for w in d.get("widgets", []):
        pw = ParsedWidget(
            type_name=w["type_name"],
            section_nombre=w["section_nombre"],
            widget_orden=int(w.get("widget_orden", 1)),
            widget_title=w.get("widget_title", ""),
            fields=w.get("fields", {}),
            items=w.get("items", []),
        )
        widgets_by_section.setdefault(pw.section_nombre, []).append(pw)

    return ParsedReport(
        stage_id=stage_id,
        kind=d["kind"],
        period_start=_date.fromisoformat(d["period_start"]),
        period_end=_date.fromisoformat(d["period_end"]),
        title=d["title"],
        intro_text=d.get("intro_text", ""),
        conclusions_text=d.get("conclusions_text", ""),
        sections=sections,
        widgets_by_section=widgets_by_section,
        image_refs=set(),
    )
