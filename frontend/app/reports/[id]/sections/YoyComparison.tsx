import type { ReportDto } from "@/lib/api";
import { hasYoy } from "@/lib/has-data";
import { formatCompact } from "@/lib/aggregations";

export default function YoyComparison({ report }: { report: ReportDto }) {
  if (!hasYoy(report)) return null;

  return (
    <section style={{ marginBottom: 48 }}>
      <span className="pill-title mint">YEAR OVER YEAR</span>
      <h2 className="font-display" style={{ fontSize: 40, textTransform: "lowercase", margin: "16px 0" }}>
        vs. mismo mes, año anterior
      </h2>
      <table style={{ width: "100%", borderCollapse: "collapse" }}>
        <thead>
          <tr style={{ borderBottom: "2px solid var(--chirri-black)" }}>
            <th scope="col" style={{ textAlign: "left", padding: "10px 12px" }}>Métrica</th>
            <th scope="col" style={{ textAlign: "right", padding: "10px 12px" }}>Actual</th>
            <th scope="col" style={{ textAlign: "right", padding: "10px 12px" }}>Hace 1 año</th>
            <th scope="col" style={{ textAlign: "right", padding: "10px 12px" }}>Δ</th>
          </tr>
        </thead>
        <tbody>
          {report.yoy!.map((row, i) => {
            const delta = row.year_ago === 0 ? null : ((row.current - row.year_ago) / row.year_ago) * 100;
            const positive = delta !== null && delta >= 0;
            return (
              <tr key={i} style={{ borderBottom: "1px solid var(--chirri-black-10, rgba(0,0,0,0.1))" }}>
                <th scope="row" style={{ textAlign: "left", padding: "10px 12px", fontWeight: 500 }}>
                  {row.network.toLowerCase()} · {row.metric}
                </th>
                <td style={{ textAlign: "right", padding: "10px 12px", fontWeight: 700 }}>
                  {formatCompact(row.current)}
                </td>
                <td style={{ textAlign: "right", padding: "10px 12px" }}>
                  {formatCompact(row.year_ago)}
                </td>
                <td style={{ textAlign: "right", padding: "10px 12px", fontSize: 13, color: positive ? "inherit" : "var(--chirri-pink-deep)" }}>
                  {delta === null ? "—" : `${positive ? "↑" : "↓"} ${Math.abs(delta).toFixed(1)}%`}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </section>
  );
}
