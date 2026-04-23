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

  return (
    <section style={{ marginBottom: 48 }}>
      {block.title && <span className="pill-title">{block.title.toUpperCase()}</span>}
      <div
        style={{
          display: "flex",
          flexDirection: direction,
          gap: 24,
          alignItems: "flex-start",
          marginTop: 16,
        }}
      >
        {hasImage && (
          // eslint-disable-next-line @next/next/no-img-element
          <img
            src={block.image_url!}
            alt={block.image_alt || block.title || ""}
            style={{ maxWidth: hasText ? "50%" : "100%", borderRadius: 8 }}
          />
        )}
        {block.body && (
          <div
            style={{
              columnCount: block.columns,
              columnGap: 24,
              maxWidth: 720,
              whiteSpace: "pre-wrap",
            }}
          >
            {block.body}
          </div>
        )}
      </div>
    </section>
  );
}
