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

export default function LineChartMini({ points, ariaLabelPrefix }: Props) {
  if (points.length === 0) return null;

  const w = 640, h = 240, padL = 40, padR = 28, padT = 36, padB = 32;
  const values = points.map((p) => p.value);
  const max = Math.max(...values);
  const min = Math.min(...values);
  const range = max - min || 1;
  const n = points.length;

  const coords = points.map((p, i) => ({
    ...p,
    x: padL + (n === 1 ? (w - padL - padR) / 2 : (i / (n - 1)) * (w - padL - padR)),
    y: padT + (1 - (p.value - min) / range) * (h - padT - padB),
  }));
  const pathD = coords.map((c, i) => `${i === 0 ? "M" : "L"}${c.x} ${c.y}`).join(" ");

  const guides = [0, 0.5, 1].map((t) => padT + t * (h - padT - padB));

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
      {/* guías horizontales punteadas */}
      {guides.map((y, i) => (
        <line
          key={`g${i}`}
          x1={padL} x2={w - padR} y1={y} y2={y}
          stroke="var(--chirri-line-strong)" strokeWidth={1}
          strokeDasharray="2 4" opacity={0.5}
        />
      ))}
      {/* eje Y */}
      <line
        x1={padL} x2={padL} y1={padT} y2={h - padB}
        stroke="var(--chirri-black)" strokeWidth={1.5}
      />
      {/* ticks + labels eje Y */}
      {[0, 0.5, 1].map((t, i) => {
        const v = min + (1 - t) * range;
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
        stroke="var(--chirri-black)" strokeWidth={1.5}
      />
      {/* line */}
      <path
        d={pathD}
        fill="none"
        stroke="var(--chirri-pink-deep)"
        strokeWidth={3.5}
        strokeLinejoin="round"
        strokeLinecap="round"
      />
      {/* points */}
      {coords.map((c, i) => {
        const isLast = i === coords.length - 1;
        return (
          <circle
            key={`c${i}`}
            cx={c.x} cy={c.y} r={isLast ? 7 : 5}
            fill={isLast ? "var(--chirri-pink-deep)" : "#fff"}
            stroke="var(--chirri-pink-deep)" strokeWidth={3}
          />
        );
      })}
      {/* valores arriba de cada punto */}
      {coords.map((c, i) => {
        const isLast = i === coords.length - 1;
        return (
          <text
            key={`v${i}`}
            x={c.x} y={c.y - (isLast ? 14 : 11)}
            textAnchor="middle"
            fontSize={isLast ? 12.5 : 11}
            fontWeight={isLast ? 800 : 700}
            fill="var(--chirri-black)"
          >
            {fmtNum(c.value)}
          </text>
        );
      })}
      {/* month labels */}
      {coords.map((c, i) => {
        const isLast = i === coords.length - 1;
        return (
          <text
            key={`m${i}`}
            x={c.x} y={h - 12}
            textAnchor="middle"
            fontSize={11.5}
            fontWeight={isLast ? 800 : 600}
            fill={isLast ? "var(--chirri-black)" : "var(--chirri-muted)"}
          >
            {c.label}
          </text>
        );
      })}
    </svg>
  );
}
