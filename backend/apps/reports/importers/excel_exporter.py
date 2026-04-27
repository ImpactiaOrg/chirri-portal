"""Exporter xlsx de un Report existente (post sections-widgets-redesign).

Genera un xlsx con la misma shape que el template vacío de `excel_writer`
pero poblado con la data de un Report real (sections + widgets).
"""
from __future__ import annotations

from decimal import Decimal
from io import BytesIO
from pathlib import PurePosixPath

from openpyxl.worksheet.worksheet import Worksheet

from apps.reports.models import (
    ChartWidget,
    ImageWidget,
    KpiGridWidget,
    Report,
    Section,
    TableWidget,
    TextImageWidget,
    TextWidget,
    TopContentsWidget,
    TopCreatorsWidget,
)

from . import schema as s
from .excel_writer import build_skeleton, to_bytes


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
def export(report: Report) -> BytesIO:
    """Serializa `report` al mismo xlsx que produciría el importer."""
    wb = build_skeleton()
    section_names = _assign_section_names(report)

    _populate_reporte(wb[s.SHEET_REPORTE], report)
    _populate_sections(wb[s.SHEET_SECTIONS], report, section_names)
    _populate_texts(wb[s.SHEET_TEXTS], report, section_names)
    _populate_images(wb[s.SHEET_IMAGES], report, section_names)
    _populate_textimages(wb[s.SHEET_TEXTIMAGES], report, section_names)
    _populate_kpigrids(wb[s.SHEET_KPIGRIDS], report, section_names)
    _populate_tables(wb[s.SHEET_TABLES], report, section_names)
    _populate_charts(wb[s.SHEET_CHARTS], report, section_names)
    _populate_topcontents(wb[s.SHEET_TOPCONTENTS], report, section_names)
    _populate_topcreators(wb[s.SHEET_TOPCREATORS], report, section_names)

    return to_bytes(wb)


# ---------------------------------------------------------------------------
# Section name assignment: section.pk → "section_N"
# ---------------------------------------------------------------------------
def _assign_section_names(report: Report) -> dict[int, str]:
    """Returns {section.pk: 'section_N'} where N counts in order."""
    names: dict[int, str] = {}
    for idx, section in enumerate(
        Section.objects.filter(report=report).order_by("order"), start=1
    ):
        names[section.pk] = f"section_{idx}"
    return names


# ---------------------------------------------------------------------------
# Per-sheet populators
# ---------------------------------------------------------------------------
def _populate_reporte(ws: Worksheet, report: Report) -> None:
    kv_values = {
        "tipo": s.KIND_LABELS.get(report.kind, report.kind),
        "fecha_inicio": _fmt_date(report.period_start),
        "fecha_fin": _fmt_date(report.period_end),
        "titulo": report.title,
        "intro": report.intro_text,
        "conclusiones": report.conclusions_text,
    }
    for idx, (key, _type, _required, _example) in enumerate(s.REPORTE_KV_ROWS, start=2):
        ws.cell(row=idx, column=2, value=kv_values.get(key, ""))


def _populate_sections(
    ws: Worksheet, report: Report, section_names: dict[int, str],
) -> None:
    for i, section in enumerate(
        Section.objects.filter(report=report).order_by("order"), start=2
    ):
        _write_row(ws, i, s.SECTIONS_HEADERS, {
            "nombre": section_names[section.pk],
            "title": section.title,
            "layout": section.layout,
            "order": section.order,
            "instructions": section.instructions,
        })


def _populate_texts(
    ws: Worksheet, report: Report, section_names: dict[int, str],
) -> None:
    row = 2
    for widget in TextWidget.objects.filter(section__report=report).order_by(
        "section__order", "order"
    ):
        _write_row(ws, row, s.TEXTS_HEADERS, {
            "section_nombre": section_names[widget.section_id],
            "widget_orden": widget.order,
            "widget_title": widget.title,
            "body": widget.body,
        })
        row += 1


def _populate_images(
    ws: Worksheet, report: Report, section_names: dict[int, str],
) -> None:
    row = 2
    for widget in ImageWidget.objects.filter(section__report=report).order_by(
        "section__order", "order"
    ):
        _write_row(ws, row, s.IMAGES_HEADERS, {
            "section_nombre": section_names[widget.section_id],
            "widget_orden": widget.order,
            "widget_title": widget.title,
            "imagen": _filename(widget.image),
            "image_alt": widget.image_alt,
            "caption": widget.caption,
        })
        row += 1


def _populate_textimages(
    ws: Worksheet, report: Report, section_names: dict[int, str],
) -> None:
    row = 2
    for widget in TextImageWidget.objects.filter(section__report=report).order_by(
        "section__order", "order"
    ):
        _write_row(ws, row, s.TEXTIMAGES_HEADERS, {
            "section_nombre": section_names[widget.section_id],
            "widget_orden": widget.order,
            "widget_title": widget.title,
            "body": widget.body,
            "imagen": _filename(widget.image),
            "image_alt": widget.image_alt,
            "image_position": widget.image_position,
            "columns": widget.columns,
        })
        row += 1


def _populate_kpigrids(
    ws: Worksheet, report: Report, section_names: dict[int, str],
) -> None:
    row = 2
    for widget in KpiGridWidget.objects.filter(section__report=report).order_by(
        "section__order", "order"
    ):
        for tile in widget.tiles.all().order_by("order"):
            _write_row(ws, row, s.KPIGRIDS_HEADERS, {
                "section_nombre": section_names[widget.section_id],
                "widget_orden": widget.order,
                "widget_title": widget.title,
                "tile_orden": tile.order,
                "label": tile.label,
                "value": _num(tile.value),
                "unit": tile.unit,
                "period_comparison": _num(tile.period_comparison),
                "period_comparison_label": tile.period_comparison_label,
            })
            row += 1


def _populate_tables(
    ws: Worksheet, report: Report, section_names: dict[int, str],
) -> None:
    row = 2
    for widget in TableWidget.objects.filter(section__report=report).order_by(
        "section__order", "order"
    ):
        for r in widget.rows.all().order_by("order"):
            cells_padded = list(r.cells) + [""] * (8 - len(r.cells))
            values = {
                "section_nombre": section_names[widget.section_id],
                "widget_orden": widget.order,
                "widget_title": widget.title,
                "widget_show_total": "TRUE" if widget.show_total else "FALSE",
                "row_orden": r.order,
                "is_header": "TRUE" if r.is_header else "FALSE",
            }
            for i, cell in enumerate(cells_padded[:8], start=1):
                values[f"cell_{i}"] = cell
            _write_row(ws, row, s.TABLES_HEADERS, values)
            row += 1


def _populate_charts(
    ws: Worksheet, report: Report, section_names: dict[int, str],
) -> None:
    row = 2
    for widget in ChartWidget.objects.filter(section__report=report).order_by(
        "section__order", "order"
    ):
        for p in widget.data_points.all().order_by("order"):
            _write_row(ws, row, s.CHARTS_HEADERS, {
                "section_nombre": section_names[widget.section_id],
                "widget_orden": widget.order,
                "widget_title": widget.title,
                "widget_network": s.NETWORK_LABELS.get(widget.network, ""),
                "chart_type": widget.chart_type,
                "point_orden": p.order,
                "point_label": p.label,
                "point_value": _num(p.value),
            })
            row += 1


def _populate_topcontents(
    ws: Worksheet, report: Report, section_names: dict[int, str],
) -> None:
    row = 2
    for widget in TopContentsWidget.objects.filter(section__report=report).order_by(
        "section__order", "order"
    ):
        for item in widget.items.all().order_by("order"):
            _write_row(ws, row, s.TOPCONTENTS_HEADERS, {
                "section_nombre": section_names[widget.section_id],
                "widget_orden": widget.order,
                "widget_title": widget.title,
                "widget_network": s.NETWORK_LABELS.get(widget.network, ""),
                "widget_period_label": widget.period_label,
                "item_orden": item.order,
                "imagen": _filename(item.thumbnail),
                "caption": item.caption,
                "post_url": item.post_url,
                "source_type": s.SOURCE_TYPE_LABELS.get(item.source_type, ""),
                "views": item.views,
                "likes": item.likes,
                "comments": item.comments,
                "shares": item.shares,
                "saves": item.saves,
            })
            row += 1


def _populate_topcreators(
    ws: Worksheet, report: Report, section_names: dict[int, str],
) -> None:
    row = 2
    for widget in TopCreatorsWidget.objects.filter(section__report=report).order_by(
        "section__order", "order"
    ):
        for item in widget.items.all().order_by("order"):
            _write_row(ws, row, s.TOPCREATORS_HEADERS, {
                "section_nombre": section_names[widget.section_id],
                "widget_orden": widget.order,
                "widget_title": widget.title,
                "widget_network": s.NETWORK_LABELS.get(widget.network, ""),
                "widget_period_label": widget.period_label,
                "item_orden": item.order,
                "imagen": _filename(item.thumbnail),
                "handle": item.handle,
                "post_url": item.post_url,
                "views": item.views,
                "likes": item.likes,
                "comments": item.comments,
                "shares": item.shares,
            })
            row += 1


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _write_row(
    ws: Worksheet, row: int, headers: list[str], values: dict,
) -> None:
    for col_idx, header in enumerate(headers, start=1):
        ws.cell(row=row, column=col_idx, value=values.get(header, ""))


def _filename(imagefield) -> str:
    """Extrae solo el nombre del archivo de un ImageField (sin path)."""
    if not imagefield or not imagefield.name:
        return ""
    return PurePosixPath(imagefield.name).name


def _num(value):
    """Normaliza Decimal/None/0 para Excel: None → '', Decimal → float."""
    if value is None:
        return ""
    if isinstance(value, Decimal):
        return float(value)
    return value


def _fmt_date(d) -> str:
    if d is None:
        return ""
    return d.strftime("%d/%m/%Y")
