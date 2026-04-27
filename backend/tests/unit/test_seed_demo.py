"""Smoke tests para el management command seed_demo — post-Task-6 (Sections + Widgets)."""
import pytest
from django.core.management import call_command


@pytest.mark.django_db
def test_seed_demo_runs_without_error():
    """Baseline: el seed corre end-to-end sin excepciones."""
    call_command("seed_demo")


@pytest.mark.django_db
def test_seed_demo_creates_sections_and_widgets():
    """Verifica que el reporte rico (Educación Marzo General) tiene las
    11 secciones + widgets tipados esperados."""
    from apps.reports.models import (
        Report, Section,
        KpiGridWidget, TableWidget,
        TopContentsWidget, TopCreatorsWidget,
        ChartWidget, ImageWidget,
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

    # 11 secciones esperadas
    assert full_report.sections.count() == 11

    # Cada subtipo de widget está representado
    assert KpiGridWidget.objects.filter(section__report=full_report).count() == 1
    assert TableWidget.objects.filter(section__report=full_report).count() == 5  # mes a mes + IG + TK + X + atribución
    assert TopContentsWidget.objects.filter(section__report=full_report).count() == 1
    assert TopCreatorsWidget.objects.filter(section__report=full_report).count() == 1
    assert ChartWidget.objects.filter(section__report=full_report).count() == 3  # IG + TK + X

    # Kitchen-sink (Abril) debe usar todos los widget types incluyendo ImageWidget
    abril = Report.objects.filter(title="Reporte general · Abril").first()
    assert abril is not None
    assert ImageWidget.objects.filter(section__report=abril).count() == 1


@pytest.mark.django_db
def test_seed_demo_table_widget_has_header_and_rows():
    """Verifica que los TableWidget de métricas tienen header row y data rows."""
    from apps.reports.models import TableWidget, TableRow, Report, Section
    call_command("seed_demo")
    full_report = Report.objects.filter(
        stage__kind="EDUCATION", kind="GENERAL", period_start__month=3,
    ).first()
    ig_table = TableWidget.objects.filter(
        section__report=full_report, section__title="Instagram",
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
    from apps.reports.models import TableWidget, TableRow, Report
    call_command("seed_demo")
    full_report = Report.objects.filter(
        stage__kind="EDUCATION", kind="GENERAL", period_start__month=3,
    ).first()
    attr_table = TableWidget.objects.filter(
        section__report=full_report, section__title="Atribución OneLink",
    ).first()
    assert attr_table is not None
    assert attr_table.show_total is True
    # Header + 3 influencer rows
    assert attr_table.rows.count() == 4
    assert attr_table.rows.filter(is_header=True).exists()
