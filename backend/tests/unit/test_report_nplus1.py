import pytest
from django.test.utils import CaptureQueriesContext
from django.db import connection

from apps.reports.models import Report, ReportMetric, ReportBlock, TopContent, OneLinkAttribution

pytestmark = pytest.mark.django_db


def test_report_detail_avoids_nplus1(authed_balanz, balanz_published_report):
    # TopContent now lives under a TOP_CONTENT ReportBlock (abr 2026 refactor).
    top_block = ReportBlock.objects.create(
        report=balanz_published_report, order=1, type=ReportBlock.Type.TOP_CONTENT,
        config={"title": "t", "kind": "POST", "limit": 6},
    )
    for i in range(20):
        TopContent.objects.create(
            block=top_block, kind=TopContent.Kind.POST,
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
    for i in range(20):
        ReportBlock.objects.create(
            report=balanz_published_report, order=i + 2,
            type=ReportBlock.Type.KPI_GRID,
            config={"tiles": [{"label": "R", "source": "reach_total"}]},
        )

    with CaptureQueriesContext(connection) as ctx:
        res = authed_balanz.get(f"/api/reports/{balanz_published_report.pk}/")
    assert res.status_code == 200
    # Query budget: auth + main report + select_related (stage/campaign/brand) +
    # prefetch x4 (metrics, top_content, onelink, blocks) + aggregations (q1 + yoy + snapshots).
    # Tight enough to fail if a row-scoped query slips in (N+1 on 20 blocks would push us well past 13).
    n = len(ctx.captured_queries)
    assert n <= 13, f"too many queries: {n}"
