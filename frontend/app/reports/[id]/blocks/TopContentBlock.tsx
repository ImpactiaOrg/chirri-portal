import type { TopContentBlockDto } from "@/lib/api";
import ContentCard from "../components/ContentCard";

export default function TopContentBlock({ block }: { block: TopContentBlockDto }) {
  const limit = typeof block.limit === "number" && block.limit > 0 ? block.limit : 6;
  const items = (block.items ?? []).slice(0, limit);

  if (items.length === 0) return null;

  const title = block.title?.trim()
    || (block.kind === "POST" ? "Posts del mes" : "Creators del mes");

  return (
    <section style={{ marginBottom: 48 }}>
      <span className="pill-title">{title.toUpperCase()}</span>
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fill, minmax(220px, 1fr))",
          gap: 16,
          marginTop: 16,
        }}
      >
        {items.map((item, i) => (
          <ContentCard key={i} content={item} />
        ))}
      </div>
    </section>
  );
}
