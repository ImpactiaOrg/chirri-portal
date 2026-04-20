from datetime import date

import pytest

from apps.reports.models import BrandFollowerSnapshot, Report, ReportMetric
from apps.reports.services.aggregations import (
    build_follower_snapshots,
    build_q1_rollup,
    build_yoy,
)

pytestmark = pytest.mark.django_db


def _make_monthly_report(stage, month, reach_value):
    r = Report.objects.create(
        stage=stage,
        kind=Report.Kind.MENSUAL,
        period_start=date(2026, month, 1),
        period_end=date(2026, month, 28),
        status=Report.Status.PUBLISHED,
    )
    ReportMetric.objects.create(
        report=r,
        network=ReportMetric.Network.INSTAGRAM,
        source_type=ReportMetric.SourceType.ORGANIC,
        metric_name="reach",
        value=reach_value,
    )
    return r


def test_build_q1_rollup_returns_three_months_for_march(balanz_stage):
    jan = _make_monthly_report(balanz_stage, 1, 100000)
    feb = _make_monthly_report(balanz_stage, 2, 200000)
    mar = _make_monthly_report(balanz_stage, 3, 300000)
    rollup = build_q1_rollup(mar)
    assert rollup["months"] == ["enero", "febrero", "marzo"]
    reach_row = next(r for r in rollup["rows"] if r["metric"] == "reach")
    assert reach_row["values"] == [100000.0, 200000.0, 300000.0]


def test_build_q1_rollup_with_only_one_report_returns_none(balanz_stage):
    mar = _make_monthly_report(balanz_stage, 3, 300000)
    rollup = build_q1_rollup(mar)
    assert rollup is None


def test_build_yoy_finds_prior_year_report(balanz_stage):
    prev = Report.objects.create(
        stage=balanz_stage,
        kind=Report.Kind.MENSUAL,
        period_start=date(2025, 3, 1),
        period_end=date(2025, 3, 31),
        status=Report.Status.PUBLISHED,
    )
    ReportMetric.objects.create(
        report=prev,
        network=ReportMetric.Network.INSTAGRAM,
        source_type=ReportMetric.SourceType.ORGANIC,
        metric_name="er",
        value=3.0,
    )
    cur = Report.objects.create(
        stage=balanz_stage,
        kind=Report.Kind.MENSUAL,
        period_start=date(2026, 3, 1),
        period_end=date(2026, 3, 31),
        status=Report.Status.PUBLISHED,
    )
    ReportMetric.objects.create(
        report=cur,
        network=ReportMetric.Network.INSTAGRAM,
        source_type=ReportMetric.SourceType.ORGANIC,
        metric_name="er",
        value=4.5,
    )
    yoy = build_yoy(cur)
    assert yoy is not None
    er_row = next(r for r in yoy if r["metric"] == "er" and r["network"] == "INSTAGRAM")
    assert float(er_row["current"]) == 4.5
    assert float(er_row["year_ago"]) == 3.0


def test_build_yoy_without_prior_returns_none(balanz_published_report):
    assert build_yoy(balanz_published_report) is None


def test_follower_snapshots_grouped_by_network(balanz_brand, balanz_stage):
    r = Report.objects.create(
        stage=balanz_stage,
        kind=Report.Kind.MENSUAL,
        period_start=date(2026, 3, 1),
        period_end=date(2026, 3, 31),
        status=Report.Status.PUBLISHED,
    )
    for m, c in [(1, 100000), (2, 104568), (3, 107072)]:
        BrandFollowerSnapshot.objects.create(
            brand=balanz_brand,
            network=ReportMetric.Network.INSTAGRAM,
            as_of=date(2026, m, 28),
            followers_count=c,
        )
    BrandFollowerSnapshot.objects.create(
        brand=balanz_brand,
        network=ReportMetric.Network.TIKTOK,
        as_of=date(2026, 3, 28),
        followers_count=50000,
    )
    snaps = build_follower_snapshots(r)
    assert len(snaps["INSTAGRAM"]) == 3
    assert snaps["INSTAGRAM"][-1]["count"] == 107072
    assert len(snaps["TIKTOK"]) == 1
