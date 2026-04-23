import pytest


@pytest.mark.django_db
def test_chart_block_defaults(report_factory):
    from apps.reports.models import ChartBlock
    report = report_factory()
    block = ChartBlock.objects.create(report=report, order=1, title="Followers IG")
    assert block.chart_type == "bar"
    assert block.network is None


@pytest.mark.django_db
def test_chart_block_with_data_points(report_factory):
    from apps.reports.models import ChartBlock, ChartDataPoint
    from apps.reports.choices import Network
    report = report_factory()
    block = ChartBlock.objects.create(
        report=report, order=1, network=Network.INSTAGRAM,
    )
    ChartDataPoint.objects.create(chart_block=block, label="Ene", value=100, order=1)
    ChartDataPoint.objects.create(chart_block=block, label="Feb", value=150, order=2)
    ChartDataPoint.objects.create(chart_block=block, label="Mar", value=180, order=3)
    assert block.data_points.count() == 3
    assert list(block.data_points.values_list("label", flat=True)) == ["Ene", "Feb", "Mar"]


@pytest.mark.django_db
def test_chart_block_rejects_unknown_chart_type(report_factory):
    from django.core.exceptions import ValidationError
    from apps.reports.models import ChartBlock
    report = report_factory()
    # "pie" no está en CHART_TYPES (solo bar/line son válidos).
    block = ChartBlock(report=report, order=1, chart_type="pie")
    with pytest.raises(ValidationError):
        block.full_clean()


@pytest.mark.django_db
def test_chart_block_accepts_line_type(report_factory):
    """DEV-128: ChartBlock.chart_type debe aceptar 'line' además de 'bar'."""
    from apps.reports.models import ChartBlock
    report = report_factory()
    block = ChartBlock(report=report, order=1, chart_type="line")
    block.full_clean()  # no debe raisear
    block.save()
    assert block.chart_type == "line"


def test_chart_types_enum_contains_bar_and_line():
    """DEV-128: guardrail contra regresión del enum de chart_type."""
    from apps.reports.models.blocks.chart import CHART_TYPES
    values = {value for value, _label in CHART_TYPES}
    assert values == {"bar", "line"}
