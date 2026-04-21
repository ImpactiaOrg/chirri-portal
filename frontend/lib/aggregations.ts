import type { Network, ReportDto, ReportMetricDto, SourceType } from "./api";

export function metricsBySource(
  report: ReportDto,
  network: Network,
  source: SourceType,
): ReportMetricDto[] {
  return report.metrics.filter(
    (m) => m.network === network && m.source_type === source,
  );
}

export function findMetric(
  report: ReportDto,
  network: Network,
  source: SourceType,
  name: string,
): ReportMetricDto | null {
  return (
    report.metrics.find(
      (m) => m.network === network && m.source_type === source && m.metric_name === name,
    ) ?? null
  );
}

export function sumMetric(
  report: ReportDto,
  network: Network,
  name: string,
): number {
  return report.metrics
    .filter((m) => m.network === network && m.metric_name === name)
    .reduce((acc, m) => acc + Number(m.value), 0);
}

export function formatCompact(n: number): string {
  if (n >= 1_000_000) return (n / 1_000_000).toFixed(2).replace(/\.?0+$/, "") + "M";
  if (n >= 1_000) return (n / 1_000).toFixed(0) + "K";
  return String(n);
}

export function formatDelta(pct: number | null): string {
  if (pct === null || pct === undefined) return "";
  const sign = pct >= 0 ? "↑" : "↓";
  return `${sign} ${Math.abs(pct).toFixed(1)}%`;
}
