import Link from "next/link";
import type { StageWithReportsDto } from "@/lib/api";
import { formatCompact } from "@/lib/aggregations";
import { formatPeriod, formatReportDate } from "@/lib/format";

type ReportKind = StageWithReportsDto["reports"][number]["kind"];

const REPORT_KIND_LABEL: Record<ReportKind, string> = {
  MENSUAL: "MENSUAL",
  QUINCENAL: "QUINCENAL",
  CIERRE_ETAPA: "CIERRE DE ETAPA",
  GENERAL: "GENERAL",
  INFLUENCER: "INFLUENCERS",
};

const REPORT_KIND_BG: Record<ReportKind, string> = {
  MENSUAL: "var(--chirri-pink)",
  QUINCENAL: "var(--chirri-pink)",
  CIERRE_ETAPA: "var(--chirri-mint)",
  GENERAL: "var(--chirri-yellow)",
  INFLUENCER: "#D4B8FF",
};

function stageStatus(
  stage: StageWithReportsDto,
): { label: string; className: string } {
  const today = new Date();
  const start = stage.start_date ? new Date(stage.start_date) : null;
  const end = stage.end_date ? new Date(stage.end_date) : null;
  if (end && end < today) return { label: "CERRADA", className: "status status-archived" };
  if (start && start > today)
    return { label: "PLANIFICADA", className: "status status-paused" };
  return { label: "EN CURSO", className: "status status-approved" };
}

export default function StageBlock({
  stage,
  latestReportId,
}: {
  stage: StageWithReportsDto;
  latestReportId: number | null;
}) {
  const period = formatPeriod(stage.start_date, stage.end_date, false);
  const orderLabel = String(stage.order).padStart(2, "0");
  const status = stageStatus(stage);
  const reportCount = stage.reports.length;

  return (
    <li
      id={`stage-${stage.id}`}
      style={{
        padding: "40px 0 56px",
        borderTop: "2px solid var(--chirri-black)",
        scrollMarginTop: 140,
        listStyle: "none",
      }}
    >
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "minmax(240px, 300px) 1fr",
          gap: 48,
          alignItems: "start",
        }}
      >
        <div style={{ position: "sticky", top: 150 }}>
          <div
            className="font-display"
            style={{
              fontSize: 120,
              lineHeight: 1,
              color: "var(--chirri-pink-deep)",
              letterSpacing: "-0.04em",
            }}
            aria-hidden="true"
          >
            {orderLabel}
          </div>
          <h3
            className="font-display"
            style={{
              fontSize: 48,
              lineHeight: 0.92,
              letterSpacing: "-0.03em",
              margin: "6px 0 10px",
              textTransform: "lowercase",
              wordBreak: "break-word",
              overflowWrap: "break-word",
              hyphens: "auto",
            }}
          >
            {stage.name.toLowerCase()}
          </h3>
          <div style={{ fontSize: 12, fontWeight: 700, marginBottom: 12 }}>{period}</div>
          <span className={status.className}>● {status.label}</span>
          {stage.description && (
            <p
              style={{
                fontSize: 14,
                lineHeight: 1.5,
                marginTop: 14,
                marginBottom: 14,
                fontWeight: 500,
              }}
            >
              {stage.description}
            </p>
          )}
          <div
            style={{
              display: "flex",
              gap: 12,
              fontFamily: "var(--font-mono)",
              fontSize: 12,
              fontWeight: 700,
              opacity: 0.6,
            }}
          >
            <span>
              {stage.reach_total != null && Number(stage.reach_total) > 0
                ? `${formatCompact(Number(stage.reach_total))} reach`
                : "— reach"}
            </span>
            <span>· — piezas</span>
          </div>
        </div>

        <div>
          <div className="eyebrow" style={{ marginBottom: 14 }}>
            Reportes de esta etapa · {reportCount}
          </div>
          {reportCount === 0 ? (
            <div
              className="card card-paper"
              style={{ textAlign: "center", padding: 28 }}
            >
              <div
                className="font-display"
                style={{
                  fontSize: 24,
                  textTransform: "lowercase",
                  color: "var(--chirri-muted)",
                }}
              >
                sin reportes todavía.
              </div>
            </div>
          ) : (
            <ul
              style={{
                listStyle: "none",
                padding: 0,
                margin: 0,
                display: "flex",
                flexDirection: "column",
                gap: 10,
              }}
            >
              {stage.reports.map((r) => {
                const reachNum =
                  r.reach_total !== null && r.reach_total !== undefined
                    ? Number(r.reach_total)
                    : null;
                const hasReach = reachNum !== null && reachNum > 0;
                return (
                  <li key={r.id}>
                    <Link
                      href={`/reports/${r.id}`}
                      className="card-link"
                      style={{
                        display: "grid",
                        gridTemplateColumns: hasReach
                          ? "110px minmax(0, 1fr) 90px 70px"
                          : "110px minmax(0, 1fr) 70px",
                        gap: 16,
                        alignItems: "center",
                        padding: "16px 20px",
                        border: "2px solid var(--chirri-black)",
                        borderRadius: 14,
                        background: "white",
                        textDecoration: "none",
                        color: "inherit",
                        boxShadow: "3px 3px 0 var(--chirri-black)",
                      }}
                    >
                      <span
                        className="tag"
                        style={{
                          background: REPORT_KIND_BG[r.kind],
                          fontSize: 9.5,
                          justifySelf: "start",
                          padding: "4px 8px",
                          lineHeight: 1.15,
                        }}
                      >
                        {REPORT_KIND_LABEL[r.kind]}
                      </span>
                      <div style={{ minWidth: 0 }}>
                        <div
                          style={{
                            display: "flex",
                            alignItems: "center",
                            gap: 8,
                            minWidth: 0,
                          }}
                        >
                          <span
                            style={{
                              fontSize: 15,
                              fontWeight: 700,
                              lineHeight: 1.2,
                              overflow: "hidden",
                              textOverflow: "ellipsis",
                              whiteSpace: "nowrap",
                              minWidth: 0,
                            }}
                          >
                            {r.display_title}
                          </span>
                          {r.id === latestReportId && (
                            <span
                              className="tag"
                              style={{
                                background: "var(--chirri-pink)",
                                fontSize: 9.5,
                                padding: "3px 8px",
                                lineHeight: 1.15,
                                flexShrink: 0,
                              }}
                            >
                              ÚLTIMO
                            </span>
                          )}
                        </div>
                        <div
                          style={{
                            fontSize: 12,
                            color: "var(--chirri-muted)",
                            marginTop: 4,
                            fontWeight: 500,
                          }}
                        >
                          Publicado {formatReportDate(r.published_at)}
                        </div>
                      </div>
                      {hasReach && (
                        <div
                          className="font-mono"
                          style={{ fontSize: 13, fontWeight: 700, textAlign: "right" }}
                          aria-label="Alcance total"
                        >
                          {formatCompact(reachNum)}
                        </div>
                      )}
                      <div
                        style={{
                          textAlign: "right",
                          fontSize: 12,
                          fontWeight: 800,
                          textDecoration: "underline",
                        }}
                      >
                        Leer →
                      </div>
                    </Link>
                  </li>
                );
              })}
            </ul>
          )}
        </div>
      </div>
    </li>
  );
}
