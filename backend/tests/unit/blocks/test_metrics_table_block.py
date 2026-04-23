import pytest


@pytest.mark.django_db
def test_metrics_table_accepts_valid_network(report_factory):
    from apps.reports.models import MetricsTableBlock
    from apps.reports.choices import Network
    report = report_factory()
    block = MetricsTableBlock.objects.create(
        report=report, order=1, network=Network.INSTAGRAM, title="IG",
    )
    assert block.network == "INSTAGRAM"


@pytest.mark.django_db
def test_metrics_table_allows_null_network(report_factory):
    from apps.reports.models import MetricsTableBlock
    report = report_factory()
    block = MetricsTableBlock.objects.create(
        report=report, order=1, title="Mes a mes",
    )
    assert block.network is None


@pytest.mark.django_db
def test_metrics_table_row_fields(report_factory):
    from apps.reports.models import MetricsTableBlock, MetricsTableRow
    from apps.reports.choices import Network, SourceType
    report = report_factory()
    block = MetricsTableBlock.objects.create(
        report=report, order=1, network=Network.INSTAGRAM,
    )
    row = MetricsTableRow.objects.create(
        metrics_table_block=block,
        metric_name="reach",
        value=500_000,
        source_type=SourceType.ORGANIC,
        period_comparison=5.2,
        order=1,
    )
    assert row.metric_name == "reach"
    assert block.rows.count() == 1


@pytest.mark.django_db
def test_metrics_table_row_source_type_nullable(report_factory):
    from apps.reports.models import MetricsTableBlock, MetricsTableRow
    report = report_factory()
    block = MetricsTableBlock.objects.create(report=report, order=1)
    row = MetricsTableRow.objects.create(
        metrics_table_block=block,
        metric_name="total_reach",
        value=1_000_000,
        order=1,
    )
    assert row.source_type is None
    assert row.period_comparison is None
