import type { ReportBlockDto, ReportDto, Network, SourceType } from "@/lib/api";

type Filter = {
  network?: Network | null;
  source_type?: SourceType | null;
  has_comparison?: boolean | null;
};

type MetricsTableConfig = {
  title?: string;
  source: "metrics" | "yoy" | "q1_rollup";
  filter?: Filter;
};

function formatInt(n: number) {
  return n.toLocaleString("es-AR");
}

function renderMetricsRows(report: ReportDto, filter: Filter) {
  const rows = report.metrics.filter((m) => {
    if (filter.network && m.network !== filter.network) return false;
    if (filter.source_type && m.source_type !== filter.source_type) return false;
    if (filter.has_comparison === true && m.period_comparison === null) return false;
    return true;
  });
  if (rows.length === 0) return null;
  return (
    <table style={{ width: "100%", borderCollapse: "collapse", marginTop: 12 }}>
      <thead>
        <tr>
          <th scope="col" style={{ textAlign: "left", padding: "8px 12px" }}>Métrica</th>
          <th scope="col" style={{ textAlign: "right", padding: "8px 12px" }}>Valor</th>
          <th scope="col" style={{ textAlign: "right", padding: "8px 12px" }}>Δ</th>
        </tr>
      </thead>
      <tbody>
        {rows.map((m, i) => (
          <tr key={i} style={{ borderTop: "1px solid rgba(0,0,0,0.05)" }}>
            <td style={{ padding: "8px 12px" }}>
              {m.network} · {m.source_type} · {m.metric_name}
            </td>
            <td style={{ textAlign: "right", padding: "8px 12px" }}>
              {formatInt(Number(m.value))}
            </td>
            <td style={{ textAlign: "right", padding: "8px 12px" }}>
              {m.period_comparison !== null ? `${m.period_comparison}%` : "—"}
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

function renderYoy(report: ReportDto) {
  if (!report.yoy || report.yoy.length === 0) return null;
  return (
    <table style={{ width: "100%", borderCollapse: "collapse", marginTop: 12 }}>
      <thead>
        <tr>
          <th scope="col" style={{ textAlign: "left", padding: "8px 12px" }}>Métrica</th>
          <th scope="col" style={{ textAlign: "right", padding: "8px 12px" }}>Hoy</th>
          <th scope="col" style={{ textAlign: "right", padding: "8px 12px" }}>Hace 1 año</th>
        </tr>
      </thead>
      <tbody>
        {report.yoy.map((r, i) => (
          <tr key={i} style={{ borderTop: "1px solid rgba(0,0,0,0.05)" }}>
            <td style={{ padding: "8px 12px" }}>{r.network} · {r.metric}</td>
            <td style={{ textAlign: "right", padding: "8px 12px" }}>{formatInt(r.current)}</td>
            <td style={{ textAlign: "right", padding: "8px 12px" }}>{formatInt(r.year_ago)}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

function renderQ1(report: ReportDto) {
  const q = report.q1_rollup;
  if (!q || q.rows.length === 0) return null;
  return (
    <table style={{ width: "100%", borderCollapse: "collapse", marginTop: 12 }}>
      <thead>
        <tr>
          <th scope="col" style={{ textAlign: "left", padding: "8px 12px" }}>Métrica</th>
          {q.months.map((m, i) => (
            <th key={i} scope="col" style={{ textAlign: "right", padding: "8px 12px" }}>{m}</th>
          ))}
        </tr>
      </thead>
      <tbody>
        {q.rows.map((r, i) => (
          <tr key={i} style={{ borderTop: "1px solid rgba(0,0,0,0.05)" }}>
            <td style={{ padding: "8px 12px" }}>{r.network} · {r.metric}</td>
            {r.values.map((v, j) => (
              <td key={j} style={{ textAlign: "right", padding: "8px 12px" }}>
                {v === null ? "—" : formatInt(v)}
              </td>
            ))}
          </tr>
        ))}
      </tbody>
    </table>
  );
}

export default function MetricsTableBlock({
  block,
  report,
}: {
  block: ReportBlockDto;
  report: ReportDto;
}) {
  const cfg = block.config as unknown as MetricsTableConfig;
  if (!cfg || !["metrics", "yoy", "q1_rollup"].includes(cfg.source)) {
    console.warn("invalid_metrics_table_config", block.id, cfg);
    return null;
  }

  let body: React.ReactNode = null;
  if (cfg.source === "metrics") body = renderMetricsRows(report, cfg.filter ?? {});
  else if (cfg.source === "yoy") body = renderYoy(report);
  else if (cfg.source === "q1_rollup") body = renderQ1(report);

  if (!body) return null;

  return (
    <section style={{ marginBottom: 48 }}>
      {cfg.title && <span className="pill-title">{cfg.title.toUpperCase()}</span>}
      {body}
    </section>
  );
}
