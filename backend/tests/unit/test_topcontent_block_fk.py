"""Regression tests for the TopContent → ReportBlock FK refactor (abr 2026).

Before the refactor, TopContent was attached to Report and the viewer filtered
by kind. A report could have TopContent rows but no TOP_CONTENT block, leaving
the viewer empty despite having data (reports 44/47 in the Balanz demo).
After the refactor, TopContent.block is NOT NULL and items travel nested
under their block in the serializer.
"""
import pytest

from apps.reports.models import Report, ReportBlock, ReportMetric, TopContent
from apps.reports.serializers import ReportDetailSerializer

pytestmark = pytest.mark.django_db


def _make_top_content_block(report, kind: str, order: int = 1):
    return ReportBlock.objects.create(
        report=report, order=order, type=ReportBlock.Type.TOP_CONTENT,
        config={"title": "t", "kind": kind, "limit": 6},
    )


def test_topcontent_requires_block(balanz_published_report):
    """TopContent can't be saved without a block (NOT NULL FK)."""
    with pytest.raises(Exception):
        TopContent.objects.create(
            report=balanz_published_report,
            kind=TopContent.Kind.POST,
            network=ReportMetric.Network.INSTAGRAM,
            source_type=ReportMetric.SourceType.ORGANIC,
            rank=1,
        )


def test_topcontent_save_syncs_report_from_block(balanz_published_report):
    """Saving with block set auto-derives report.id to keep them in sync."""
    block = _make_top_content_block(balanz_published_report, "POST")
    tc = TopContent(
        block=block,
        kind=TopContent.Kind.POST,
        network=ReportMetric.Network.INSTAGRAM,
        source_type=ReportMetric.SourceType.ORGANIC,
        rank=1,
    )
    tc.save()
    tc.refresh_from_db()
    assert tc.report_id == balanz_published_report.id


def test_deleting_block_cascades_to_items(balanz_published_report):
    block = _make_top_content_block(balanz_published_report, "POST")
    TopContent.objects.create(
        report=balanz_published_report, block=block,
        kind=TopContent.Kind.POST,
        network=ReportMetric.Network.INSTAGRAM,
        source_type=ReportMetric.SourceType.ORGANIC,
        rank=1,
    )
    block.delete()
    assert TopContent.objects.count() == 0


def test_serializer_exposes_items_nested_under_block(balanz_published_report):
    """Regression for report 44: top content was loaded but not rendered
    because the frontend expected it under block.items, not under report.top_content."""
    block = _make_top_content_block(balanz_published_report, "POST")
    TopContent.objects.create(
        report=balanz_published_report, block=block,
        kind=TopContent.Kind.POST,
        network=ReportMetric.Network.INSTAGRAM,
        source_type=ReportMetric.SourceType.ORGANIC,
        rank=1, handle="@x", caption="hola",
    )
    data = ReportDetailSerializer(balanz_published_report).data
    assert len(data["blocks"]) == 1
    block_data = data["blocks"][0]
    assert block_data["type"] == "TOP_CONTENT"
    assert len(block_data["items"]) == 1
    assert block_data["items"][0]["caption"] == "hola"
    # DTO no longer exposes top_content at report root.
    assert "top_content" not in data


def test_serializer_items_empty_for_non_topcontent_blocks(balanz_published_report):
    block = ReportBlock.objects.create(
        report=balanz_published_report, order=1, type=ReportBlock.Type.KPI_GRID,
        config={"tiles": [{"label": "Reach", "source": "reach_total"}]},
    )
    data = ReportDetailSerializer(balanz_published_report).data
    assert data["blocks"][0]["items"] == []
