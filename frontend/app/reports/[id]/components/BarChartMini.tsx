type Point = { label: string; value: number };

type Props = {
  points: Point[];
  ariaLabelPrefix: string;
};

function fmtNum(v: number): string {
  if (Math.abs(v) >= 1000) return Math.round(v).toLocaleString("es-AR");
  if (Number.isInteger(v)) return String(v);
  return v.toFixed(1);
}

export default function BarChartMini({ points, ariaLabelPrefix }: Props) {
  if (points.length === 0) return null;

  const w = 640, h = 240, padL = 40, padR = 28, padT = 36, padB = 32;
  const values = points.map((p) => p.value);
  const max = Math.max(...values) * 1.08;
  const avg = values.reduce((a, b) => a + b, 0) / values.length;
  const barGap = 28;
  const n = points.length;
  const availW = w - padL - padR - barGap * (n - 1);
  const barW = availW / n;
  const yFor = (v: number) => padT + (1 - v / max) * (h - padT - padB);
  const avgY = yFor(avg);

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
      {/* eje Y */}
      <line
        x1={padL} x2={padL} y1={padT} y2={h - padB}
        stroke="var(--chirri-black)" strokeWidth={1.5}
      />
      {/* ticks + labels eje Y */}
      {[0, 0.5, 1].map((t, i) => {
        const v = (1 - t) * max;
        const y = padT + t * (h - padT - padB);
        return (
          <g key={`yt${i}`}>
            <line
              x1={padL - 4} x2={padL} y1={y} y2={y}
              stroke="var(--chirri-black)" strokeWidth={1.5}
            />
            <text
              x={padL - 7} y={y + 3.5}
              textAnchor="end"
              fontFamily="var(--font-mono, ui-monospace, monospace)"
              fontSize={9} fontWeight={700}
              fill="var(--chirri-black)" opacity={0.55}
            >
              {fmtNum(v)}
            </text>
          </g>
        );
      })}
      {/* baseline */}
      <line
        x1={padL} x2={w - padR} y1={h - padB} y2={h - padB}
        stroke="var(--chirri-black)" strokeWidth={2}
      />
      {/* línea promedio horizontal — solo si hay >= 2 puntos */}
      {n >= 2 && (
        <line
          x1={padL} x2={w - padR} y1={avgY} y2={avgY}
          stroke="var(--chirri-black)" strokeWidth={1.5}
          strokeDasharray="5 4" opacity={0.55}
        />
      )}
      {/* bars + valores + meses */}
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
              x={x + barW / 2} y={y - 7}
              textAnchor="middle"
              fontSize={isLast ? 12.5 : 11}
              fontWeight={isLast ? 800 : 700}
              fill="var(--chirri-black)"
            >
              {fmtNum(p.value)}
            </text>
            <text
              x={x + barW / 2} y={h - 12}
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
