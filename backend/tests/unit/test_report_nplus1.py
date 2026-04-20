import pytest
from django.test.utils import CaptureQueriesContext
from django.db import connection

from apps.reports.models import Report, ReportMetric, TopContent, OneLinkAttribution

pytestmark = pytest.mark.django_db


def test_report_detail_avoids_nplus1(authed_balanz, balanz_published_report):
    for i in range(20):
        TopContent.objects.create(
            report=balanz_published_report, kind=TopContent.Kind.POST,
            network=ReportMetric.Network.INSTAGRAM,
            source_type=ReportMetric.SourceType.ORGANIC,
            rank=i + 1, caption=f"#{i}", metrics={},
        )
    for i in range(10):
        OneLinkAttribution.objects.create(
            report=balanz_published_report,
            influencer_handle=f"@inf{i}",
            clicks=i, app_downloads=i,
        )

    with CaptureQueriesContext(connection) as ctx:
        res = authed_balanz.get(f"/api/reports/{balanz_published_report.pk}/")
    assert res.status_code == 200
    # auth + main + prefetch_related(metrics) + prefetch_related(top_content) +
    # prefetch_related(onelink) + aggregations (q1/yoy/snapshots queries).
    # Upper bound is generous — the point is no query per row.
    assert len(ctx.captured_queries) < 20, f"too many queries: {len(ctx.captured_queries)}"
