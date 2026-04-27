import type { TopContentsWidgetDto } from "@/lib/api";
import ContentItemCard from "../components/ContentItemCard";

export default function TopContentsWidget({ widget }: { widget: TopContentsWidgetDto }) {
  const items = [...(widget.items ?? [])].sort((a, b) => a.order - b.order);

  if (items.length === 0) return null;

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
          gridTemplateColumns: "repeat(auto-fill, minmax(200px, 1fr))",
          gap: 16,
        }}
      >
        {items.map((item) => (
          <ContentItemCard key={item.order} item={item} />
        ))}
      </div>
    </div>
  );
}
