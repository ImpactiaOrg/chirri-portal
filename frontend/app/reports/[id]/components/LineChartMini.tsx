type Point = { label: string; value: number };

type Props = {
  points: Point[];
  ariaLabelPrefix: string;
};

export default function LineChartMini({ points, ariaLabelPrefix }: Props) {
  if (points.length === 0) return null;

  const w = 640, h = 220, padL = 40, padR = 28, padT = 28, padB = 36;
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
        stroke="var(--chirri-black)" strokeWidth={1.5}
      />
      <path
        d={pathD}
        fill="none"
        stroke="var(--chirri-pink-deep)"
        strokeWidth={3.5}
        strokeLinejoin="round"
        strokeLinecap="round"
      />
      {coords.map((c, i) => {
        const isLast = i === coords.length - 1;
        return (
          <circle
            key={c.label}
            cx={c.x} cy={c.y} r={isLast ? 7 : 5}
            fill={isLast ? "var(--chirri-pink-deep)" : "#fff"}
            stroke="var(--chirri-pink-deep)" strokeWidth={3}
          />
        );
      })}
      {coords.map((c, i) => {
        const isLast = i === coords.length - 1;
        return (
          <text
            key={`m${i}`}
            x={c.x} y={h - 14}
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
