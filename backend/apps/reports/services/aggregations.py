from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from apps.reports.models import BrandFollowerSnapshot, Report, ReportMetric

MONTHS_ES = [
    "enero", "febrero", "marzo", "abril", "mayo", "junio",
    "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre",
]


def _quarter_of(month: int) -> tuple[int, int]:
    start = ((month - 1) // 3) * 3 + 1
    return start, start + 2


def build_q1_rollup(report: Report) -> dict[str, Any] | None:
    quarter_start, quarter_end = _quarter_of(report.period_start.month)
    year = report.period_start.year
    brand_id = report.stage.campaign.brand_id

    reports = list(
        Report.objects
        .filter(
            stage__campaign__brand_id=brand_id,
            status=Report.Status.PUBLISHED,
            period_start__year=year,
            period_start__month__gte=quarter_start,
            period_start__month__lte=quarter_end,
        )
        .order_by("period_start")
        .prefetch_related("metrics")
    )
    if len(reports) < 2:
        return None

    months = [MONTHS_ES[r.period_start.month - 1] for r in reports]

    rows: list[dict[str, Any]] = []
    keys: set[tuple[str, str]] = set()
    for r in reports:
        for m in r.metrics.all():
            if m.source_type == ReportMetric.SourceType.ORGANIC:
                keys.add((m.metric_name, m.network))

    for metric_name, network in sorted(keys):
        values: list[float | None] = []
        for r in reports:
            match = next(
                (m for m in r.metrics.all()
                 if m.metric_name == metric_name and m.network == network
                 and m.source_type == ReportMetric.SourceType.ORGANIC),
                None,
            )
            values.append(float(match.value) if match else None)
        rows.append({"metric": metric_name, "network": network, "values": values})

    return {"months": months, "rows": rows}


def build_yoy(report: Report) -> list[dict[str, Any]] | None:
    target = date(report.period_start.year - 1, report.period_start.month, 1)
    lo = target - timedelta(days=15)
    hi = target + timedelta(days=15)
    brand_id = report.stage.campaign.brand_id

    prior = (
        Report.objects
        .filter(
            stage__campaign__brand_id=brand_id,
            status=Report.Status.PUBLISHED,
            period_start__gte=lo,
            period_start__lte=hi,
        )
        .prefetch_related("metrics")
        .first()
    )
    if prior is None:
        return None

    rows: list[dict[str, Any]] = []
    for m in report.metrics.all():
        if m.metric_name not in {"reach", "er"}:
            continue
        if m.source_type != ReportMetric.SourceType.ORGANIC:
            continue
        match = next(
            (p for p in prior.metrics.all()
             if p.metric_name == m.metric_name and p.network == m.network
             and p.source_type == ReportMetric.SourceType.ORGANIC),
            None,
        )
        if match is None:
            continue
        rows.append({
            "metric": m.metric_name,
            "network": m.network,
            "current": float(m.value),
            "year_ago": float(match.value),
        })
    return rows or None


def build_follower_snapshots(report: Report) -> dict[str, list[dict[str, Any]]]:
    lo = report.period_start - timedelta(days=90)
    hi = report.period_end
    brand_id = report.stage.campaign.brand_id

    result: dict[str, list[dict[str, Any]]] = {}
    qs = (
        BrandFollowerSnapshot.objects
        .filter(brand_id=brand_id, as_of__gte=lo, as_of__lte=hi)
        .order_by("as_of")
    )
    for s in qs:
        result.setdefault(s.network, []).append({
            "month": MONTHS_ES[s.as_of.month - 1],
            "as_of": s.as_of.isoformat(),
            "count": s.followers_count,
        })
    return result
