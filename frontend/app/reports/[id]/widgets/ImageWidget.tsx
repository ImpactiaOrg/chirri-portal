import type { ImageWidgetDto } from "@/lib/api";

export default function ImageWidget({ widget }: { widget: ImageWidgetDto }) {
  if (!widget.image_url) return null;
  return (
    <div className="card card-paper" style={{ padding: 16, overflow: "hidden" }}>
      {widget.title && (
        <h3 style={{ margin: 0, marginBottom: 12, fontSize: 18 }}>
          {widget.title}
        </h3>
      )}
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img
        src={widget.image_url}
        alt={widget.image_alt || widget.title || "Imagen del reporte"}
        style={{ width: "100%", height: "auto", display: "block", borderRadius: 8 }}
      />
      {widget.caption && (
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
          {widget.caption}
        </div>
      )}
    </div>
  );
}
