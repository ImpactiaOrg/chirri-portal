import type { TopCreatorsWidgetDto } from "@/lib/api";
import CreatorItemCard from "../components/CreatorItemCard";

export default function TopCreatorsWidget({ widget }: { widget: TopCreatorsWidgetDto }) {
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
          gridTemplateColumns: "repeat(auto-fit, minmax(200px, 280px))",
          gap: 16,
          justifyContent: "center",
        }}
      >
        {items.map((item) => (
          <CreatorItemCard key={item.order} item={item} />
        ))}
      </div>
    </div>
  );
}
