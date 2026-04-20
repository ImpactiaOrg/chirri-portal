import pytest
from django.core.management import call_command

from apps.reports.models import Report, TopContent, OneLinkAttribution, BrandFollowerSnapshot

pytestmark = pytest.mark.django_db


def test_seed_demo_creates_report_viewer_fixtures():
    call_command("seed_demo")
    r = Report.objects.filter(status=Report.Status.PUBLISHED).order_by("-period_start").first()
    assert r is not None
    assert TopContent.objects.filter(report=r).count() >= 3
    assert OneLinkAttribution.objects.filter(report=r).count() >= 3
    assert BrandFollowerSnapshot.objects.filter(brand=r.stage.campaign.brand).count() >= 3
    assert r.intro_text  # non-empty
