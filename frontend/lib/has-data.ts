import type { Network, ReportDto } from "./api";

export function hasMetrics(report: ReportDto, network: Network): boolean {
  return report.metrics.some((m) => m.network === network);
}

export function hasTopContent(report: ReportDto, kind: "POST" | "CREATOR"): boolean {
  return report.blocks.some(
    (b) => b.type === "TOP_CONTENT" && (b.items ?? []).some((c) => c.kind === kind),
  );
}

export function hasOneLink(report: ReportDto): boolean {
  return report.onelink.length > 0;
}

export function hasFollowerGrowth(report: ReportDto): boolean {
  return Object.values(report.follower_snapshots).some((arr) => arr.length >= 2);
}

export function hasQ1Rollup(report: ReportDto): boolean {
  return !!report.q1_rollup && report.q1_rollup.rows.length > 0 && report.q1_rollup.months.length >= 2;
}

export function hasYoy(report: ReportDto): boolean {
  return !!report.yoy && report.yoy.length > 0;
}

export function hasIntro(report: ReportDto): boolean {
  return report.intro_text.trim().length > 0;
}

export function hasConclusions(report: ReportDto): boolean {
  return report.conclusions_text.trim().length > 0;
}
