"""Tests de la serialización polimórfica de Widgets + Section."""
import pytest
from decimal import Decimal

from apps.reports.models import (
    Section,
    TextWidget, KpiGridWidget, KpiTile,
    TableWidget, TableRow,
    ChartWidget, ChartDataPoint,
    TopContentsWidget, TopContentItem,
)
from apps.reports.serializers import WidgetSerializer, SectionSerializer
from apps.reports.tests.factories import make_report


@pytest.mark.django_db
def test_text_widget_serializes_with_type():
    report = make_report()
    s = Section.objects.create(report=report, order=1, title="Intro")
    w = TextWidget.objects.create(section=s, order=1, title="", body="Hola mundo")
    data = WidgetSerializer(w).data
    assert data["type"] == "TextWidget"
    assert data["body"] == "Hola mundo"
    assert data["title"] == ""


@pytest.mark.django_db
def test_table_widget_serializes_with_rows():
    report = make_report()
    s = Section.objects.create(report=report, order=1)
    w = TableWidget.objects.create(section=s, order=1, title="IG", show_total=True)
    TableRow.objects.create(widget=w, order=1, is_header=True, cells=["A", "B"])
    TableRow.objects.create(widget=w, order=2, cells=["1", "2"])
    data = WidgetSerializer(w).data
    assert data["type"] == "TableWidget"
    assert data["title"] == "IG"
    assert data["show_total"] is True
    assert len(data["rows"]) == 2
    assert data["rows"][0]["is_header"] is True
    assert data["rows"][1]["cells"] == ["1", "2"]


@pytest.mark.django_db
def test_kpi_grid_widget_serializes_with_tiles():
    report = make_report()
    s = Section.objects.create(report=report, order=1)
    w = KpiGridWidget.objects.create(section=s, order=1)
    KpiTile.objects.create(widget=w, order=1, label="Reach", value=Decimal("100"))
    data = WidgetSerializer(w).data
    assert data["type"] == "KpiGridWidget"
    assert len(data["tiles"]) == 1


@pytest.mark.django_db
def test_section_serializes_with_widgets():
    report = make_report()
    s = Section.objects.create(
        report=report, order=1, title="Análisis", layout=Section.Layout.STACK,
    )
    TextWidget.objects.create(section=s, order=1, body="Texto")
    TableWidget.objects.create(section=s, order=2)
    data = SectionSerializer(s).data
    assert data["title"] == "Análisis"
    assert data["layout"] == "stack"
    assert data["order"] == 1
    assert len(data["widgets"]) == 2
    assert data["widgets"][0]["type"] == "TextWidget"
    assert data["widgets"][1]["type"] == "TableWidget"


@pytest.mark.django_db
def test_chart_widget_serializes_with_datapoints():
    report = make_report()
    s = Section.objects.create(report=report, order=1)
    w = ChartWidget.objects.create(section=s, order=1, chart_type="line", network="INSTAGRAM")
    ChartDataPoint.objects.create(widget=w, order=1, label="Ene", value=Decimal("10"))
    data = WidgetSerializer(w).data
    assert data["type"] == "ChartWidget"
    assert data["chart_type"] == "line"
    assert data["network"] == "INSTAGRAM"
    assert len(data["data_points"]) == 1


@pytest.mark.django_db
def test_top_contents_widget_serializes_with_items():
    report = make_report()
    s = Section.objects.create(report=report, order=1)
    w = TopContentsWidget.objects.create(section=s, order=1, period_label="Marzo", network="INSTAGRAM")
    TopContentItem.objects.create(widget=w, order=1, caption="Post 1")
    data = WidgetSerializer(w).data
    assert data["type"] == "TopContentsWidget"
    assert data["period_label"] == "Marzo"
    assert len(data["items"]) == 1
