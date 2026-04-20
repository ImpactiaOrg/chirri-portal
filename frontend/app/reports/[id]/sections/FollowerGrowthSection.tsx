import type { ReportDto } from "@/lib/api";
import { hasFollowerGrowth } from "@/lib/has-data";
import BarChartMini from "../components/BarChartMini";

const LABELS: Record<string, string> = {
  INSTAGRAM: "Instagram",
  TIKTOK: "TikTok",
  X: "X / Twitter",
};

export default function FollowerGrowthSection({ report }: { report: ReportDto }) {
  if (!hasFollowerGrowth(report)) return null;

  return (
    <section style={{ marginBottom: 48 }}>
      <span className="pill-title mint">FOLLOWER GROWTH</span>
      <h2 className="font-display" style={{ fontSize: 40, textTransform: "lowercase", margin: "16px 0" }}>
        crecimiento trimestral
      </h2>
      <div style={{ display: "flex", flexDirection: "column", gap: 32 }}>
        {Object.entries(report.follower_snapshots)
          .filter(([, arr]) => arr.length >= 2)
          .map(([network, arr]) => (
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
