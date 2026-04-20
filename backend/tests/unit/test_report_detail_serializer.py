import pytest
from apps.reports.serializers import ReportDetailSerializer

pytestmark = pytest.mark.django_db


def test_serializer_includes_new_fields(balanz_published_report):
    data = ReportDetailSerializer(balanz_published_report).data
    for field in ("top_content", "onelink", "follower_snapshots", "q1_rollup", "yoy", "intro_text", "brand_name"):
        assert field in data


def test_serializer_top_content_thumbnail_url_is_null_when_missing(balanz_published_report):
    from apps.reports.models import TopContent, ReportMetric
    TopContent.objects.create(
        report=balanz_published_report, kind=TopContent.Kind.POST,
        network=ReportMetric.Network.INSTAGRAM,
        source_type=ReportMetric.SourceType.ORGANIC,
        rank=1, caption="x", metrics={},
    )
    data = ReportDetailSerializer(balanz_published_report).data
    assert data["top_content"][0]["thumbnail_url"] is None
