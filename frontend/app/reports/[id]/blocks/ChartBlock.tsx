import type { ChartBlockDto } from "@/lib/api";
import BarChartMini from "../components/BarChartMini";
import LineChartMini from "../components/LineChartMini";

const NETWORK_LABELS: Record<string, string> = {
  INSTAGRAM: "Instagram",
  TIKTOK: "TikTok",
  X: "X / Twitter",
};

export default function ChartBlock({ block }: { block: ChartBlockDto }) {
  const points = [...(block.data_points ?? [])]
    .sort((a, b) => a.order - b.order)
    .map((p) => ({ label: p.label, value: Number(p.value) }));
  if (points.length === 0) return null;

  const title = block.title?.trim() || "Follower growth";
  const ariaPrefix = block.network
    ? `${title} ${NETWORK_LABELS[block.network] ?? block.network}`
    : title;

  const Chart = block.chart_type === "line" ? LineChartMini : BarChartMini;

  return (
    <section style={{ marginBottom: 48 }}>
      <span className="pill-title mint">{title.toUpperCase()}</span>
      <div style={{ marginTop: 16 }}>
        <Chart points={points} ariaLabelPrefix={ariaPrefix} />
      </div>
    </section>
  );
}
