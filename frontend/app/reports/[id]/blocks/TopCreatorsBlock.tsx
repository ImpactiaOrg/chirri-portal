import type { TopCreatorsBlockDto } from "@/lib/api";
import CreatorItemCard from "../components/CreatorItemCard";

export default function TopCreatorsBlock({ block }: { block: TopCreatorsBlockDto }) {
  const limit = typeof block.limit === "number" && block.limit > 0 ? block.limit : 6;
  const items = (block.items ?? []).slice(0, limit);

  if (items.length === 0) return null;

  const title = block.title?.trim() || "Top creadores";

  return (
    <section style={{ marginBottom: 48 }}>
      <span className="pill-title pill-title-yellow">{title.toUpperCase()}</span>
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(200px, 280px))",
          gap: 16,
          marginTop: 16,
          justifyContent: "center",
        }}
      >
        {items.map((item) => (
          <CreatorItemCard key={item.order} item={item} />
        ))}
      </div>
    </section>
  );
}
