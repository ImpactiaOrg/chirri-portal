import type { ReportDto } from "@/lib/api";
import { sumMetric } from "@/lib/aggregations";
import KpiTile from "../components/KpiTile";

const NETWORKS = ["INSTAGRAM", "TIKTOK", "X"] as const;

export default function KpisSummary({ report }: { report: ReportDto }) {
  const totalReach = NETWORKS.reduce((acc, n) => acc + sumMetric(report, n, "reach"), 0);
  const orgReach = NETWORKS.reduce(
    (acc, n) =>
      acc +
      report.metrics
        .filter((m) => m.network === n && m.source_type === "ORGANIC" && m.metric_name === "reach")
        .reduce((a, m) => a + Number(m.value), 0),
    0,
  );
  const infReach = NETWORKS.reduce(
    (acc, n) =>
      acc +
      report.metrics
        .filter(
          (m) => m.network === n && m.source_type === "INFLUENCER" && m.metric_name === "reach",
        )
        .reduce((a, m) => a + Number(m.value), 0),
    0,
  );

  if (totalReach === 0) return null;

  return (
    <section style={{ marginBottom: 48 }}>
      <span className="pill-title">KPIs DEL MES</span>
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))",
          gap: 16,
          marginTop: 16,
        }}
      >
        <KpiTile label="Total Reach" value={totalReach} />
        <KpiTile label="Orgánico" value={orgReach} />
        <KpiTile label="Influencers" value={infReach} />
      </div>
    </section>
  );
}
