import { formatCompact, formatDelta } from "@/lib/aggregations";

type Props = {
  label: string;
  value: number;
  delta?: number | null;
  unit?: string;
};

export default function KpiTile({ label, value, delta, unit }: Props) {
  const isPositive = delta !== null && delta !== undefined && delta >= 0;
  const deltaLabel = formatDelta(delta ?? null);

  return (
    <div
      className="card card-paper"
      style={{ padding: 20, display: "flex", flexDirection: "column", gap: 8 }}
    >
      <div className="eyebrow">{label}</div>
      <div
        className="font-display"
        style={{
          fontSize: 56,
          lineHeight: 0.95,
          letterSpacing: "-0.03em",
          textTransform: "lowercase",
        }}
      >
        {formatCompact(value)}
        {unit && <span style={{ fontSize: 22, marginLeft: 4 }}>{unit}</span>}
      </div>
      {deltaLabel && (
        <div
          style={{
            fontSize: 13,
            fontWeight: 700,
            color: isPositive ? "var(--chirri-mint-deep, #2a8a5a)" : "var(--chirri-pink-deep)",
          }}
          aria-label={`Variación vs periodo anterior: ${deltaLabel}`}
        >
          {deltaLabel}
        </div>
      )}
    </div>
  );
}
