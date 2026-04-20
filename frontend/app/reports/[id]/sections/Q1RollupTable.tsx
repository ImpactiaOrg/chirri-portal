import type { ReportDto } from "@/lib/api";
import { hasQ1Rollup } from "@/lib/has-data";
import { formatCompact } from "@/lib/aggregations";

export default function Q1RollupTable({ report }: { report: ReportDto }) {
  if (!hasQ1Rollup(report)) return null;
  const rollup = report.q1_rollup!;

  return (
    <section style={{ marginBottom: 48 }}>
      <span className="pill-title">TRIMESTRAL</span>
      <h2 className="font-display" style={{ fontSize: 40, textTransform: "lowercase", margin: "16px 0" }}>
        comparativa mensual
      </h2>
      <table style={{ width: "100%", borderCollapse: "collapse" }}>
        <thead>
          <tr style={{ borderBottom: "2px solid var(--chirri-black)" }}>
            <th scope="col" style={{ textAlign: "left", padding: "10px 12px" }}>Métrica</th>
            {rollup.months.map((m, i) => (
              <th key={i} scope="col" style={{ textAlign: "right", padding: "10px 12px" }}>
                {m}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rollup.rows.map((row, i) => (
            <tr key={i} style={{ borderBottom: "1px solid var(--chirri-black-10, rgba(0,0,0,0.1))" }}>
              <th scope="row" style={{ textAlign: "left", padding: "10px 12px", fontWeight: 500 }}>
                {row.network.toLowerCase()} · {row.metric}
              </th>
              {row.values.map((v, j) => (
                <td key={j} style={{ textAlign: "right", padding: "10px 12px", fontWeight: 700 }}>
                  {v === null ? "—" : formatCompact(v)}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  );
}
