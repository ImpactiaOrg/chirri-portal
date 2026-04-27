"""Tests del Widget polymorphic dispatch."""
import pytest
from decimal import Decimal

from apps.reports.models import (
    Section, Widget,
    TextWidget, ImageWidget, TextImageWidget,
    KpiGridWidget, KpiTile,
    TableWidget, TableRow,
    ChartWidget, ChartDataPoint,
    TopContentsWidget, TopContentItem,
    TopCreatorsWidget, TopCreatorItem,
)
from apps.reports.tests.factories import make_report


@pytest.fixture
def section():
    report = make_report()
    return Section.objects.create(report=report, order=1, title="Test")


@pytest.mark.django_db
def test_text_widget_can_be_created(section):
    w = TextWidget.objects.create(section=section, order=1, body="Hola")
    assert w.body == "Hola"
    assert w.title == ""


@pytest.mark.django_db
def test_table_widget_with_rows(section):
    w = TableWidget.objects.create(section=section, order=1, show_total=True)
    TableRow.objects.create(widget=w, order=1, is_header=True, cells=["A", "B"])
    TableRow.objects.create(widget=w, order=2, cells=["1", "2"])
    rows = list(w.rows.order_by("order"))
    assert len(rows) == 2
    assert rows[0].is_header is True
    assert rows[1].cells == ["1", "2"]


@pytest.mark.django_db
def test_kpi_grid_with_tiles(section):
    w = KpiGridWidget.objects.create(section=section, order=1, title="KPIs")
    KpiTile.objects.create(
        widget=w, order=1, label="Reach", value=Decimal("100"),
    )
    assert w.tiles.count() == 1
    assert w.tiles.first().label == "Reach"


@pytest.mark.django_db
def test_chart_widget_with_points(section):
    w = ChartWidget.objects.create(section=section, order=1, chart_type="line")
    ChartDataPoint.objects.create(widget=w, order=1, label="Ene", value=Decimal("10"))
    assert w.data_points.count() == 1


@pytest.mark.django_db
def test_top_contents_with_items(section):
    w = TopContentsWidget.objects.create(section=section, order=1, period_label="Marzo")
    TopContentItem.objects.create(widget=w, order=1, caption="Post 1")
    assert w.items.count() == 1


@pytest.mark.django_db
def test_top_creators_with_items(section):
    w = TopCreatorsWidget.objects.create(section=section, order=1, period_label="Marzo")
    TopCreatorItem.objects.create(widget=w, order=1, handle="@flor")
    assert w.items.count() == 1


@pytest.mark.django_db
def test_widget_polymorphic_returns_subtype(section):
    """django-polymorphic devuelve la instancia subtipo automáticamente."""
    TextWidget.objects.create(section=section, order=1, body="x")
    TableWidget.objects.create(section=section, order=2)
    KpiGridWidget.objects.create(section=section, order=3)
    fetched = list(Widget.objects.filter(section=section).order_by("order"))
    assert isinstance(fetched[0], TextWidget)
    assert isinstance(fetched[1], TableWidget)
    assert isinstance(fetched[2], KpiGridWidget)


@pytest.mark.django_db
def test_widget_order_is_unique_per_section(section):
    from django.db import IntegrityError, transaction
    TextWidget.objects.create(section=section, order=1, body="a")
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            TableWidget.objects.create(section=section, order=1)
