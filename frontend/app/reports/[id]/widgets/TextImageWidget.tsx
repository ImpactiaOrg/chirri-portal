import type { TextImageWidgetDto } from "@/lib/api";

export default function TextImageWidget({ widget }: { widget: TextImageWidgetDto }) {
  const hasImage = !!widget.image_url;
  const hasText = !!(widget.body || widget.title);
  if (!hasImage && !hasText) return null;

  const position = widget.image_position ?? "top";
  const direction: React.CSSProperties["flexDirection"] =
    position === "top" || !hasImage
      ? "column"
      : position === "right"
        ? "row"
        : "row-reverse";
  const isHorizontal = direction === "row" || direction === "row-reverse";
  const showSeparator = hasImage && !!widget.body;

  return (
    <div
      className="card card-paper"
      style={{
        padding: 24,
        display: "flex",
        flexDirection: direction,
        gap: 24,
        alignItems: isHorizontal ? "stretch" : "flex-start",
      }}
    >
      {widget.title && (
        <h3 style={{ margin: 0, marginBottom: 4, fontSize: 18, width: "100%" }}>
          {widget.title}
        </h3>
      )}
      {hasImage && (
        // eslint-disable-next-line @next/next/no-img-element
        <img
          src={widget.image_url!}
          alt={widget.image_alt || widget.title || ""}
          style={{
            maxWidth: widget.body ? "50%" : "100%",
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
      {widget.body && (
        <div
          style={{
            columnCount: widget.columns,
            columnGap: 24,
            maxWidth: hasImage ? 720 : "100%",
            flex: hasImage ? "0 1 auto" : "1 1 auto",
            whiteSpace: "pre-wrap",
            fontSize: 18,
            lineHeight: 1.5,
            fontWeight: 500,
            color: "var(--chirri-black)",
          }}
        >
          {widget.body}
        </div>
      )}
    </div>
  );
}
