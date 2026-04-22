import pytest
from apps.reports.serializers import ReportDetailSerializer

pytestmark = pytest.mark.django_db


def test_serializer_includes_new_fields(balanz_published_report):
    data = ReportDetailSerializer(balanz_published_report).data
    # top_content moved to blocks[].items after abr 2026 refactor.
    for field in ("blocks", "onelink", "follower_snapshots", "q1_rollup", "yoy", "intro_text", "brand_name"):
        assert field in data


def test_serializer_top_content_thumbnail_url_is_null_when_missing(balanz_published_report):
    from apps.reports.models import TopContent, ReportMetric, ReportBlock
    block = ReportBlock.objects.create(
        report=balanz_published_report, order=1, type=ReportBlock.Type.TOP_CONTENT,
        config={"title": "t", "kind": "POST", "limit": 6},
    )
    TopContent.objects.create(
        block=block, kind=TopContent.Kind.POST,
        network=ReportMetric.Network.INSTAGRAM,
        source_type=ReportMetric.SourceType.ORGANIC,
        rank=1, caption="x", metrics={},
    )
    data = ReportDetailSerializer(balanz_published_report).data
    assert data["blocks"][0]["items"][0]["thumbnail_url"] is None
