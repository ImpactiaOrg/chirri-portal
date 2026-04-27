"""Smoke tests para el management command seed_demo — post-DEV-116."""
import pytest
from django.core.management import call_command


@pytest.mark.django_db
def test_seed_demo_runs_without_error():
    """Baseline: el seed corre end-to-end sin excepciones."""
    call_command("seed_demo")


@pytest.mark.django_db
def test_seed_demo_creates_typed_blocks():
    """Verifica que el reporte rico (Educación Marzo General) tiene los
    11 blocks tipados esperados."""
    from apps.reports.models import (
        Report, KpiGridBlock, TableBlock,
        TopContentsBlock, TopCreatorsBlock,
        ChartBlock, ImageBlock,
    )
    call_command("seed_demo")

    # Al menos un reporte con layout completo
    full_report = (
        Report.objects.filter(
            stage__kind="EDUCATION",
            kind=Report.Kind.GENERAL,
            period_start__month=3,
        )
        .first()
    )
    assert full_report is not None, "Expected an Educación Marzo General report"

    # 11 blocks esperados
    assert full_report.blocks.count() == 11

    # Cada subtipo está representado
    assert KpiGridBlock.objects.filter(report=full_report).count() == 1
    assert TableBlock.objects.filter(report=full_report).count() == 5  # mes a mes + IG + TK + X + atribución
    assert TopContentsBlock.objects.filter(report=full_report).count() == 1
    assert TopCreatorsBlock.objects.filter(report=full_report).count() == 1
    assert ChartBlock.objects.filter(report=full_report).count() == 3  # IG + TK + X

    # Kitchen-sink (Abril) debe usar todos los block types incluyendo ImageBlock (DEV-130)
    abril = Report.objects.filter(title="Reporte general · Abril").first()
    assert abril is not None
    assert ImageBlock.objects.filter(report=abril).count() == 1


@pytest.mark.django_db
def test_seed_demo_table_block_has_header_and_rows():
    """Verifica que los TableBlock de métricas tienen header row y data rows."""
    from apps.reports.models import TableBlock, TableRow, Report
    call_command("seed_demo")
    full_report = Report.objects.filter(
        stage__kind="EDUCATION", kind="GENERAL", period_start__month=3,
    ).first()
    ig_table = TableBlock.objects.filter(
        report=full_report, title="Instagram",
    ).first()
    assert ig_table is not None
    assert ig_table.rows.count() > 0
    # Header row exists
    assert ig_table.rows.filter(is_header=True).exists()
    # Spot-check: existe un row de reach orgánico
    assert ig_table.rows.filter(
        cells__contains=["ORGANIC · reach"],
    ).exists()


@pytest.mark.django_db
def test_seed_demo_attribution_table_has_show_total_and_rows():
    """Verifica que la tabla de atribución tiene show_total=True y rows seeded."""
    from apps.reports.models import TableBlock, TableRow, Report
    call_command("seed_demo")
    full_report = Report.objects.filter(
        stage__kind="EDUCATION", kind="GENERAL", period_start__month=3,
    ).first()
    attr_table = TableBlock.objects.filter(
        report=full_report, title="Atribución OneLink",
    ).first()
    assert attr_table is not None
    assert attr_table.show_total is True
    # Header + 3 influencer rows
    assert attr_table.rows.count() == 4
    assert attr_table.rows.filter(is_header=True).exists()
