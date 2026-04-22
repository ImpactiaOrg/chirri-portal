import type { ReportDto } from "@/lib/api";
import { formatReportDate } from "@/lib/format";
import { hasIntro } from "@/lib/has-data";

const KIND_LABEL: Record<ReportDto["kind"], string> = {
  GENERAL: "Reporte General",
  INFLUENCER: "Reporte Influencers",
  QUINCENAL: "Reporte Quincenal",
  MENSUAL: "Reporte Mensual",
  CIERRE_ETAPA: "Cierre de Etapa",
};

export default function HeaderSection({ report }: { report: ReportDto }) {
  const kindLabel = KIND_LABEL[report.kind] ?? "Reporte";
  return (
    <section style={{ marginBottom: 48 }}>
      <div
        style={{
          position: "relative",
          background: "white",
          border: "var(--border-thick)",
          borderRadius: 28,
          boxShadow: "4px 4px 0 var(--chirri-black)",
          padding: "40px 48px",
          overflow: "hidden",
        }}
      >
        <div
          aria-hidden
          style={{
            position: "absolute",
            top: -60,
            right: -80,
            width: 280,
            height: 180,
            borderRadius: "50%",
            background: "var(--chirri-mint)",
            opacity: 0.7,
            pointerEvents: "none",
          }}
        />
        <div
          aria-hidden
          style={{
            position: "absolute",
            top: 24,
            right: 40,
            fontSize: 28,
            color: "var(--chirri-mint-deep)",
            pointerEvents: "none",
          }}
        >
          ✳
        </div>

        <div style={{ position: "relative", display: "flex", gap: 12, alignItems: "center", flexWrap: "wrap" }}>
          <span
            className="pill-title mint"
            style={{ fontSize: 20, padding: "10px 24px" }}
          >
            {kindLabel.toUpperCase()}
          </span>
          <span className="pill" style={{ background: "var(--chirri-yellow)" }}>
            {report.stage_name}
          </span>
        </div>

        <h1
          className="font-display"
          style={{
            position: "relative",
            fontSize: 72,
            lineHeight: 0.95,
            letterSpacing: "-0.03em",
            margin: "24px 0 16px",
            textTransform: "lowercase",
          }}
        >
          {report.display_title.toLowerCase()}
        </h1>

        <div
          style={{
            position: "relative",
            display: "flex",
            gap: 24,
            flexWrap: "wrap",
            fontSize: 14,
            color: "var(--chirri-black)",
            marginBottom: 16,
          }}
        >
          <span>
            <span aria-hidden style={{ marginRight: 6 }}>📅</span>
            <strong>Publicado</strong> {formatReportDate(report.published_at)}
          </span>
          <span>
            <span aria-hidden style={{ marginRight: 6 }}>📍</span>
            <strong>Etapa</strong> {report.stage_name}
          </span>
        </div>

        {hasIntro(report) && (
          <p
            style={{
              position: "relative",
              fontSize: 18,
              lineHeight: 1.5,
              fontWeight: 500,
              maxWidth: 720,
              margin: "8px 0 20px",
            }}
          >
            {report.intro_text}
          </p>
        )}

        {report.original_pdf_url && (
          <a
            href={report.original_pdf_url}
            download
            aria-label="Descargar PDF original"
            className="btn btn-primary"
            style={{ position: "relative", textDecoration: "none", display: "inline-block", marginTop: 8 }}
          >
            ↓ Descargar
          </a>
        )}
      </div>
    </section>
  );
}
