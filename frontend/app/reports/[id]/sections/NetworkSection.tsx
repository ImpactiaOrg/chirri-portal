import type { ReportDto } from "@/lib/api";
import { metricsByNetwork } from "@/lib/aggregations";
import { hasMetrics } from "@/lib/has-data";
import MetricRow from "../components/MetricRow";

type Network = "INSTAGRAM" | "TIKTOK" | "X";

const LABELS: Record<Network, string> = {
  INSTAGRAM: "Instagram",
  TIKTOK: "TikTok",
  X: "X / Twitter",
};

export default function NetworkSection({
  report,
  network,
}: {
  report: ReportDto;
  network: Network;
}) {
  if (!hasMetrics(report, network)) return null;
  const metrics = metricsByNetwork(report, network);

  return (
    <section style={{ marginBottom: 40 }}>
      <h2
        className="font-display"
        style={{ fontSize: 48, textTransform: "lowercase", margin: "0 0 16px" }}
      >
        {LABELS[network].toLowerCase()}
      </h2>
      <table style={{ width: "100%", borderCollapse: "collapse" }}>
        <thead>
          <tr>
            <th scope="col" style={{ textAlign: "left", padding: "10px 12px" }}>Métrica</th>
            <th scope="col" style={{ textAlign: "right", padding: "10px 12px" }}>Valor</th>
            <th scope="col" style={{ textAlign: "right", padding: "10px 12px" }}>Δ</th>
          </tr>
        </thead>
        <tbody>
          {metrics.map((m, i) => (
            <MetricRow
              key={i}
              label={`${m.source_type.toLowerCase()} · ${m.metric_name}`}
              current={Number(m.value)}
              delta={m.period_comparison === null ? null : Number(m.period_comparison)}
            />
          ))}
        </tbody>
      </table>
    </section>
  );
}
