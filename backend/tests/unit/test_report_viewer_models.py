import pytest
from apps.reports.models import Report

pytestmark = pytest.mark.django_db


def test_report_intro_text_defaults_to_empty(balanz_published_report):
    assert balanz_published_report.intro_text == ""


def test_report_intro_text_can_be_set(balanz_published_report):
    balanz_published_report.intro_text = "Bienvenidos al reporte."
    balanz_published_report.save()
    balanz_published_report.refresh_from_db()
    assert balanz_published_report.intro_text == "Bienvenidos al reporte."


from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from apps.reports.validators import validate_image_size, validate_image_mimetype


def test_validate_image_size_accepts_under_5mb():
    small = SimpleUploadedFile("x.jpg", b"x" * 100, content_type="image/jpeg")
    validate_image_size(small)


def test_validate_image_size_rejects_over_5mb():
    huge = SimpleUploadedFile("x.jpg", b"x" * (6 * 1024 * 1024), content_type="image/jpeg")
    with pytest.raises(ValidationError):
        validate_image_size(huge)


def test_validate_image_mimetype_accepts_jpeg():
    img = SimpleUploadedFile("x.jpg", b"x", content_type="image/jpeg")
    validate_image_mimetype(img)


def test_validate_image_mimetype_rejects_svg():
    svg = SimpleUploadedFile("x.svg", b"<svg/>", content_type="image/svg+xml")
    with pytest.raises(ValidationError):
        validate_image_mimetype(svg)


from apps.reports.models import TopContent, ReportMetric


def test_top_content_is_created_with_json_metrics(balanz_published_report):
    tc = TopContent.objects.create(
        report=balanz_published_report,
        kind=TopContent.Kind.POST,
        network=ReportMetric.Network.INSTAGRAM,
        source_type=ReportMetric.SourceType.ORGANIC,
        rank=1,
        caption="Post destacado del mes",
        metrics={"likes": 500, "reach": 12000, "er": 4.2},
    )
    assert tc.metrics["likes"] == 500
    assert tc.rank == 1


def test_top_content_orders_by_report_kind_network_rank(balanz_published_report):
    TopContent.objects.create(
        report=balanz_published_report, kind=TopContent.Kind.POST,
        network=ReportMetric.Network.INSTAGRAM, source_type=ReportMetric.SourceType.ORGANIC,
        rank=2, caption="b", metrics={},
    )
    TopContent.objects.create(
        report=balanz_published_report, kind=TopContent.Kind.POST,
        network=ReportMetric.Network.INSTAGRAM, source_type=ReportMetric.SourceType.ORGANIC,
        rank=1, caption="a", metrics={},
    )
    ranks = list(TopContent.objects.values_list("rank", flat=True))
    assert ranks == [1, 2]


from datetime import date
from django.db import IntegrityError
from apps.reports.models import BrandFollowerSnapshot


def test_follower_snapshot_enforces_unique_brand_network_date(balanz_brand):
    BrandFollowerSnapshot.objects.create(
        brand=balanz_brand,
        network=ReportMetric.Network.INSTAGRAM,
        as_of=date(2026, 2, 28),
        followers_count=104568,
    )
    with pytest.raises(IntegrityError):
        BrandFollowerSnapshot.objects.create(
            brand=balanz_brand,
            network=ReportMetric.Network.INSTAGRAM,
            as_of=date(2026, 2, 28),
            followers_count=999,
        )


from apps.reports.models import OneLinkAttribution


def test_onelink_attribution_orders_by_downloads_desc(balanz_published_report):
    OneLinkAttribution.objects.create(
        report=balanz_published_report, influencer_handle="@low", clicks=10, app_downloads=2,
    )
    OneLinkAttribution.objects.create(
        report=balanz_published_report, influencer_handle="@high", clicks=100, app_downloads=50,
    )
    handles = list(
        OneLinkAttribution.objects.filter(report=balanz_published_report)
        .values_list("influencer_handle", flat=True)
    )
    assert handles == ["@high", "@low"]
