import type { MetricsTableBlockDto } from "@/lib/api";

function formatValue(raw: string): string {
  const n = Number(raw);
  if (!Number.isFinite(n)) return raw;
  // Keep fractional digits when the Decimal carries them (e.g., 4.8 ER %),
  // show integers as integers.
  if (Number.isInteger(n)) return n.toLocaleString("es-AR");
  return n.toLocaleString("es-AR", { maximumFractionDigits: 2 });
}

export default function MetricsTableBlock({ block }: { block: MetricsTableBlockDto }) {
  const rows = [...(block.rows ?? [])].sort((a, b) => a.order - b.order);
  if (rows.length === 0) return null;

  const title = block.title?.trim() || (block.network ?? "Métricas");

  return (
    <section style={{ marginBottom: 48 }}>
      <span className="pill-title">{title.toUpperCase()}</span>
      <table style={{ width: "100%", borderCollapse: "collapse", marginTop: 12 }}>
        <thead>
          <tr>
            <th scope="col" style={{ textAlign: "left", padding: "8px 12px" }}>Métrica</th>
            <th scope="col" style={{ textAlign: "right", padding: "8px 12px" }}>Valor</th>
            <th scope="col" style={{ textAlign: "right", padding: "8px 12px" }}>Δ</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((r, i) => {
            const label = r.source_type
              ? `${r.source_type} · ${r.metric_name}`
              : r.metric_name;
            return (
              <tr key={i} style={{ borderTop: "1px solid rgba(0,0,0,0.05)" }}>
                <td style={{ padding: "8px 12px" }}>{label}</td>
                <td style={{ textAlign: "right", padding: "8px 12px" }}>
                  {formatValue(r.value)}
                </td>
                <td style={{ textAlign: "right", padding: "8px 12px" }}>
                  {r.period_comparison !== null ? `${r.period_comparison}%` : "—"}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </section>
  );
}
