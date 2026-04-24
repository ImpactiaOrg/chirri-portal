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
        Report, KpiGridBlock, MetricsTableBlock,
        TopContentsBlock, TopCreatorsBlock,
        AttributionTableBlock, ChartBlock, ImageBlock,
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
    assert MetricsTableBlock.objects.filter(report=full_report).count() == 4  # mes a mes + IG + TK + X
    assert TopContentsBlock.objects.filter(report=full_report).count() == 1
    assert TopCreatorsBlock.objects.filter(report=full_report).count() == 1
    assert AttributionTableBlock.objects.filter(report=full_report).count() == 1
    assert ChartBlock.objects.filter(report=full_report).count() == 3  # IG + TK + X

    # Kitchen-sink (Abril) debe usar todos los block types incluyendo ImageBlock (DEV-130)
    abril = Report.objects.filter(title="Reporte general · Abril").first()
    assert abril is not None
    assert ImageBlock.objects.filter(report=abril).count() == 1


@pytest.mark.django_db
def test_seed_demo_instagram_metrics_table_has_typed_rows():
    """Verifica que la metrics table de Instagram tiene rows con source_type."""
    from apps.reports.models import MetricsTableBlock, Report
    call_command("seed_demo")
    full_report = Report.objects.filter(
        stage__kind="EDUCATION", kind="GENERAL", period_start__month=3,
    ).first()
    ig_table = MetricsTableBlock.objects.filter(
        report=full_report, network="INSTAGRAM",
    ).first()
    assert ig_table is not None
    assert ig_table.rows.count() > 0
    # Spot-check: existe un row de reach orgánico
    assert ig_table.rows.filter(
        metric_name="reach", source_type="ORGANIC",
    ).exists()
