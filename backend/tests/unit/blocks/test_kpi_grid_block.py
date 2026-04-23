import pytest


@pytest.mark.django_db
def test_kpi_grid_block_creates_with_tiles(report_factory):
    from apps.reports.models import KpiGridBlock, KpiTile
    report = report_factory()
    block = KpiGridBlock.objects.create(report=report, order=1, title="KPIs")
    KpiTile.objects.create(kpi_grid_block=block, label="Reach", value=1000, order=1)
    KpiTile.objects.create(
        kpi_grid_block=block, label="ER", value=4.5,
        period_comparison=0.3, order=2,
    )
    assert block.tiles.count() == 2
    assert block.tiles.first().label == "Reach"


@pytest.mark.django_db
def test_kpi_tile_unique_order_per_grid(report_factory):
    from django.db import IntegrityError
    from apps.reports.models import KpiGridBlock, KpiTile
    report = report_factory()
    block = KpiGridBlock.objects.create(report=report, order=1)
    KpiTile.objects.create(kpi_grid_block=block, label="A", value=1, order=1)
    with pytest.raises(IntegrityError):
        KpiTile.objects.create(kpi_grid_block=block, label="B", value=2, order=1)


@pytest.mark.django_db
def test_kpi_tile_cascade_on_block_delete(report_factory):
    from apps.reports.models import KpiGridBlock, KpiTile
    report = report_factory()
    block = KpiGridBlock.objects.create(report=report, order=1)
    KpiTile.objects.create(kpi_grid_block=block, label="A", value=1, order=1)
    block.delete()
    assert KpiTile.objects.count() == 0
