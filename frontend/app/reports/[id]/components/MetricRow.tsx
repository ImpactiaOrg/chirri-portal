import { formatCompact, formatDelta } from "@/lib/aggregations";

type Props = {
  label: string;
  current: number;
  previous?: number | null;
  delta?: number | null;
  unit?: string;
};

export default function MetricRow({ label, current, previous, delta, unit }: Props) {
  return (
    <tr>
      <th scope="row" style={{ textAlign: "left", fontWeight: 500, padding: "10px 12px" }}>
        {label}
      </th>
      <td style={{ textAlign: "right", padding: "10px 12px", fontWeight: 700 }}>
        {formatCompact(current)}{unit && <span style={{ fontSize: 12 }}>{unit}</span>}
      </td>
      {previous !== undefined && previous !== null && (
        <td style={{ textAlign: "right", padding: "10px 12px", color: "var(--chirri-muted)" }}>
          {formatCompact(previous)}{unit && <span style={{ fontSize: 12 }}>{unit}</span>}
        </td>
      )}
      {delta !== undefined && (
        <td style={{ textAlign: "right", padding: "10px 12px", fontSize: 13 }}>
          {formatDelta(delta ?? null)}
        </td>
      )}
    </tr>
  );
}
