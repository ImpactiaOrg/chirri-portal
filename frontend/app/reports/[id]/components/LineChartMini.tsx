type Point = { label: string; value: number };

type Props = {
  points: Point[];
  ariaLabelPrefix: string;
};

export default function LineChartMini({ points, ariaLabelPrefix }: Props) {
  if (points.length === 0) return null;
  const max = Math.max(...points.map((p) => p.value));
  const ceiling = max * 1.1 || 1;

  const ariaLabel = `${ariaLabelPrefix}: ${points
    .map((p) => `${p.label} ${p.value.toLocaleString("es-AR")}`)
    .join(", ")}`;

  const slotWidth = 80;
  const gap = 20;
  const height = 160;
  const width = points.length * slotWidth + (points.length - 1) * gap;

  const coords = points.map((p, i) => {
    const x = i * (slotWidth + gap) + slotWidth / 2;
    const y = height - (p.value / ceiling) * height;
    return { ...p, x, y };
  });

  const pathD = coords
    .map((c, i) => `${i === 0 ? "M" : "L"}${c.x},${c.y}`)
    .join(" ");

  return (
    <svg
      role="img"
      aria-label={ariaLabel}
      viewBox={`0 0 ${width} ${height + 40}`}
      style={{ width: "100%", maxWidth: 520 }}
    >
      <path
        d={pathD}
        fill="none"
        stroke="var(--chirri-pink-deep)"
        strokeWidth={3}
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      {coords.map((c) => (
        <g key={c.label}>
          <circle cx={c.x} cy={c.y} r={4} fill="var(--chirri-pink-deep)" />
          <text
            x={c.x}
            y={c.y - 10}
            textAnchor="middle"
            fontSize={12}
            fontWeight={800}
            fill="var(--chirri-black)"
          >
            {c.value.toLocaleString("es-AR")}
          </text>
          <text
            x={c.x}
            y={height + 20}
            textAnchor="middle"
            fontSize={11}
            fill="var(--chirri-black)"
          >
            {c.label}
          </text>
        </g>
      ))}
    </svg>
  );
}
