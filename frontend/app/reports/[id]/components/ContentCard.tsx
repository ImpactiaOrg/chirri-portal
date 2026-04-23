import type { TopContentDto } from "@/lib/api";
import { formatCompact } from "@/lib/aggregations";

type Props = { content: TopContentDto };

export default function ContentCard({ content }: Props) {
  const alt = content.caption
    ? content.caption
    : content.handle
    ? `Post de ${content.handle}`
    : "Contenido destacado";

  return (
    <article
      className="card card-paper"
      style={{ padding: 0, overflow: "hidden", display: "flex", flexDirection: "column" }}
    >
      <div
        style={{
          aspectRatio: "1 / 1",
          background: "var(--chirri-pink)",
          overflow: "hidden",
          position: "relative",
        }}
      >
        {content.thumbnail_url ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img
            src={content.thumbnail_url}
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
      <div style={{ padding: 16, display: "flex", flexDirection: "column", gap: 6 }}>
        {content.handle && (
          <div style={{ fontWeight: 800, fontSize: 14 }}>{content.handle}</div>
        )}
        {content.caption && (
          <p style={{ fontSize: 13, lineHeight: 1.4, margin: 0 }}>{content.caption}</p>
        )}
        <dl
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(2, 1fr)",
            gap: 4,
            marginTop: 8,
            fontSize: 12,
          }}
        >
          {Object.entries(content.metrics).slice(0, 4).map(([k, v]) => (
            <div key={k} style={{ display: "flex", justifyContent: "space-between" }}>
              <dt style={{ color: "var(--chirri-muted)" }}>{k}</dt>
              <dd style={{ margin: 0, fontWeight: 700 }}>{formatCompact(Number(v))}</dd>
            </div>
          ))}
        </dl>
      </div>
    </article>
  );
}
