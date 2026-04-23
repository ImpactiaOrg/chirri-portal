import type { KpiGridBlockDto } from "@/lib/api";
import KpiTile from "../components/KpiTile";

export default function KpiGridBlock({ block }: { block: KpiGridBlockDto }) {
  const tiles = [...(block.tiles ?? [])].sort((a, b) => a.order - b.order);
  if (tiles.length === 0) return null;

  const title = block.title?.trim() || "KPIs del mes";

  return (
    <section style={{ marginBottom: 48 }}>
      <span className="pill-title">{title.toUpperCase()}</span>
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))",
          gap: 16,
          marginTop: 16,
        }}
      >
        {tiles.map((tile, i) => (
          <KpiTile
            key={i}
            label={tile.label}
            value={Number(tile.value)}
            delta={tile.period_comparison !== null ? Number(tile.period_comparison) : null}
          />
        ))}
      </div>
    </section>
  );
}
