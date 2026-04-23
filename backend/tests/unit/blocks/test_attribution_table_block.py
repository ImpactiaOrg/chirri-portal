import pytest


@pytest.mark.django_db
def test_attribution_table_block_show_total_default_true(report_factory):
    from apps.reports.models import AttributionTableBlock
    report = report_factory()
    block = AttributionTableBlock.objects.create(report=report, order=1)
    assert block.show_total is True


@pytest.mark.django_db
def test_attribution_table_block_show_total_toggleable(report_factory):
    from apps.reports.models import AttributionTableBlock
    report = report_factory()
    block = AttributionTableBlock.objects.create(
        report=report, order=1, show_total=False,
    )
    assert block.show_total is False
