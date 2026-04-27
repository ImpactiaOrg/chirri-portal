import type { SectionDto } from "@/lib/api";
import WidgetRenderer from "../widgets/WidgetRenderer";

const PILL_COLORS = ["mint", "pink", "yellow", "white"] as const;

function pillColorFor(order: number): string {
  return PILL_COLORS[(order - 1) % PILL_COLORS.length];
}

const LAYOUT_GRID: Record<SectionDto["layout"], React.CSSProperties> = {
  stack: {
    display: "flex",
    flexDirection: "column",
    gap: 24,
  },
  columns_2: {
    display: "grid",
    gridTemplateColumns: "repeat(auto-fit, minmax(360px, 1fr))",
    gap: 24,
  },
  columns_3: {
    display: "grid",
    gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))",
    gap: 16,
  },
};

export default function SectionRenderer({ section }: { section: SectionDto }) {
  const sortedWidgets = [...section.widgets].sort((a, b) => a.order - b.order);
  if (sortedWidgets.length === 0) return null;

  const colorClass = pillColorFor(section.order);

  return (
    <section style={{ marginBottom: 48 }}>
      {section.title && (
        <span className={`pill-title ${colorClass}`}>
          {section.title.toUpperCase()}
        </span>
      )}
      <div
        style={{
          ...LAYOUT_GRID[section.layout],
          marginTop: section.title ? 16 : 0,
        }}
      >
        {sortedWidgets.map((w) => (
          <WidgetRenderer key={w.id} widget={w} />
        ))}
      </div>
    </section>
  );
}
