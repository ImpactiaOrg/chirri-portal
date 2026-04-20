import type { ReportDto } from "@/lib/api";
import { formatCompact, formatDelta } from "@/lib/aggregations";

export default function MonthlyCompare({ report }: { report: ReportDto }) {
  const withDeltas = report.metrics.filter((m) => m.period_comparison !== null);
  if (withDeltas.length === 0) return null;

  return (
    <section style={{ marginBottom: 48 }}>
      <span className="pill-title">VS MES ANTERIOR</span>
      <h2 className="font-display" style={{ fontSize: 40, textTransform: "lowercase", margin: "16px 0" }}>
        variaciones mes vs mes
      </h2>
      <table style={{ width: "100%", borderCollapse: "collapse" }}>
        <thead>
          <tr style={{ borderBottom: "2px solid var(--chirri-black)" }}>
            <th scope="col" style={{ textAlign: "left", padding: "10px 12px" }}>Red / métrica</th>
            <th scope="col" style={{ textAlign: "right", padding: "10px 12px" }}>Valor</th>
            <th scope="col" style={{ textAlign: "right", padding: "10px 12px" }}>Δ vs anterior</th>
          </tr>
        </thead>
        <tbody>
          {withDeltas.map((m, i) => {
            const delta = Number(m.period_comparison);
            const positive = delta >= 0;
            return (
              <tr key={i} style={{ borderBottom: "1px solid var(--chirri-black-10, rgba(0,0,0,0.1))" }}>
                <th scope="row" style={{ textAlign: "left", padding: "10px 12px", fontWeight: 500 }}>
                  {m.network.toLowerCase()} · {m.source_type.toLowerCase()} · {m.metric_name}
                </th>
                <td style={{ textAlign: "right", padding: "10px 12px", fontWeight: 700 }}>
                  {formatCompact(Number(m.value))}
                </td>
                <td style={{ textAlign: "right", padding: "10px 12px", fontSize: 13, color: positive ? "inherit" : "var(--chirri-pink-deep)" }}>
                  {formatDelta(delta)}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </section>
  );
}
