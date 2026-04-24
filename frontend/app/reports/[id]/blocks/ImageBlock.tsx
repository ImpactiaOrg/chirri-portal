import type { ImageBlockDto } from "@/lib/api";

type OverlayStyle = React.CSSProperties;

function overlayStyleFor(position: ImageBlockDto["overlay_position"]): OverlayStyle | null {
  if (position === "none") return null;
  const base: OverlayStyle = {
    position: "absolute",
    left: 0,
    right: 0,
    padding: "24px 32px",
    color: "#fff",
    textShadow: "0 1px 4px rgba(0,0,0,0.55)",
    display: "flex",
    flexDirection: "column",
    gap: 8,
  };
  if (position === "top") return { ...base, top: 0 };
  if (position === "bottom") return { ...base, bottom: 0 };
  // center
  return {
    ...base,
    top: "50%",
    transform: "translateY(-50%)",
    textAlign: "center",
    alignItems: "center",
  };
}

export default function ImageBlock({ block }: { block: ImageBlockDto }) {
  if (!block.image_url) return null;

  const overlay = overlayStyleFor(block.overlay_position);
  const hasOverlayContent = overlay && (block.title.trim() || block.caption.trim());

  return (
    <section style={{ marginBottom: 48 }}>
      <div style={{ position: "relative", width: "100%", overflow: "hidden", borderRadius: 12 }}>
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img
          src={block.image_url}
          alt={block.image_alt || block.title || "Imagen del reporte"}
          style={{ width: "100%", height: "auto", display: "block" }}
        />
        {hasOverlayContent && (
          <div style={overlay!}>
            {block.title && (
              <h3 style={{ margin: 0, fontSize: 28, fontWeight: 800 }}>
                {block.title}
              </h3>
            )}
            {block.caption && (
              <p style={{ margin: 0, fontSize: 16, lineHeight: 1.4 }}>
                {block.caption}
              </p>
            )}
          </div>
        )}
      </div>
    </section>
  );
}
