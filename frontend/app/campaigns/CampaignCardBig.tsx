import Link from "next/link";
import type { CampaignDto } from "@/lib/api";
import { formatCompact } from "@/lib/aggregations";
import { formatPeriod, formatReportDate } from "@/lib/format";
import { statusPillFor } from "@/lib/campaign-view";

const PALETTE = [
  "var(--chirri-yellow)",
  "var(--chirri-pink)",
  "var(--chirri-mint)",
];

type Props = {
  campaign: CampaignDto;
  colorIndex: number;
};

export default function CampaignCardBig({ campaign, colorIndex }: Props) {
  const color = PALETTE[colorIndex % PALETTE.length];
  const period = formatPeriod(
    campaign.start_date,
    campaign.end_date,
    campaign.is_ongoing_operation,
  );
  const lastReport = campaign.last_published_at
    ? formatReportDate(campaign.last_published_at)
    : null;
  const pill = statusPillFor(campaign);
  const reachNum =
    campaign.reach_total !== null && campaign.reach_total !== undefined
      ? Number(campaign.reach_total)
      : null;
  const reachLabel = reachNum && reachNum > 0 ? formatCompact(reachNum) : "—";

  return (
    <Link
      href={`/campaigns/${campaign.id}`}
      className="card-link"
      style={{
        background: color,
        border: "2.5px solid var(--chirri-black)",
        borderRadius: 22,
        padding: 36,
        boxShadow: "4px 4px 0 var(--chirri-black)",
        display: "grid",
        gridTemplateColumns: "1fr auto",
        gap: 40,
        alignItems: "end",
        textDecoration: "none",
        color: "inherit",
        position: "relative",
        overflow: "hidden",
      }}
    >
      <div
        className="blob-mint"
        aria-hidden="true"
        style={{ top: -40, right: 80, transform: "rotate(-20deg)", opacity: 0.5 }}
      />

      <div style={{ position: "relative" }}>
        <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 12 }}>
          <span
            className={pill.className}
            aria-label={`Estado: ${pill.label.toLowerCase()}`}
          >
            ● {pill.label}
          </span>
          <span style={{ fontSize: 12, fontWeight: 700 }}>{period}</span>
        </div>
        <h2
          className="font-display"
          style={{
            fontSize: 64,
            lineHeight: 0.88,
            letterSpacing: "-0.03em",
            margin: "0 0 10px",
            textTransform: "lowercase",
          }}
        >
          {campaign.name.toLowerCase()}
        </h2>
        <p style={{ fontSize: 15, maxWidth: 520, lineHeight: 1.5, fontWeight: 500 }}>
          {campaign.brief}
        </p>
        <div
          style={{
            display: "flex",
            gap: 18,
            marginTop: 18,
            fontSize: 12,
            fontWeight: 700,
            flexWrap: "wrap",
          }}
        >
          <span>— piezas</span>
          <span>· — influencers</span>
          {lastReport && <span>· último reporte {lastReport}</span>}
        </div>
      </div>

      <div style={{ textAlign: "right", position: "relative" }}>
        <div
          style={{
            fontSize: 10,
            letterSpacing: "0.14em",
            fontWeight: 800,
            textTransform: "uppercase",
          }}
        >
          Alcance total
        </div>
        <div
          className="font-display"
          style={{ fontSize: 72, lineHeight: 1, letterSpacing: "-0.03em" }}
          aria-label="Alcance total de la campaña"
        >
          {reachLabel}
        </div>
        <span className="btn btn-primary" style={{ marginTop: 14 }}>
          Abrir →
        </span>
      </div>
    </Link>
  );
}
