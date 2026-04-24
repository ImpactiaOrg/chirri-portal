import type { TopContentsBlockDto } from "@/lib/api";
import ContentItemCard from "../components/ContentItemCard";

export default function TopContentsBlock({ block }: { block: TopContentsBlockDto }) {
  const limit = typeof block.limit === "number" && block.limit > 0 ? block.limit : 6;
  const items = (block.items ?? []).slice(0, limit);

  if (items.length === 0) return null;

  const title = block.title?.trim() || "Top contenidos";

  return (
    <section style={{ marginBottom: 48 }}>
      <span className="pill-title">{title.toUpperCase()}</span>
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fill, minmax(200px, 1fr))",
          gap: 16,
          marginTop: 16,
        }}
      >
        {items.map((item) => (
          <ContentItemCard key={item.order} item={item} />
        ))}
      </div>
    </section>
  );
}
