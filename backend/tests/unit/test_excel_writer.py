"""Smoke + shape tests del template writer y exporter (DEV-83 · Etapa 1).

No cubren el parser (Etapa 2). El foco es que el archivo que ve Julián
tenga las 10 hojas en orden, headers correctos, dropdowns en los enums
y que la hoja Instrucciones cubra A/B/C/D.
"""
from datetime import date, datetime, timezone
from decimal import Decimal
from io import BytesIO

import pytest
from openpyxl import load_workbook

from apps.reports.importers import schema as s
from apps.reports.importers.excel_exporter import export
from apps.reports.importers.excel_writer import build_template
from apps.reports.models import (
    AttributionTableBlock,
    ChartBlock,
    ChartDataPoint,
    ImageBlock,
    KpiGridBlock,
    KpiTile,
    MetricsTableBlock,
    MetricsTableRow,
    OneLinkAttribution,
    Report,
    TextImageBlock,
    TopContentsBlock,
    TopContentItem,
    TopCreatorsBlock,
    TopCreatorItem,
)
from apps.reports.tests.factories import make_stage


# ---------------------------------------------------------------------------
# Template writer — no DB
# ---------------------------------------------------------------------------
def test_template_has_10_sheets_in_order():
    buf = build_template()
    wb = load_workbook(buf)
    assert wb.sheetnames == s.SHEETS_IN_ORDER


def test_template_instrucciones_covers_llm_and_human_sections():
    wb = load_workbook(build_template())
    ws = wb[s.SHEET_INSTRUCCIONES]
    text = "\n".join(
        str(ws.cell(row=r, column=1).value or "")
        for r in range(1, ws.max_row + 1)
    )
    assert "A. Cómo llenar el Excel" in text
    assert "B. Cómo armar el ZIP" in text
    assert "C. Regenerar el template" in text
    assert "D. Para LLMs" in text
    # Contrato explícito para el LLM
    assert "nombre" in text
    assert ".jpg" in text and ".png" in text


def test_template_reporte_sheet_has_kv_rows_and_layout_header():
    wb = load_workbook(build_template())
    ws = wb[s.SHEET_REPORTE]

    # KV keys en columna A (marcadas con * los obligatorios)
    col_a = [str(ws.cell(row=r, column=1).value or "") for r in range(1, ws.max_row + 1)]
    assert any("tipo*" in v for v in col_a), "tipo debería estar marcado obligatorio"
    assert any("fecha_inicio*" in v for v in col_a)
    assert any("# Layout" in v for v in col_a)


def test_template_block_sheets_have_exact_headers():
    wb = load_workbook(build_template())
    for sheet_name, expected_headers in s.SHEET_HEADERS.items():
        ws = wb[sheet_name]
        actual = [ws.cell(row=1, column=c).value for c in range(1, len(expected_headers) + 1)]
        assert actual == expected_headers, f"{sheet_name}: headers mismatch"


def test_template_has_dropdown_on_tipo():
    wb = load_workbook(build_template())
    ws = wb[s.SHEET_REPORTE]
    assert ws.data_validations.count > 0, "Reporte debería tener al menos un dropdown"


def test_template_dropdowns_on_block_sheets_match_schema():
    wb = load_workbook(build_template())
    for (sheet_name, _header), _choices in s.DROPDOWNS.items():
        if sheet_name == s.SHEET_REPORTE:
            continue  # Reporte es key-value, validado arriba
        ws = wb[sheet_name]
        assert ws.data_validations.count > 0, (
            f"{sheet_name} debería tener al menos un dropdown"
        )


# ---------------------------------------------------------------------------
# Exporter — necesita DB
# ---------------------------------------------------------------------------
@pytest.fixture
def tiny_report(db):
    """Report con 1 block de cada tipo (sin imágenes reales, paths dummy)."""
    stage = make_stage()
    report = Report.objects.create(
        stage=stage,
        kind=Report.Kind.MENSUAL,
        period_start=date(2026, 4, 1),
        period_end=date(2026, 4, 30),
        title="Reporte tiny",
        intro_text="Intro de prueba",
        conclusions_text="Conclusiones de prueba",
        status=Report.Status.DRAFT,
        published_at=datetime(2026, 5, 2, 12, 0, tzinfo=timezone.utc),
    )

    TextImageBlock.objects.create(
        report=report, order=1, title="Intro", body="Body text",
        image_position="left", columns=1,
    )
    ImageBlock.objects.create(
        report=report, order=2, title="Hero",
        caption="Caption",
    )
    kpi = KpiGridBlock.objects.create(report=report, order=3, title="KPIs")
    KpiTile.objects.create(
        kpi_grid_block=kpi, order=1, label="Reach",
        value=Decimal("1000"), period_comparison=Decimal("5.0"),
    )
    KpiTile.objects.create(
        kpi_grid_block=kpi, order=2, label="Engagement",
        value=Decimal("5.5"), period_comparison=None,
    )

    mt = MetricsTableBlock.objects.create(
        report=report, order=4, title="Mes a mes", network=None,
    )
    MetricsTableRow.objects.create(
        metrics_table_block=mt, order=1, metric_name="reach",
        value=Decimal("500"), source_type="ORGANIC",
    )

    tc = TopContentsBlock.objects.create(
        report=report, order=5, title="Top posts",
        network="INSTAGRAM", period_label="abril", limit=6,
    )
    TopContentItem.objects.create(
        block=tc, order=1, caption="Post 1",
        source_type="ORGANIC", views=100, likes=10,
    )

    tcr = TopCreatorsBlock.objects.create(
        report=report, order=6, title="Top creators",
        network="INSTAGRAM", period_label="abril", limit=6,
    )
    TopCreatorItem.objects.create(
        block=tcr, order=1, handle="@test", views=200,
    )

    attr = AttributionTableBlock.objects.create(
        report=report, order=7, title="OneLink", show_total=True,
    )
    OneLinkAttribution.objects.create(
        attribution_block=attr, influencer_handle="@creator",
        clicks=100, app_downloads=25,
    )

    chart = ChartBlock.objects.create(
        report=report, order=8, title="Followers",
        network="INSTAGRAM", chart_type="bar",
    )
    ChartDataPoint.objects.create(
        chart_block=chart, order=1, label="Ene", value=Decimal("100"),
    )
    ChartDataPoint.objects.create(
        chart_block=chart, order=2, label="Feb", value=Decimal("120"),
    )

    return report


def test_exporter_returns_bytesio(tiny_report):
    buf = export(tiny_report)
    assert isinstance(buf, BytesIO)
    assert len(buf.getvalue()) > 0


def test_exporter_preserves_sheet_layout_from_template(tiny_report):
    """Shape = mismas hojas en el mismo orden que el template vacío."""
    wb = load_workbook(export(tiny_report))
    assert wb.sheetnames == s.SHEETS_IN_ORDER


def test_exporter_populates_reporte_kv_and_layout(tiny_report):
    wb = load_workbook(export(tiny_report))
    ws = wb[s.SHEET_REPORTE]

    # Recoger key-value — parar al entrar a la sección Layout
    kv = {}
    for r in range(2, ws.max_row + 1):
        key = ws.cell(row=r, column=1).value
        if isinstance(key, str) and key.startswith("# Layout"):
            break
        if isinstance(key, str) and key and not key.startswith("#"):
            kv[key.rstrip("*")] = ws.cell(row=r, column=2).value

    assert kv["tipo"] == "Mensual"
    assert kv["fecha_inicio"] == "01/04/2026"
    assert kv["fecha_fin"] == "30/04/2026"
    assert kv["titulo"] == "Reporte tiny"
    assert kv["intro"] == "Intro de prueba"
    assert kv["conclusiones"] == "Conclusiones de prueba"

    # Layout: 8 blocks, orden 1..8 con nombres `{prefix}_1`
    layout_rows = _read_layout(ws)
    assert len(layout_rows) == 8
    orders = [r["orden"] for r in layout_rows]
    assert orders == [1, 2, 3, 4, 5, 6, 7, 8]
    nombres = [r["nombre"] for r in layout_rows]
    expected = [
        "textimage_1", "imagen_1", "kpi_1", "metrics_1",
        "topcontents_1", "topcreators_1", "attribution_1", "chart_1",
    ]
    assert nombres == expected


def test_exporter_writes_kpi_tiles_denormalized(tiny_report):
    wb = load_workbook(export(tiny_report))
    rows = _read_tabular(wb[s.SHEET_KPIS], s.KPIS_HEADERS)
    assert len(rows) == 2
    # block_title repetido en cada row
    assert all(r["nombre"] == "kpi_1" for r in rows)
    assert all(r["block_title"] == "KPIs" for r in rows)
    assert rows[0]["label"] == "Reach"
    assert rows[0]["value"] == 1000.0
    assert rows[0]["period_comparison"] == 5.0
    # period_comparison=None en DB → celda vacía en xlsx (openpyxl la lee como None)
    assert rows[1]["period_comparison"] in (None, "")


def test_exporter_writes_chart_points(tiny_report):
    wb = load_workbook(export(tiny_report))
    rows = _read_tabular(wb[s.SHEET_CHARTS], s.CHARTS_HEADERS)
    assert len(rows) == 2
    assert rows[0]["nombre"] == "chart_1"
    assert rows[0]["chart_type"] == "bar"
    assert rows[0]["point_label"] == "Ene"
    assert rows[1]["point_label"] == "Feb"


def test_exporter_writes_textimage_and_imagen_one_row_per_block(tiny_report):
    wb = load_workbook(export(tiny_report))
    ti_rows = _read_tabular(wb[s.SHEET_TEXTIMAGE], s.TEXTIMAGE_HEADERS)
    im_rows = _read_tabular(wb[s.SHEET_IMAGENES], s.IMAGENES_HEADERS)
    assert len(ti_rows) == 1
    assert len(im_rows) == 1
    assert ti_rows[0]["nombre"] == "textimage_1"
    assert ti_rows[0]["image_position"] == "left"
    assert im_rows[0]["nombre"] == "imagen_1"
    assert im_rows[0]["caption"] == "Caption"


def test_exporter_empty_sheets_when_no_blocks_of_that_type(db):
    """Report sin ImageBlock → hoja Imagenes queda vacía (solo headers)."""
    stage = make_stage()
    report = Report.objects.create(
        stage=stage,
        kind=Report.Kind.MENSUAL,
        period_start=date(2026, 4, 1),
        period_end=date(2026, 4, 30),
        title="Sin images",
        status=Report.Status.DRAFT,
    )
    TextImageBlock.objects.create(report=report, order=1, title="Solo")

    wb = load_workbook(export(report))
    ws = wb[s.SHEET_IMAGENES]
    # Solo el header row
    rows = _read_tabular(ws, s.IMAGENES_HEADERS)
    assert rows == []


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _read_tabular(ws, headers: list[str]) -> list[dict]:
    out = []
    for r in range(2, ws.max_row + 1):
        if ws.cell(row=r, column=1).value in (None, ""):
            continue
        row = {h: ws.cell(row=r, column=i).value for i, h in enumerate(headers, start=1)}
        out.append(row)
    return out


def _read_layout(ws) -> list[dict]:
    """Lee la sección # Layout de la hoja Reporte."""
    header_row = None
    for r in range(1, ws.max_row + 1):
        if ws.cell(row=r, column=1).value == "orden":
            header_row = r
            break
    if header_row is None:
        return []
    out = []
    for r in range(header_row + 1, ws.max_row + 1):
        orden = ws.cell(row=r, column=1).value
        nombre = ws.cell(row=r, column=2).value
        if orden in (None, ""):
            continue
        out.append({"orden": orden, "nombre": nombre})
    return out
