"""El ReportBlockSerializer despacha por subtipo correctamente."""
import pytest

from apps.reports.tests.factories import make_report


@pytest.mark.django_db
def test_serializer_dispatches_by_subtype():
    from apps.reports.models import (
        TextImageBlock, KpiGridBlock, KpiTile, TableBlock, TableRow,
        ChartBlock, ChartDataPoint,
    )
    from apps.reports.serializers import ReportBlockSerializer

    report = make_report()
    TextImageBlock.objects.create(report=report, order=1, title="X")
    kpi = KpiGridBlock.objects.create(report=report, order=2, title="KPIs")
    KpiTile.objects.create(kpi_grid_block=kpi, label="Reach", value=100, order=1)
    tb = TableBlock.objects.create(report=report, order=3, title="Métricas")
    TableRow.objects.create(table_block=tb, order=1, is_header=True, cells=["Métrica", "Valor"])
    cb = ChartBlock.objects.create(report=report, order=4, network="INSTAGRAM")
    ChartDataPoint.objects.create(chart_block=cb, label="Ene", value=100, order=1)

    from apps.reports.models import ReportBlock
    blocks = ReportBlock.objects.filter(report=report).order_by("order")
    serialized = ReportBlockSerializer(blocks, many=True).data

    assert len(serialized) == 4
    assert [b["type"] for b in serialized] == [
        "TextImageBlock", "KpiGridBlock", "TableBlock", "ChartBlock",
    ]
    # Nested children
    assert serialized[1]["tiles"][0]["label"] == "Reach"
    assert serialized[2]["rows"][0]["cells"] == ["Métrica", "Valor"]
    assert serialized[3]["data_points"][0]["label"] == "Ene"
