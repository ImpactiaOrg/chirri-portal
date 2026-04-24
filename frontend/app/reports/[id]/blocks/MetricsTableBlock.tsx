import type { MetricsTableBlockDto } from "@/lib/api";

function formatValue(raw: string): string {
  const n = Number(raw);
  if (!Number.isFinite(n)) return raw;
  if (Number.isInteger(n)) return n.toLocaleString("es-AR");
  return n.toLocaleString("es-AR", { maximumFractionDigits: 2 });
}

function formatDelta(pct: string | null): { text: string; positive: boolean } | null {
  if (pct === null || pct === undefined) return null;
  const n = Number(pct);
  if (!Number.isFinite(n)) return null;
  return {
    text: `${n >= 0 ? "+" : ""}${n.toLocaleString("es-AR", { maximumFractionDigits: 2 })}%`,
    positive: n >= 0,
  };
}

const thStyle: React.CSSProperties = {
  padding: "14px 20px",
  fontSize: 11,
  fontWeight: 800,
  letterSpacing: "0.14em",
  textTransform: "uppercase",
  color: "var(--chirri-black)",
  background: "var(--chirri-paper)",
  borderBottom: "2px solid var(--chirri-black)",
};

const tdStyle: React.CSSProperties = {
  padding: "14px 20px",
  fontSize: 14,
  color: "var(--chirri-black)",
};

export default function MetricsTableBlock({ block }: { block: MetricsTableBlockDto }) {
  const rows = [...(block.rows ?? [])].sort((a, b) => a.order - b.order);
  if (rows.length === 0) return null;

  const title = block.title?.trim() || (block.network ?? "Métricas");

  return (
    <section style={{ marginBottom: 48 }}>
      <span className="pill-title">{title.toUpperCase()}</span>
      <div
        className="card"
        style={{
          marginTop: 16,
          padding: 0,
          overflow: "hidden",
          background: "#fff",
        }}
      >
        <table style={{ width: "100%", borderCollapse: "collapse" }}>
          <thead>
            <tr>
              <th scope="col" style={{ ...thStyle, textAlign: "left" }}>Métrica</th>
              <th scope="col" style={{ ...thStyle, textAlign: "right" }}>Valor</th>
              <th scope="col" style={{ ...thStyle, textAlign: "right" }}>Δ</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r, i) => {
              const label = r.source_type
                ? `${r.source_type} · ${r.metric_name}`
                : r.metric_name;
              const delta = formatDelta(r.period_comparison);
              return (
                <tr
                  key={i}
                  style={{ borderTop: i > 0 ? "1px solid rgba(10,10,10,0.08)" : "none" }}
                >
                  <td style={{ ...tdStyle, fontWeight: 600 }}>{label}</td>
                  <td style={{ ...tdStyle, textAlign: "right" }}>{formatValue(r.value)}</td>
                  <td
                    style={{
                      ...tdStyle,
                      textAlign: "right",
                      fontWeight: 700,
                      color: delta
                        ? delta.positive
                          ? "var(--chirri-mint-deep)"
                          : "var(--chirri-pink-deep)"
                        : "var(--chirri-muted)",
                    }}
                  >
                    {delta ? delta.text : "—"}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </section>
  );
}
