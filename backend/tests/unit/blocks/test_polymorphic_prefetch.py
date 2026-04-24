"""El serializer polimórfico no genera N+1 al listar blocks."""
import pytest

from apps.reports.tests.factories import make_report
from django.test.utils import CaptureQueriesContext
from django.db import connection


@pytest.mark.django_db
def test_no_n_plus_1_on_mixed_block_types():
    from apps.reports.models import (
        Report, TextImageBlock, KpiGridBlock, KpiTile,
        MetricsTableBlock, MetricsTableRow, ChartBlock, ChartDataPoint,
    )
    from apps.reports.serializers import ReportDetailSerializer

    report = make_report()
    TextImageBlock.objects.create(report=report, order=1)
    kpi = KpiGridBlock.objects.create(report=report, order=2)
    for i in range(3):
        KpiTile.objects.create(kpi_grid_block=kpi, label=f"t{i}", value=i, order=i)
    mt = MetricsTableBlock.objects.create(report=report, order=3)
    for i in range(5):
        MetricsTableRow.objects.create(
            metrics_table_block=mt, metric_name=f"m{i}", value=i, order=i,
        )
    chart = ChartBlock.objects.create(report=report, order=4)
    for i in range(3):
        ChartDataPoint.objects.create(chart_block=chart, label=f"p{i}", value=i, order=i)

    # Fetch report with the same prefetches the view uses.
    prefetched = Report.objects.filter(pk=report.pk).prefetch_related(
        "blocks",
        "blocks__kpigridblock__tiles",
        "blocks__metricstableblock__rows",
        "blocks__chartblock__data_points",
        "blocks__topcontentsblock__items",
        "blocks__topcreatorsblock__items",
        "blocks__attributiontableblock__entries",
    ).first()

    with CaptureQueriesContext(connection) as ctx:
        data = ReportDetailSerializer(prefetched).data
        _ = data["blocks"]  # force serialization

    # Target: <=15 queries (1 Report + 1 base blocks + N per-subtype lookups +
    # children prefetches). Strict ceiling to detect N+1 regressions.
    query_count = len(ctx.captured_queries)
    assert query_count <= 15, (
        f"Too many queries ({query_count}):\n" +
        "\n".join(q["sql"][:120] for q in ctx.captured_queries)
    )
