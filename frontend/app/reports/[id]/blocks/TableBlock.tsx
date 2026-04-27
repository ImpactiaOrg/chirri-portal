import type { TableBlockDto, TableRowDto } from "@/lib/api";

const NUMBER_RE = /^[+-]?\d+(?:[.,]\d+)?\s*$/;
const PERCENT_RE = /^[+-]?\d+(?:[.,]\d+)?\s*%$/;

type CellKind = "text" | "number" | "percent_delta";

function classify(cell: string): CellKind {
  const trimmed = cell.trim();
  if (PERCENT_RE.test(trimmed)) return "percent_delta";
  if (NUMBER_RE.test(trimmed)) return "number";
  return "text";
}

function parseNumber(cell: string): number | null {
  const n = Number(cell.trim().replace(",", "."));
  return Number.isFinite(n) ? n : null;
}

function formatNumber(cell: string): string {
  const n = parseNumber(cell);
  if (n === null) return cell;
  if (Number.isInteger(n)) return n.toLocaleString("es-AR");
  return n.toLocaleString("es-AR", { maximumFractionDigits: 2 });
}

function formatPercent(cell: string): { text: string; positive: boolean } {
  const stripped = cell.trim().replace("%", "").replace(",", ".");
  const n = Number(stripped);
  const positive = n >= 0;
  const sign = positive ? "+" : "";
  return {
    text: `${sign}${n.toLocaleString("es-AR", { maximumFractionDigits: 2 })}%`,
    positive,
  };
}

const thStyle: React.CSSProperties = {
  padding: "14px 20px",
  fontSize: 11,
  fontWeight: 800,
  letterSpacing: "0.14em",
  textTransform: "uppercase",
  color: "var(--chirri-black)",
  background: "var(--chirri-paper)",
  borderBottom: "2px solid var(--chirri-black)",
};

const tdStyle: React.CSSProperties = {
  padding: "14px 20px",
  fontSize: 14,
  color: "var(--chirri-black)",
};

function renderCell(cell: string, isHeader: boolean): React.ReactNode {
  if (isHeader) return cell;
  const kind = classify(cell);
  if (kind === "percent_delta") {
    const { text, positive } = formatPercent(cell);
    return (
      <span
        style={{
          fontWeight: 700,
          color: positive ? "var(--chirri-mint-deep)" : "var(--chirri-pink-deep)",
        }}
      >
        {text}
      </span>
    );
  }
  if (kind === "number") return formatNumber(cell);
  return cell;
}

function alignFor(cell: string, isHeader: boolean, col: number): "left" | "right" {
  if (isHeader) return col === 0 ? "left" : "right";
  return classify(cell) === "text" ? "left" : "right";
}

function computeTotals(rows: TableRowDto[], colCount: number): string[] {
  const dataRows = rows.filter((r) => !r.is_header);
  const totals: string[] = [];
  for (let col = 0; col < colCount; col++) {
    if (col === 0) {
      totals.push("Total");
      continue;
    }
    let sum = 0;
    let summable = false;
    for (const r of dataRows) {
      const cell = r.cells[col] ?? "";
      if (classify(cell) === "number") {
        const n = parseNumber(cell);
        if (n !== null) {
          sum += n;
          summable = true;
        }
      }
    }
    totals.push(summable ? formatNumber(String(sum)) : "");
  }
  return totals;
}

export default function TableBlock({ block }: { block: TableBlockDto }) {
  const sorted = [...(block.rows ?? [])].sort((a, b) => a.order - b.order);
  if (sorted.length === 0) return null;

  const headerRows = sorted.filter((r) => r.is_header);
  const dataRows = sorted.filter((r) => !r.is_header);
  const colCount = Math.max(...sorted.map((r) => r.cells.length));
  const showTotal = block.show_total && dataRows.length > 0;
  const totals = showTotal ? computeTotals(sorted, colCount) : null;
  const title = block.title?.trim();

  return (
    <section style={{ marginBottom: 48 }}>
      {title && <span className="pill-title">{title.toUpperCase()}</span>}
      <div
        className="card"
        style={{
          marginTop: title ? 16 : 0,
          padding: 0,
          overflow: "hidden",
          background: "#fff",
        }}
      >
        <table style={{ width: "100%", borderCollapse: "collapse" }}>
          {headerRows.length > 0 && (
            <thead>
              {headerRows.map((r) => (
                <tr key={`h-${r.order}`}>
                  {Array.from({ length: colCount }).map((_, col) => {
                    const cell = r.cells[col] ?? "";
                    return (
                      <th
                        key={col}
                        scope="col"
                        style={{ ...thStyle, textAlign: alignFor(cell, true, col) }}
                      >
                        {cell}
                      </th>
                    );
                  })}
                </tr>
              ))}
            </thead>
          )}
          <tbody>
            {dataRows.map((r, i) => (
              <tr
                key={`d-${r.order}`}
                style={{ borderTop: i > 0 ? "1px solid rgba(10,10,10,0.08)" : "none" }}
              >
                {Array.from({ length: colCount }).map((_, col) => {
                  const cell = r.cells[col] ?? "";
                  return (
                    <td
                      key={col}
                      style={{
                        ...tdStyle,
                        textAlign: alignFor(cell, false, col),
                        fontWeight: col === 0 ? 600 : 400,
                      }}
                    >
                      {renderCell(cell, false)}
                    </td>
                  );
                })}
              </tr>
            ))}
            {showTotal && totals && (
              <tr
                style={{
                  borderTop: "2px solid var(--chirri-black)",
                  background: "var(--chirri-paper)",
                }}
              >
                {totals.map((cell, col) => (
                  <td
                    key={col}
                    style={{
                      ...tdStyle,
                      textAlign: col === 0 ? "left" : "right",
                      fontWeight: 800,
                    }}
                  >
                    {cell}
                  </td>
                ))}
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </section>
  );
}
