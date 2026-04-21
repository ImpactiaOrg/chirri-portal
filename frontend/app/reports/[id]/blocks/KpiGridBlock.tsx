import type { ReportBlockDto, ReportDto, Network } from "@/lib/api";
import KpiTile from "../components/KpiTile";

const NETWORKS: Network[] = ["INSTAGRAM", "TIKTOK", "X"];

type KpiSource =
  | "reach_total"
  | "reach_organic"
  | "reach_influencer"
  | "reach_paid"
  | "engagement_total";

type Tile = { label: string; source: KpiSource };

type KpiGridConfig = { title?: string; tiles: Tile[] };

function sumReachByType(
  report: ReportDto,
  filter: "total" | "ORGANIC" | "INFLUENCER" | "PAID",
): number {
  return NETWORKS.reduce((acc, n) => {
    return (
      acc +
      report.metrics
        .filter(
          (m) =>
            m.network === n &&
            m.metric_name === "reach" &&
            (filter === "total" ? true : m.source_type === filter),
        )
        .reduce((a, m) => a + Number(m.value), 0)
    );
  }, 0);
}

function sumEngagement(report: ReportDto): number {
  return report.metrics
    .filter((m) => m.metric_name === "engagement")
    .reduce((a, m) => a + Number(m.value), 0);
}

function computeTileValue(report: ReportDto, source: KpiSource): number {
  switch (source) {
    case "reach_total":
      return sumReachByType(report, "total");
    case "reach_organic":
      return sumReachByType(report, "ORGANIC");
    case "reach_influencer":
      return sumReachByType(report, "INFLUENCER");
    case "reach_paid":
      return sumReachByType(report, "PAID");
    case "engagement_total":
      return sumEngagement(report);
    default:
      return 0;
  }
}

export default function KpiGridBlock({
  block,
  report,
}: {
  block: ReportBlockDto;
  report: ReportDto;
}) {
  const cfg = block.config as unknown as KpiGridConfig;
  if (!Array.isArray(cfg?.tiles) || cfg.tiles.length === 0) {
    console.warn("invalid_kpi_grid_config", block.id, cfg);
    return null;
  }

  const values = cfg.tiles.map((t) => computeTileValue(report, t.source));
  if (values.every((v) => v === 0)) return null;

  return (
    <section style={{ marginBottom: 48 }}>
      {cfg.title ? <span className="pill-title">{cfg.title.toUpperCase()}</span>
        : <span className="pill-title">KPIs DEL MES</span>}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))",
          gap: 16,
          marginTop: 16,
        }}
      >
        {cfg.tiles.map((tile, i) => (
          <KpiTile key={i} label={tile.label} value={values[i]} />
        ))}
      </div>
    </section>
  );
}
