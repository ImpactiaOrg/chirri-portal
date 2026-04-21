import type { ReportBlockDto, ReportDto, TopContentDto } from "@/lib/api";
import ContentCard from "../components/ContentCard";

type TopContentConfig = { title?: string; kind: "POST" | "CREATOR"; limit?: number };

export default function TopContentBlock({
  block,
  report,
}: {
  block: ReportBlockDto;
  report: ReportDto;
}) {
  const cfg = block.config as unknown as TopContentConfig;
  if (!cfg || (cfg.kind !== "POST" && cfg.kind !== "CREATOR")) {
    console.warn("invalid_top_content_config", block.id, cfg);
    return null;
  }
  const limit = typeof cfg.limit === "number" && cfg.limit > 0 ? cfg.limit : 6;
  const items: TopContentDto[] = report.top_content
    .filter((c) => c.kind === cfg.kind)
    .slice(0, limit);

  if (items.length === 0) return null;

  const title = cfg.title ?? (cfg.kind === "POST" ? "Posts del mes" : "Creators del mes");

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
