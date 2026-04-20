import type { ReportDto } from "@/lib/api";
import { formatReportDate } from "@/lib/format";

export default function HeaderSection({ report }: { report: ReportDto }) {
  return (
    <section style={{ marginBottom: 40 }}>
      <div className="eyebrow">{report.brand_name} · {report.campaign_name}</div>
      <h1
        className="font-display"
        style={{
          fontSize: 72,
          lineHeight: 0.9,
          letterSpacing: "-0.03em",
          margin: "8px 0 0",
          textTransform: "lowercase",
        }}
      >
        {report.display_title.toLowerCase()}
      </h1>
      <p style={{ fontSize: 14, color: "var(--chirri-muted)", marginTop: 8 }}>
        Etapa: {report.stage_name} · Publicado: {formatReportDate(report.published_at)}
      </p>
    </section>
  );
}
