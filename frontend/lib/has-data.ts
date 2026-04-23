import type { ReportDto } from "./api";

export function hasTopContent(report: ReportDto, kind: "POST" | "CREATOR"): boolean {
  return report.blocks.some(
    (b) => b.type === "TopContentBlock" && (b.items ?? []).some((c) => c.kind === kind),
  );
}

export function hasIntro(report: ReportDto): boolean {
  return report.intro_text.trim().length > 0;
}

export function hasConclusions(report: ReportDto): boolean {
  return report.conclusions_text.trim().length > 0;
}
