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
def test_payload_includes_sections_as_list():
    """Task 3: blocks replaced by sections in ReportDetailSerializer."""
    from apps.reports.models import Section, TextWidget
    from apps.reports.serializers import ReportDetailSerializer
    report = make_report()
    s = Section.objects.create(report=report, order=1, title="Hello")
    TextWidget.objects.create(section=s, order=1, body="world")
    data = ReportDetailSerializer(report).data
    assert "sections" in data
    assert "blocks" not in data
    assert len(data["sections"]) == 1
    assert data["sections"][0]["title"] == "Hello"
    assert data["sections"][0]["widgets"][0]["type"] == "TextWidget"
