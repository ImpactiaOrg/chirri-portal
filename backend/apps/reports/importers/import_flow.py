"""Orquestador: bytes + stage_id → Report creado o List[ImporterError] (DEV-83 · Etapa 2).

Compone bundle_reader + excel_parser + builder. Lo usan tanto la vista admin
como el command `validate_import` (ese último frena antes del builder).
"""
from __future__ import annotations

import logging

from apps.reports.models import Report

from .bundle_reader import read_bundle
from .builder import build_report
from .errors import ImporterError
from .excel_parser import parse

logger = logging.getLogger(__name__)


def import_bytes(
    data: bytes, filename: str, *, stage_id: int,
) -> tuple[Report | None, list[ImporterError]]:
    """Corre el pipeline completo. Si hay errores, devuelve (None, errors)."""
    xlsx_bytes, images, bundle_errors = read_bundle(data, filename=filename)
    if bundle_errors or xlsx_bytes is None:
        return None, bundle_errors

    parsed, parse_errors = parse(xlsx_bytes, available_images=set(images.keys()))
    if parse_errors or parsed is None:
        return None, parse_errors

    try:
        report = build_report(parsed, images, stage_id=stage_id)
    except Exception as exc:  # noqa: BLE001 — queremos capturar cualquier fallo del builder
        logger.exception(
            "report_import_builder_failed",
            extra={"stage_id": stage_id, "filename": filename},
        )
        return None, [ImporterError(
            sheet="(builder)", row=None, column=None,
            reason=f"Error inesperado al crear el report: {type(exc).__name__}",
        )]

    logger.info(
        "report_import_success",
        extra={
            "stage_id": stage_id, "filename": filename,
            "report_id": report.pk, "blocks": report.blocks.count(),
        },
    )
    return report, []


def validate_bytes(
    data: bytes, filename: str,
) -> list[ImporterError]:
    """Igual que `import_bytes` pero frena antes del builder (no toca DB)."""
    xlsx_bytes, images, bundle_errors = read_bundle(data, filename=filename)
    if bundle_errors or xlsx_bytes is None:
        return bundle_errors
    _parsed, parse_errors = parse(xlsx_bytes, available_images=set(images.keys()))
    return parse_errors
