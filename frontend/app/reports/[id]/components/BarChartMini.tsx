type Point = { label: string; value: number };

type Props = {
  points: Point[];
  ariaLabelPrefix: string;
};

export default function BarChartMini({ points, ariaLabelPrefix }: Props) {
  if (points.length === 0) return null;
  const max = Math.max(...points.map((p) => p.value));
  const ceiling = max * 1.1 || 1;

  const ariaLabel = `${ariaLabelPrefix}: ${points
    .map((p) => `${p.label} ${p.value.toLocaleString("es-AR")}`)
    .join(", ")}`;

  const barWidth = 80;
  const gap = 20;
  const height = 160;
  const width = points.length * barWidth + (points.length - 1) * gap;

  return (
    <svg
      role="img"
      aria-label={ariaLabel}
      viewBox={`0 0 ${width} ${height + 40}`}
      style={{ width: "100%", maxWidth: 520 }}
    >
      {points.map((p, i) => {
        const h = (p.value / ceiling) * height;
        const x = i * (barWidth + gap);
        const y = height - h;
        return (
          <g key={p.label}>
            <rect
              x={x}
              y={y}
              width={barWidth}
              height={h}
              fill="var(--chirri-pink-deep)"
            />
            <text
              x={x + barWidth / 2}
              y={y - 6}
              textAnchor="middle"
              fontSize={12}
              fontWeight={800}
              fill="var(--chirri-black)"
            >
              {p.value.toLocaleString("es-AR")}
            </text>
            <text
              x={x + barWidth / 2}
              y={height + 20}
              textAnchor="middle"
              fontSize={11}
              fill="var(--chirri-black)"
            >
              {p.label}
            </text>
          </g>
        );
      })}
    </svg>
  );
}
