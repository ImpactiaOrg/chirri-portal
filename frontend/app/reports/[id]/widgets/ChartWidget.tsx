import type { ChartWidgetDto } from "@/lib/api";
import BarChartMini from "../components/BarChartMini";
import LineChartMini from "../components/LineChartMini";

const NETWORK_LABELS: Record<string, string> = {
  INSTAGRAM: "INSTAGRAM",
  TIKTOK: "TIKTOK",
  X: "X",
};

const NETWORK_EMOJI: Record<string, string> = {
  INSTAGRAM: "📸",
  TIKTOK: "🎵",
  X: "𝕏",
};

function shortMonth(label: string): string {
  return label.trim().slice(0, 3).toLowerCase();
}

export default function ChartWidget({ widget }: { widget: ChartWidgetDto }) {
  const points = [...(widget.data_points ?? [])]
    .sort((a, b) => a.order - b.order)
    .map((p) => ({ label: p.label, value: Number(p.value) }));
  if (points.length === 0) return null;

  const title = widget.title?.trim() || "";
  const networkLabel = widget.network ? NETWORK_LABELS[widget.network] ?? widget.network : "";
  const pillText = [title.toUpperCase(), networkLabel].filter(Boolean).join(" ");
  const emoji = widget.network ? NETWORK_EMOJI[widget.network] ?? "📊" : "📊";

  const last = points[points.length - 1];
  const prev = points.length >= 2 ? points[points.length - 2] : null;
  const deltaPct = prev ? ((last.value - prev.value) / prev.value) * 100 : null;
  const up = (deltaPct ?? 0) >= 0;

  const Chart = widget.chart_type === "line" ? LineChartMini : BarChartMini;
  const monthAxis = points.map((p) => shortMonth(p.label)).join(" · ");

  return (
    <div
      className="card card-paper"
      style={{
        padding: "28px 32px 36px",
        position: "relative",
        overflow: "hidden",
      }}
    >
      {/* Blob decorativo */}
      <div
        aria-hidden="true"
        style={{
          position: "absolute",
          top: -60,
          right: -40,
          width: 220,
          height: 220,
          borderRadius: "50%",
          background: "var(--chirri-pink)",
          opacity: 0.55,
          zIndex: 0,
        }}
      />

      {/* Header: pill */}
      <div style={{ position: "relative", zIndex: 1, marginBottom: 24 }}>
        {pillText && (
          <div
            style={{
              display: "inline-flex",
              alignItems: "center",
              gap: 6,
              padding: "5px 11px",
              background: "var(--chirri-pink)",
              border: "2px solid var(--chirri-black)",
              borderRadius: 999,
              fontSize: 10.5,
              fontWeight: 800,
              letterSpacing: "0.12em",
              textTransform: "uppercase",
              marginBottom: 14,
            }}
          >
            <span style={{ fontSize: 12 }}>{emoji}</span>
            {pillText}
          </div>
        )}
      </div>

      {/* Body: número + polaroid */}
      <div
        style={{
          position: "relative",
          zIndex: 1,
          display: "grid",
          gridTemplateColumns: "minmax(220px, 0.7fr) minmax(360px, 1.3fr)",
          gap: 32,
          alignItems: "center",
        }}
      >
        {/* Izquierda: número + delta */}
        <div>
          <div
            style={{
              fontSize: 11,
              fontWeight: 700,
              letterSpacing: "0.14em",
              opacity: 0.55,
              textTransform: "uppercase",
              marginBottom: 6,
            }}
          >
            Cierre {last.label}
          </div>
          <div
            className="font-display"
            style={{
              fontSize: 92,
              lineHeight: 0.85,
              letterSpacing: "-0.04em",
            }}
          >
            {last.value.toLocaleString("es-AR")}
          </div>
          {deltaPct !== null && (
            <div
              style={{
                marginTop: 14,
                display: "inline-flex",
                alignItems: "center",
                gap: 6,
                padding: "5px 12px",
                background: "var(--chirri-black)",
                color: "var(--chirri-yellow)",
                borderRadius: 999,
                fontSize: 13,
                fontWeight: 800,
              }}
            >
              {up ? "▲" : "▼"} {up ? "+" : ""}
              {deltaPct.toFixed(1)}% vs {prev!.label.toLowerCase()}
            </div>
          )}
        </div>

        {/* Derecha: polaroid */}
        <div
          style={{
            background: "#fff",
            border: "2px solid var(--chirri-black)",
            boxShadow: "3px 3px 0 var(--chirri-black)",
            padding: "20px 20px 16px",
            position: "relative",
          }}
        >
          {/* Cinta washi amarilla */}
          <div
            aria-hidden="true"
            style={{
              position: "absolute",
              top: -11,
              left: "50%",
              transform: "translateX(-50%)",
              width: 84,
              height: 22,
              background: "rgba(255,220,120,0.75)",
              border: "1px solid rgba(0,0,0,0.15)",
            }}
          />
          <Chart points={points} ariaLabelPrefix={pillText || title || "Chart"} />
          <div
            style={{
              marginTop: 8,
              fontFamily: "var(--font-mono, ui-monospace, monospace)",
              fontSize: 10,
              letterSpacing: "0.1em",
              opacity: 0.55,
              textAlign: "center",
            }}
          >
            {monthAxis}
          </div>
        </div>
      </div>
    </div>
  );
}
