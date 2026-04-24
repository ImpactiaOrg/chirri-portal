// Presentation helpers shared across the portal. Metric-aggregation helpers
// that used to live here were removed in DEV-116 when ReportMetric was
// replaced by typed blocks with denormalised snapshots — each block carries
// its own rows/tiles, so the frontend no longer aggregates on the fly.

export function formatCompact(n: number): string {
  if (n >= 1_000_000) return (n / 1_000_000).toFixed(2).replace(/\.?0+$/, "") + "M";
  if (n >= 1_000) return (n / 1_000).toFixed(0) + "K";
  return String(n);
}

export function formatDelta(pct: number | null): string {
  if (pct === null || pct === undefined) return "";
  const sign = pct >= 0 ? "▲" : "▼";
  return `${sign} ${Math.abs(pct).toFixed(1)}%`;
}
