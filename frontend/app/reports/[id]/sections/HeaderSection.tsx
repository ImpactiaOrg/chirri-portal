import type { ReportAttachmentDto, ReportDto } from "@/lib/api";
import { formatReportDate } from "@/lib/format";
import { hasIntro } from "@/lib/has-data";

const KIND_LABEL: Record<ReportDto["kind"], string> = {
  GENERAL: "Reporte General",
  INFLUENCER: "Reporte Influencers",
  QUINCENAL: "Reporte Quincenal",
  MENSUAL: "Reporte Mensual",
  CIERRE_ETAPA: "Cierre de Etapa",
};

function iconFor(mime: string): string {
  if (mime.startsWith("application/pdf")) return "📄";
  if (mime.includes("spreadsheet") || mime.includes("excel")) return "📊";
  if (mime.startsWith("image/")) return "🖼️";
  if (mime.includes("zip") || mime.includes("compressed")) return "🗜️";
  return "📎";
}

function formatSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function AttachmentList({ items }: { items: ReportAttachmentDto[] }) {
  if (items.length === 0) return null;
  return (
    <div style={{ position: "relative", marginTop: 20 }}>
      <div
        style={{
          fontSize: 10,
          letterSpacing: "0.14em",
          fontWeight: 800,
          textTransform: "uppercase",
          color: "var(--chirri-muted)",
          marginBottom: 8,
        }}
      >
        Descargas
      </div>
      <ul style={{ listStyle: "none", padding: 0, margin: 0, display: "flex", flexDirection: "column", gap: 6 }}>
        {items.map((a) => (
          <li key={a.id}>
            <a
              href={a.url ?? "#"}
              download
              aria-disabled={!a.url}
              aria-label={a.alt_text || a.title}
              style={{
                display: "inline-flex",
                alignItems: "center",
                gap: 10,
                padding: "8px 14px",
                border: "2px solid var(--chirri-black)",
                borderRadius: 999,
                background: "white",
                textDecoration: "none",
                fontSize: 14,
                fontWeight: 600,
              }}
            >
              <span aria-hidden>{iconFor(a.mime_type)}</span>
              <span>{a.title}</span>
              <span style={{ color: "var(--chirri-muted)", fontWeight: 500 }}>
                · {formatSize(a.size_bytes)}
              </span>
            </a>
          </li>
        ))}
      </ul>
    </div>
  );
}

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

        <AttachmentList items={report.attachments} />
      </div>
    </section>
  );
}
