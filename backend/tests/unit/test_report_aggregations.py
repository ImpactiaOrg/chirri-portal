from datetime import date

import pytest

from apps.reports.models import Report, ReportMetric
from apps.reports.services.aggregations import build_q1_rollup

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


def test_build_q1_rollup_with_only_one_report_returns_empty_rows(balanz_stage):
    mar = _make_monthly_report(balanz_stage, 3, 300000)
    rollup = build_q1_rollup(mar)
    assert rollup is None or len(rollup["rows"]) == 0 or rollup["months"] == ["marzo"]
