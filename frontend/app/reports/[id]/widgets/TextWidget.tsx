import type { TextWidgetDto } from "@/lib/api";

export default function TextWidget({ widget }: { widget: TextWidgetDto }) {
  if (!widget.body.trim()) return null;
  return (
    <div className="card" style={{ padding: 24, background: "#fff" }}>
      {widget.title && (
        <h3 style={{ margin: 0, marginBottom: 12, fontSize: 18 }}>
          {widget.title}
        </h3>
      )}
      <div style={{ whiteSpace: "pre-wrap", lineHeight: 1.5 }}>{widget.body}</div>
    </div>
  );
}
