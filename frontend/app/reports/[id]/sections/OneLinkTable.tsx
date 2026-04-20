import type { ReportDto } from "@/lib/api";
import { hasOneLink } from "@/lib/has-data";
import { formatCompact } from "@/lib/aggregations";

export default function OneLinkTable({ report }: { report: ReportDto }) {
  if (!hasOneLink(report)) return null;
  const totalClicks = report.onelink.reduce((a, r) => a + r.clicks, 0);
  const totalDownloads = report.onelink.reduce((a, r) => a + r.app_downloads, 0);

  return (
    <section style={{ marginBottom: 48 }}>
      <span className="pill-title">ONELINK</span>
      <h2 className="font-display" style={{ fontSize: 40, textTransform: "lowercase", margin: "16px 0" }}>
        clicks y downloads por creator
      </h2>
      <table style={{ width: "100%", borderCollapse: "collapse" }}>
        <thead>
          <tr style={{ borderBottom: "2px solid var(--chirri-black)" }}>
            <th scope="col" style={{ textAlign: "left", padding: "10px 12px" }}>Creator</th>
            <th scope="col" style={{ textAlign: "right", padding: "10px 12px" }}>Clicks</th>
            <th scope="col" style={{ textAlign: "right", padding: "10px 12px" }}>Downloads</th>
          </tr>
        </thead>
        <tbody>
          {report.onelink.map((row) => (
            <tr key={row.influencer_handle} style={{ borderBottom: "1px solid var(--chirri-black-10, rgba(0,0,0,0.1))" }}>
              <th scope="row" style={{ textAlign: "left", padding: "10px 12px", fontWeight: 500 }}>
                {row.influencer_handle}
              </th>
              <td style={{ textAlign: "right", padding: "10px 12px" }}>{formatCompact(row.clicks)}</td>
              <td style={{ textAlign: "right", padding: "10px 12px", fontWeight: 700 }}>
                {formatCompact(row.app_downloads)}
              </td>
            </tr>
          ))}
          <tr style={{ borderTop: "2px solid var(--chirri-black)", fontWeight: 800 }}>
            <th scope="row" style={{ textAlign: "left", padding: "10px 12px" }}>Total</th>
            <td style={{ textAlign: "right", padding: "10px 12px" }}>{formatCompact(totalClicks)}</td>
            <td style={{ textAlign: "right", padding: "10px 12px" }}>{formatCompact(totalDownloads)}</td>
          </tr>
        </tbody>
      </table>
    </section>
  );
}
