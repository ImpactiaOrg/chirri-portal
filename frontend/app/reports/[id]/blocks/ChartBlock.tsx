import type { ReportBlockDto, ReportDto } from "@/lib/api";
import BarChartMini from "../components/BarChartMini";

type ChartConfig = {
  title?: string;
  source: "follower_snapshots";
  group_by: "network";
  chart_type: "bar";
};

const LABELS: Record<string, string> = {
  INSTAGRAM: "Instagram",
  TIKTOK: "TikTok",
  X: "X / Twitter",
};

export default function ChartBlock({
  block,
  report,
}: {
  block: ReportBlockDto;
  report: ReportDto;
}) {
  const cfg = block.config as unknown as ChartConfig;
  if (cfg?.source !== "follower_snapshots" || cfg.group_by !== "network" || cfg.chart_type !== "bar") {
    console.warn("invalid_chart_config", block.id, cfg);
    return null;
  }
  const entries = Object.entries(report.follower_snapshots ?? {})
    .filter(([, arr]) => arr.length >= 2);
  if (entries.length === 0) return null;

  const title = cfg.title ?? "Follower growth";

  return (
    <section style={{ marginBottom: 48 }}>
      <span className="pill-title mint">{title.toUpperCase()}</span>
      <div style={{ display: "flex", flexDirection: "column", gap: 32, marginTop: 16 }}>
        {entries.map(([network, arr]) => (
          <div key={network}>
            <h3 style={{ fontSize: 14, fontWeight: 800, textTransform: "uppercase", margin: "0 0 12px" }}>
              {LABELS[network] ?? network}
            </h3>
            <BarChartMini
              points={arr.map((p) => ({ label: p.month, value: p.count }))}
              ariaLabelPrefix={`Follower growth ${LABELS[network] ?? network}`}
            />
          </div>
        ))}
      </div>
    </section>
  );
}
