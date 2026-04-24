import type { TopCreatorItemDto } from "@/lib/api";
import { formatCompact } from "@/lib/aggregations";

type Props = { item: TopCreatorItemDto };

const METRIC_ROWS: Array<{ key: keyof TopCreatorItemDto; label: string }> = [
  { key: "views", label: "VIEWS" },
  { key: "likes", label: "LIKES" },
  { key: "comments", label: "COM" },
  { key: "shares", label: "SHARES" },
];

export default function CreatorItemCard({ item }: Props) {
  const alt = item.handle ? `Creator ${item.handle}` : "Creator destacado";

  return (
    <article
      className="card card-paper"
      style={{
        padding: 16, display: "flex", flexDirection: "column",
        alignItems: "center", gap: 12, textAlign: "center",
      }}
    >
      <div
        style={{
          width: "100%",
          aspectRatio: "3 / 4",
          background: "var(--chirri-yellow)",
          overflow: "hidden",
          borderRadius: 8,
        }}
      >
        {item.thumbnail_url ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img
            src={item.thumbnail_url}
            alt={alt}
            style={{ width: "100%", height: "100%", objectFit: "cover" }}
          />
        ) : (
          <div
            aria-hidden="true"
            style={{
              width: "100%",
              height: "100%",
              display: "grid",
              placeItems: "center",
              color: "var(--chirri-muted)",
              fontSize: 12,
            }}
          >
            sin imagen
          </div>
        )}
      </div>
      <div style={{ fontWeight: 800, fontSize: 15 }}>{item.handle}</div>
      <dl style={{ display: "grid", gap: 4, fontSize: 12, width: "100%", margin: 0 }}>
        {METRIC_ROWS.map(({ key, label }) => {
          const value = item[key];
          if (typeof value !== "number") {
            return (
              <div key={key} style={{ display: "flex", justifyContent: "space-between" }}>
                <dt style={{ color: "var(--chirri-muted)", fontWeight: 700 }}>{label}</dt>
                <dd style={{ margin: 0, fontWeight: 800 }}>-</dd>
              </div>
            );
          }
          return (
            <div key={key} style={{ display: "flex", justifyContent: "space-between" }}>
              <dt style={{ color: "var(--chirri-muted)", fontWeight: 700 }}>{label}</dt>
              <dd style={{ margin: 0, fontWeight: 800 }}>{formatCompact(value)}</dd>
            </div>
          );
        })}
      </dl>
    </article>
  );
}
