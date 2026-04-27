import type { ReportDto } from "./api";

export function hasTopContents(report: ReportDto): boolean {
  return report.sections.some((s) =>
    s.widgets.some(
      (w) => w.type === "TopContentsWidget" && (w.items ?? []).length > 0,
    ),
  );
}

export function hasTopCreators(report: ReportDto): boolean {
  return report.sections.some((s) =>
    s.widgets.some(
      (w) => w.type === "TopCreatorsWidget" && (w.items ?? []).length > 0,
    ),
  );
}

export function hasIntro(report: ReportDto): boolean {
  return report.intro_text.trim().length > 0;
}

export function hasConclusions(report: ReportDto): boolean {
  return report.conclusions_text.trim().length > 0;
}
