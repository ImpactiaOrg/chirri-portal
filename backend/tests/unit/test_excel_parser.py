"""Parser xlsx → ParsedReport + builder → Report (DEV-83 · Etapa 2).

Incluye un roundtrip pesado (writer → exporter → parser → builder)
que garantiza que las 4 piezas (template, export, parse, build) se
mantienen consistentes ante cualquier cambio de schema.
"""
from datetime import date, datetime, timezone
from decimal import Decimal
from io import BytesIO

import pytest
from openpyxl import load_workbook

from apps.reports.importers import schema as s
from apps.reports.importers.builder import build_report
from apps.reports.importers.excel_exporter import export
from apps.reports.importers.excel_parser import parse
from apps.reports.importers.excel_writer import build_template, to_bytes
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
    TopContentItem,
    TopContentsBlock,
    TopCreatorItem,
    TopCreatorsBlock,
)
from apps.reports.tests.factories import make_stage


# ---------------------------------------------------------------------------
# Basic parse tests (no DB)
# ---------------------------------------------------------------------------
def test_parse_empty_template_returns_errors_for_missing_required():
    parsed, errors = parse(build_template().getvalue())
    assert parsed is None
    # Faltan tipo, fecha_inicio, fecha_fin
    required_keys = {e.column for e in errors if e.sheet == s.SHEET_REPORTE}
    assert "tipo" in required_keys
    assert "fecha_inicio" in required_keys
    assert "fecha_fin" in required_keys


def test_parse_missing_sheet_fatal():
    wb = load_workbook(build_template())
    wb.remove(wb["Kpis"])
    buf = BytesIO()
    wb.save(buf)
    parsed, errors = parse(buf.getvalue())
    assert parsed is None
    assert any(e.sheet == "Kpis" and e.reason == "hoja faltante" for e in errors)


def test_parse_corrupt_xlsx():
    parsed, errors = parse(b"not-an-xlsx")
    assert parsed is None
    assert errors[0].sheet == "(workbook)"


def test_parse_invalid_date():
    xlsx = _fill_minimal_xlsx(fecha_inicio="no-es-fecha")
    parsed, errors = parse(xlsx)
    assert parsed is None
    assert any(e.column == "fecha_inicio" and "inválida" in e.reason for e in errors)


def test_parse_invalid_kind_enum():
    xlsx = _fill_minimal_xlsx(tipo="Trimestral")  # no está en enum
    parsed, errors = parse(xlsx)
    assert parsed is None
    assert any(e.column == "tipo" and "'Trimestral' inválido" in e.reason for e in errors)


def test_parse_nombre_duplicated_across_sheets():
    """Un mismo nombre en dos hojas distintas → error de uniqueness cross-sheet."""
    wb = load_workbook(build_template())
    _fill_scalars(wb[s.SHEET_REPORTE])

    ws_ti = wb[s.SHEET_TEXTIMAGE]
    ws_ti.cell(row=2, column=1, value="duplicado")
    ws_ti.cell(row=2, column=2, value="Intro")

    ws_img = wb[s.SHEET_IMAGENES]
    ws_img.cell(row=2, column=1, value="duplicado")
    ws_img.cell(row=2, column=2, value="Hero")
    ws_img.cell(row=2, column=4, value="hero.jpg")  # imagen obligatoria

    _add_layout(wb[s.SHEET_REPORTE], [(1, "duplicado")])

    buf = BytesIO()
    wb.save(buf)
    parsed, errors = parse(buf.getvalue(), available_images={"hero.jpg"})
    assert parsed is None
    assert any("duplicado" in e.reason.lower() for e in errors)


def test_parse_layout_references_unknown_nombre():
    wb = load_workbook(build_template())
    _fill_scalars(wb[s.SHEET_REPORTE])
    _add_layout(wb[s.SHEET_REPORTE], [(1, "fantasma")])
    buf = BytesIO()
    wb.save(buf)
    parsed, errors = parse(buf.getvalue())
    assert parsed is None
    assert any("'fantasma'" in e.reason for e in errors)


def test_parse_image_ref_missing_in_bundle():
    wb = load_workbook(build_template())
    _fill_scalars(wb[s.SHEET_REPORTE])
    ws_img = wb[s.SHEET_IMAGENES]
    ws_img.cell(row=2, column=1, value="hero")
    ws_img.cell(row=2, column=2, value="Hero")
    ws_img.cell(row=2, column=4, value="hero.jpg")
    _add_layout(wb[s.SHEET_REPORTE], [(1, "hero")])
    buf = BytesIO()
    wb.save(buf)

    parsed, errors = parse(buf.getvalue(), available_images=frozenset())
    assert parsed is None
    assert any("no presente en images/" in e.reason for e in errors)


def test_parse_kpi_denormalized_consistency_violation():
    wb = load_workbook(build_template())
    _fill_scalars(wb[s.SHEET_REPORTE])
    ws = wb[s.SHEET_KPIS]
    # Dos rows con mismo nombre pero block_title distinto.
    ws.cell(row=2, column=1, value="kpis")
    ws.cell(row=2, column=2, value="KPIs del mes")
    ws.cell(row=2, column=3, value=1)
    ws.cell(row=2, column=4, value="Reach")
    ws.cell(row=2, column=5, value=1000)
    ws.cell(row=3, column=1, value="kpis")
    ws.cell(row=3, column=2, value="KPIs DISTINTO")
    ws.cell(row=3, column=3, value=2)
    ws.cell(row=3, column=4, value="Engagement")
    ws.cell(row=3, column=5, value=5.5)
    _add_layout(wb[s.SHEET_REPORTE], [(1, "kpis")])
    buf = BytesIO()
    wb.save(buf)
    parsed, errors = parse(buf.getvalue())
    assert parsed is None
    assert any("difiere del usado antes" in e.reason for e in errors)


# ---------------------------------------------------------------------------
# Roundtrip: writer → exporter → parser → builder
# ---------------------------------------------------------------------------
@pytest.fixture
def full_report(db):
    """Report con 1 instancia de cada block type (8 blocks), sin imágenes."""
    stage = make_stage()
    report = Report.objects.create(
        stage=stage,
        kind=Report.Kind.MENSUAL,
        period_start=date(2026, 4, 1),
        period_end=date(2026, 4, 30),
        title="Full",
        intro_text="Intro",
        conclusions_text="Concl",
        status=Report.Status.DRAFT,
    )
    TextImageBlock.objects.create(
        report=report, order=1, title="Intro", body="Body",
        image_position="left", columns=1,
    )
    # ImageBlock requiere imagen — le adjuntamos un contenido en memoria
    from django.core.files.base import ContentFile
    img_block = ImageBlock(
        report=report, order=2, title="Hero", caption="Caption",
    )
    img_block.image.save("hero.jpg", ContentFile(b"fake-image"), save=False)
    img_block.save()

    kpi = KpiGridBlock.objects.create(report=report, order=3, title="KPIs")
    KpiTile.objects.create(
        kpi_grid_block=kpi, order=1, label="Reach",
        value=Decimal("1000"), period_comparison=Decimal("5.0"),
    )

    mt = MetricsTableBlock.objects.create(
        report=report, order=4, title="Mes", network="INSTAGRAM",
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
        block=tc, order=1, caption="P1",
        source_type="ORGANIC", views=100,
    )

    tcr = TopCreatorsBlock.objects.create(
        report=report, order=6, title="Creators",
        network="INSTAGRAM", period_label="abril", limit=6,
    )
    TopCreatorItem.objects.create(
        block=tcr, order=1, handle="@test", views=200,
    )

    attr = AttributionTableBlock.objects.create(
        report=report, order=7, title="Attr", show_total=True,
    )
    OneLinkAttribution.objects.create(
        attribution_block=attr, influencer_handle="@sofi",
        clicks=100, app_downloads=20,
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


def test_roundtrip_export_parse_build_reconstructs_same_shape(full_report, db):
    """writer→exporter→parser→builder produce un Report funcionalmente equivalente."""
    # Django puede sufijar el filename ("hero.jpg" → "hero_abc.jpg") al
    # guardar. Leemos el filename real que escribió el exporter.
    img_filename = _image_filename(ImageBlock.objects.get(report=full_report))

    # 1. Export
    xlsx_bytes = export(full_report).getvalue()

    # 2. Parse
    parsed, errors = parse(
        xlsx_bytes, available_images={img_filename},
    )
    assert errors == [], f"Parser encontró errores: {[e.to_dict() for e in errors]}"
    assert parsed is not None

    # 3. Build (reusa el stage del fixture — evita colisión de UNIQUE en Client.name)
    fake_images = {img_filename: b"fake-image-bytes"}
    new_report = build_report(parsed, fake_images, stage_id=full_report.stage.pk)

    # 4. Verify shape
    assert new_report.pk != full_report.pk  # es un report nuevo
    assert new_report.kind == full_report.kind
    assert new_report.period_start == full_report.period_start
    assert new_report.period_end == full_report.period_end
    assert new_report.title == full_report.title
    assert new_report.intro_text == full_report.intro_text
    assert new_report.conclusions_text == full_report.conclusions_text
    assert new_report.status == Report.Status.DRAFT

    # Mismo número de blocks
    assert new_report.blocks.count() == full_report.blocks.count()

    # Un block de cada tipo
    assert TextImageBlock.objects.filter(report=new_report).count() == 1
    assert ImageBlock.objects.filter(report=new_report).count() == 1
    assert KpiGridBlock.objects.filter(report=new_report).count() == 1
    assert MetricsTableBlock.objects.filter(report=new_report).count() == 1
    assert TopContentsBlock.objects.filter(report=new_report).count() == 1
    assert TopCreatorsBlock.objects.filter(report=new_report).count() == 1
    assert AttributionTableBlock.objects.filter(report=new_report).count() == 1
    assert ChartBlock.objects.filter(report=new_report).count() == 1

    # Items anidados
    new_kpi = KpiGridBlock.objects.get(report=new_report)
    assert new_kpi.tiles.count() == 1
    new_chart = ChartBlock.objects.get(report=new_report)
    assert new_chart.data_points.count() == 2

    # Image persistida en ImageBlock
    new_img = ImageBlock.objects.get(report=new_report)
    assert new_img.image.name  # ImageField tiene contenido


def test_roundtrip_preserves_block_order(full_report, db):
    img_filename = _image_filename(ImageBlock.objects.get(report=full_report))
    xlsx_bytes = export(full_report).getvalue()
    parsed, errors = parse(xlsx_bytes, available_images={img_filename})
    assert errors == []
    new_report = build_report(
        parsed, {img_filename: b"data"}, stage_id=full_report.stage.pk,
    )
    orders = list(
        new_report.blocks.all().order_by("order").values_list("order", flat=True)
    )
    assert orders == [1, 2, 3, 4, 5, 6, 7, 8]


def test_builder_rolls_back_on_failure(db, full_report, monkeypatch):
    """Si el builder falla a mitad de transacción, ningún Report nuevo queda en DB."""
    img_filename = _image_filename(ImageBlock.objects.get(report=full_report))
    xlsx_bytes = export(full_report).getvalue()
    parsed, errors = parse(xlsx_bytes, available_images={img_filename})
    assert errors == []
    pre_count = Report.objects.count()

    # Forzar un fallo a mitad de la transacción: interceptar el builder
    # del ChartBlock (que corre después de que ya se crearon varios blocks).
    from apps.reports.importers import builder as b

    def boom(*args, **kwargs):
        raise RuntimeError("explotó a mitad del build")

    monkeypatch.setitem(b._BUILDERS, "ChartBlock", boom)

    with pytest.raises(RuntimeError, match="explotó"):
        build_report(parsed, {img_filename: b"x"}, stage_id=full_report.stage.pk)

    # Ningún report nuevo quedó persistido (rollback total)
    assert Report.objects.count() == pre_count


def _image_filename(img_block) -> str:
    return img_block.image.name.rsplit("/", 1)[-1]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _fill_minimal_xlsx(
    tipo: str = "Mensual",
    fecha_inicio: str = "01/04/2026",
    fecha_fin: str = "30/04/2026",
) -> bytes:
    """Generates a template with minimal valid scalars + 1 TextImageBlock in Layout."""
    wb = load_workbook(build_template())
    ws = wb[s.SHEET_REPORTE]
    # Filas KV: tipo=2, fecha_inicio=3, fecha_fin=4.
    ws.cell(row=2, column=2, value=tipo)
    ws.cell(row=3, column=2, value=fecha_inicio)
    ws.cell(row=4, column=2, value=fecha_fin)
    buf = BytesIO()
    wb.save(buf)
    return buf.getvalue()


def _fill_scalars(ws) -> None:
    ws.cell(row=2, column=2, value="Mensual")
    ws.cell(row=3, column=2, value="01/04/2026")
    ws.cell(row=4, column=2, value="30/04/2026")


def _add_layout(ws, rows: list[tuple[int, str]]) -> None:
    """Encuentra el header `orden` en la hoja Reporte y escribe las rows debajo."""
    header_row = None
    for r in range(1, ws.max_row + 1):
        if ws.cell(row=r, column=1).value == "orden":
            header_row = r
            break
    assert header_row is not None, "No encontré el header 'orden' en Reporte"
    for i, (orden, nombre) in enumerate(rows, start=1):
        ws.cell(row=header_row + i, column=1, value=orden)
        ws.cell(row=header_row + i, column=2, value=nombre)
