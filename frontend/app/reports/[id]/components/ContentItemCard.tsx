import type { TopContentItemDto } from "@/lib/api";
import { formatCompact } from "@/lib/aggregations";

type Props = { item: TopContentItemDto };

const METRIC_ROWS: Array<{ key: keyof TopContentItemDto; label: string }> = [
  { key: "views", label: "VIEWS" },
  { key: "likes", label: "LIKES" },
  { key: "comments", label: "COM" },
  { key: "shares", label: "SHARES" },
  { key: "saves", label: "GUARDADOS" },
];

export default function ContentItemCard({ item }: Props) {
  const alt = item.caption ? item.caption : "Contenido destacado";

  return (
    <article
      className="card card-paper"
      style={{ padding: 0, overflow: "hidden", display: "flex", flexDirection: "column" }}
    >
      <div
        style={{
          aspectRatio: "3 / 4",
          background: "var(--chirri-pink)",
          overflow: "hidden",
          position: "relative",
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
        {item.caption && (
          <div
            style={{
              position: "absolute",
              top: 12,
              left: 12,
              right: 12,
              fontWeight: 700,
              fontSize: 13,
              color: "#fff",
              textShadow: "0 1px 2px rgba(0,0,0,0.6)",
            }}
          >
            {item.caption}
          </div>
        )}
      </div>
      <dl style={{ padding: "12px 16px", display: "grid", gap: 4, fontSize: 12, margin: 0 }}>
        {METRIC_ROWS.map(({ key, label }) => {
          const value = item[key];
          if (typeof value !== "number") return null;
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
