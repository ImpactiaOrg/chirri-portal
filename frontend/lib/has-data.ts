import type { ReportDto } from "./api";

export function hasTopContents(report: ReportDto): boolean {
  return report.blocks.some(
    (b) => b.type === "TopContentsBlock" && (b.items ?? []).length > 0,
  );
}

export function hasTopCreators(report: ReportDto): boolean {
  return report.blocks.some(
    (b) => b.type === "TopCreatorsBlock" && (b.items ?? []).length > 0,
  );
}

export function hasIntro(report: ReportDto): boolean {
  return report.intro_text.trim().length > 0;
}

export function hasConclusions(report: ReportDto): boolean {
  return report.conclusions_text.trim().length > 0;
}
