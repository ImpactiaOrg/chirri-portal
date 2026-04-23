"""ReportDetailSerializer post-DEV-116: blocks polimórficos, sin
metrics/yoy/q1_rollup/follower_snapshots."""
import pytest

from apps.reports.tests.factories import make_report


@pytest.mark.django_db
def test_payload_has_no_legacy_fields():
    from apps.reports.serializers import ReportDetailSerializer
    report = make_report()
    data = ReportDetailSerializer(report).data
    for gone in ["metrics", "yoy", "q1_rollup", "follower_snapshots", "onelink"]:
        assert gone not in data, f"legacy field still in payload: {gone}"


@pytest.mark.django_db
def test_payload_includes_blocks_as_list():
    from apps.reports.models import TextImageBlock
    from apps.reports.serializers import ReportDetailSerializer
    report = make_report()
    TextImageBlock.objects.create(
        report=report, order=1, title="Hello", body="world",
    )
    data = ReportDetailSerializer(report).data
    assert "blocks" in data
    assert len(data["blocks"]) == 1
    assert data["blocks"][0]["type"] == "TextImageBlock"
    assert data["blocks"][0]["title"] == "Hello"
