import type { AttributionTableBlockDto } from "@/lib/api";

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

export default function AttributionTableBlock({
  block,
}: {
  block: AttributionTableBlockDto;
}) {
  const rows = block.entries ?? [];
  if (rows.length === 0) return null;

  const showTotal = block.show_total !== false;
  const totalClicks = rows.reduce((a, r) => a + r.clicks, 0);
  const totalDownloads = rows.reduce((a, r) => a + r.app_downloads, 0);
  const title = block.title?.trim() || "Atribución OneLink";

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
              <th scope="col" style={{ ...thStyle, textAlign: "left" }}>Influencer</th>
              <th scope="col" style={{ ...thStyle, textAlign: "right" }}>Clicks</th>
              <th scope="col" style={{ ...thStyle, textAlign: "right" }}>Descargas</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r, i) => (
              <tr
                key={i}
                style={{ borderTop: i > 0 ? "1px solid rgba(10,10,10,0.08)" : "none" }}
              >
                <td style={{ ...tdStyle, fontWeight: 600 }}>{r.influencer_handle}</td>
                <td style={{ ...tdStyle, textAlign: "right" }}>
                  {r.clicks.toLocaleString("es-AR")}
                </td>
                <td style={{ ...tdStyle, textAlign: "right" }}>
                  {r.app_downloads.toLocaleString("es-AR")}
                </td>
              </tr>
            ))}
            {showTotal && (
              <tr
                style={{
                  borderTop: "2px solid var(--chirri-black)",
                  background: "var(--chirri-paper)",
                }}
              >
                <td style={{ ...tdStyle, fontWeight: 800 }}>Total</td>
                <td style={{ ...tdStyle, textAlign: "right", fontWeight: 800 }}>
                  {totalClicks.toLocaleString("es-AR")}
                </td>
                <td style={{ ...tdStyle, textAlign: "right", fontWeight: 800 }}>
                  {totalDownloads.toLocaleString("es-AR")}
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </section>
  );
}
