"""OneLinkAttribution FK ahora apunta a AttributionTableBlock."""
import pytest


@pytest.mark.django_db
def test_onelink_fk_is_attribution_block(report_factory):
    from apps.reports.models import OneLinkAttribution, AttributionTableBlock
    report = report_factory()
    block = AttributionTableBlock.objects.create(report=report, order=1)
    entry = OneLinkAttribution.objects.create(
        attribution_block=block,
        influencer_handle="@test",
        clicks=100, app_downloads=10,
    )
    assert entry.attribution_block_id == block.id


@pytest.mark.django_db
def test_onelink_report_fk_removed():
    from apps.reports.models import OneLinkAttribution
    fields = {f.name for f in OneLinkAttribution._meta.get_fields()}
    assert "report" not in fields
