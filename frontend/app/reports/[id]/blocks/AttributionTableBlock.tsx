import type { ReportBlockDto, ReportDto } from "@/lib/api";

type AttributionTableConfig = { title?: string; show_total?: boolean };

export default function AttributionTableBlock({
  block,
  report,
}: {
  block: ReportBlockDto;
  report: ReportDto;
}) {
  const cfg = (block.config ?? {}) as AttributionTableConfig;
  const rows = report.onelink ?? [];
  if (rows.length === 0) return null;

  const showTotal = cfg.show_total !== false;
  const totalClicks = rows.reduce((a, r) => a + r.clicks, 0);
  const totalDownloads = rows.reduce((a, r) => a + r.app_downloads, 0);
  const title = cfg.title ?? "Atribución OneLink";

  return (
    <section style={{ marginBottom: 48 }}>
      <span className="pill-title">{title.toUpperCase()}</span>
      <table style={{ width: "100%", borderCollapse: "collapse", marginTop: 12 }}>
        <thead>
          <tr>
            <th scope="col" style={{ textAlign: "left", padding: "8px 12px" }}>Influencer</th>
            <th scope="col" style={{ textAlign: "right", padding: "8px 12px" }}>Clicks</th>
            <th scope="col" style={{ textAlign: "right", padding: "8px 12px" }}>Descargas</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((r, i) => (
            <tr key={i} style={{ borderTop: "1px solid rgba(0,0,0,0.05)" }}>
              <td style={{ padding: "8px 12px" }}>{r.influencer_handle}</td>
              <td style={{ textAlign: "right", padding: "8px 12px" }}>
                {r.clicks.toLocaleString("es-AR")}
              </td>
              <td style={{ textAlign: "right", padding: "8px 12px" }}>
                {r.app_downloads.toLocaleString("es-AR")}
              </td>
            </tr>
          ))}
          {showTotal && (
            <tr style={{ borderTop: "2px solid rgba(0,0,0,0.15)", fontWeight: 600 }}>
              <td style={{ padding: "8px 12px" }}>Total</td>
              <td style={{ textAlign: "right", padding: "8px 12px" }}>
                {totalClicks.toLocaleString("es-AR")}
              </td>
              <td style={{ textAlign: "right", padding: "8px 12px" }}>
                {totalDownloads.toLocaleString("es-AR")}
              </td>
            </tr>
          )}
        </tbody>
      </table>
    </section>
  );
}
