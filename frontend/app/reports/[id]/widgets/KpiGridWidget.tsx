import type { KpiGridWidgetDto } from "@/lib/api";
import KpiTile from "../components/KpiTile";

const TILE_COLORS = ["mint", "pink", "yellow", "paper"] as const;

export default function KpiGridWidget({ widget }: { widget: KpiGridWidgetDto }) {
  const tiles = [...(widget.tiles ?? [])].sort((a, b) => a.order - b.order);
  if (tiles.length === 0) return null;

  return (
    <div>
      {widget.title && (
        <h3 style={{ margin: 0, marginBottom: 12, fontSize: 18 }}>
          {widget.title}
        </h3>
      )}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))",
          gap: 16,
        }}
      >
        {tiles.map((tile, i) => (
          <KpiTile
            key={tile.order}
            label={tile.label}
            value={Number(tile.value)}
            delta={tile.period_comparison !== null ? Number(tile.period_comparison) : null}
            unit={tile.unit}
            comparisonLabel={tile.period_comparison_label}
            color={TILE_COLORS[i % TILE_COLORS.length]}
          />
        ))}
      </div>
    </div>
  );
}
