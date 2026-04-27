import type { TextImageBlockDto } from "@/lib/api";

export default function TextImageBlock({ block }: { block: TextImageBlockDto }) {
  const hasImage = !!block.image_url;
  const hasText = !!(block.body || block.title);
  if (!hasImage && !hasText) return null;

  const position = block.image_position ?? "top";
  const direction =
    position === "top" || !hasImage
      ? "column"
      : position === "right"
        ? "row"
        : "row-reverse";
  const isHorizontal = direction === "row" || direction === "row-reverse";
  const showSeparator = hasImage && hasText;

  return (
    <section style={{ marginBottom: 48 }}>
      {block.title && <span className="pill-title">{block.title.toUpperCase()}</span>}
      <div
        className="card card-paper"
        style={{
          marginTop: block.title ? 16 : 0,
          padding: 24,
          display: "flex",
          flexDirection: direction,
          gap: 24,
          alignItems: isHorizontal ? "stretch" : "flex-start",
        }}
      >
        {hasImage && (
          // eslint-disable-next-line @next/next/no-img-element
          <img
            src={block.image_url!}
            alt={block.image_alt || block.title || ""}
            style={{
              maxWidth: hasText ? "50%" : "100%",
              borderRadius: 8,
              display: "block",
            }}
          />
        )}
        {showSeparator && (
          <div
            aria-hidden="true"
            style={
              isHorizontal
                ? { alignSelf: "stretch", width: 2, background: "var(--chirri-black)" }
                : { width: "100%", height: 2, background: "var(--chirri-black)" }
            }
          />
        )}
        {block.body && (
          <div
            style={{
              columnCount: block.columns,
              columnGap: 24,
              // Sin imagen el body toma todo el card; con imagen lo
              // limitamos a 720 para que la imagen tenga aire al lado.
              maxWidth: hasImage ? 720 : "100%",
              flex: hasImage ? "0 1 auto" : "1 1 auto",
              whiteSpace: "pre-wrap",
              fontSize: 18,
              lineHeight: 1.5,
              fontWeight: 500,
              color: "var(--chirri-black)",
            }}
          >
            {block.body}
          </div>
        )}
      </div>
    </section>
  );
}
