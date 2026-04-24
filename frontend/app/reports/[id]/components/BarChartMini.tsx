type Point = { label: string; value: number };

type Props = {
  points: Point[];
  ariaLabelPrefix: string;
};

export default function BarChartMini({ points, ariaLabelPrefix }: Props) {
  if (points.length === 0) return null;

  const w = 640, h = 220, padL = 28, padR = 28, padT = 28, padB = 36;
  const values = points.map((p) => p.value);
  const max = Math.max(...values) * 1.05;
  const barGap = 28;
  const n = points.length;
  const availW = w - padL - padR - barGap * (n - 1);
  const barW = availW / n;

  const ariaLabel = `${ariaLabelPrefix}: ${points
    .map((p) => `${p.label} ${p.value.toLocaleString("es-AR")}`)
    .join(", ")}`;

  return (
    <svg
      role="img"
      aria-label={ariaLabel}
      viewBox={`0 0 ${w} ${h}`}
      style={{ width: "100%", height: "auto", display: "block" }}
    >
      <line
        x1={padL} x2={w - padR} y1={h - padB} y2={h - padB}
        stroke="var(--chirri-black)" strokeWidth={2}
      />
      {points.map((p, i) => {
        const isLast = i === n - 1;
        const x = padL + i * (barW + barGap);
        const bh = (p.value / max) * (h - padT - padB);
        const y = h - padB - bh;
        return (
          <g key={p.label}>
            <rect
              x={x} y={y} width={barW} height={bh}
              fill={isLast ? "var(--chirri-pink-deep)" : "var(--chirri-pink)"}
              stroke="var(--chirri-black)" strokeWidth={2}
              rx={3}
            />
            <text
              x={x + barW / 2} y={h - 14}
              textAnchor="middle"
              fontSize={11.5}
              fontWeight={isLast ? 800 : 600}
              fill={isLast ? "var(--chirri-black)" : "var(--chirri-muted)"}
            >
              {p.label}
            </text>
          </g>
        );
      })}
    </svg>
  );
}
