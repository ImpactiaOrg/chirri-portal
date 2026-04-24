import type { ImageBlockDto } from "@/lib/api";

export default function ImageBlock({ block }: { block: ImageBlockDto }) {
  if (!block.image_url) return null;

  const title = block.title?.trim();
  const caption = block.caption?.trim();

  return (
    <section style={{ marginBottom: 48 }}>
      {title && <span className="pill-title">{title.toUpperCase()}</span>}
      <div
        className="card card-paper"
        style={{
          marginTop: title ? 16 : 0,
          padding: 16,
          overflow: "hidden",
        }}
      >
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img
          src={block.image_url}
          alt={block.image_alt || title || "Imagen del reporte"}
          style={{
            width: "100%",
            height: "auto",
            display: "block",
            borderRadius: 8,
          }}
        />
        {caption && (
          <div
            style={{
              marginTop: 16,
              paddingTop: 16,
              borderTop: "2px solid var(--chirri-black)",
              fontSize: 18,
              lineHeight: 1.5,
              fontWeight: 500,
              color: "var(--chirri-black)",
            }}
          >
            {caption}
          </div>
        )}
      </div>
    </section>
  );
}
