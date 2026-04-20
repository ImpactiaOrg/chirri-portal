import Link from "next/link";
import type { StageWithReportsDto } from "@/lib/api";
import { formatPeriod, formatReportDate } from "@/lib/format";

const REPORT_KIND_LABEL: Record<
  StageWithReportsDto["reports"][number]["kind"],
  string
> = {
  MENSUAL: "MENSUAL",
  QUINCENAL: "QUINCENAL",
  CIERRE_ETAPA: "CIERRE DE ETAPA",
  GENERAL: "GENERAL",
  INFLUENCER: "INFLUENCER",
};

export default function StageBlock({ stage }: { stage: StageWithReportsDto }) {
  const period = formatPeriod(stage.start_date, stage.end_date, false);

  return (
    <li
      style={{
        display: "grid",
        gridTemplateColumns: "48px 1fr",
        gap: 20,
        padding: "24px 0",
        borderTop: "2px solid var(--chirri-black)",
      }}
    >
      <div
        className="font-display"
        style={{ fontSize: 40, lineHeight: 1, opacity: 0.6 }}
        aria-hidden="true"
      >
        {String(stage.order).padStart(2, "0")}
      </div>
      <div>
        <h3
          className="font-display"
          style={{
            fontSize: 36,
            lineHeight: 1,
            letterSpacing: "-0.02em",
            margin: "0 0 6px",
            textTransform: "lowercase",
          }}
        >
          {stage.name.toLowerCase()}
        </h3>
        <div style={{ fontSize: 12, fontWeight: 700, marginBottom: 12 }}>{period}</div>
        {stage.description && (
          <p style={{ fontSize: 14, lineHeight: 1.5, maxWidth: 620, marginBottom: 16 }}>
            {stage.description}
          </p>
        )}
        {stage.reports.length === 0 ? (
          <p style={{ fontSize: 13, color: "var(--chirri-muted)", fontStyle: "italic" }}>
            Esta etapa todavía no tiene reportes publicados.
          </p>
        ) : (
          <ul style={{ listStyle: "none", padding: 0, margin: 0, display: "flex", flexDirection: "column", gap: 8 }}>
            {stage.reports.map((r) => (
              <li key={r.id}>
                <Link
                  href={`/reports/${r.id}`}
                  className="card-link"
                  style={{
                    display: "grid",
                    gridTemplateColumns: "1fr auto auto",
                    gap: 16,
                    alignItems: "center",
                    padding: "12px 16px",
                    border: "2px solid var(--chirri-black)",
                    borderRadius: 12,
                    background: "var(--chirri-yellow-soft)",
                    textDecoration: "none",
                    color: "inherit",
                    fontSize: 14,
                    fontWeight: 600,
                  }}
                >
                  <span>{r.display_title}</span>
                  <span className="pill pill-white" style={{ fontSize: 10 }}>
                    {REPORT_KIND_LABEL[r.kind]}
                  </span>
                  <span style={{ fontSize: 12, fontWeight: 700 }}>
                    {formatReportDate(r.published_at)}
                  </span>
                </Link>
              </li>
            ))}
          </ul>
        )}
      </div>
    </li>
  );
}
