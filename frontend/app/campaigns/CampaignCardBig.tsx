import Link from "next/link";
import type { CampaignDto } from "@/lib/api";
import { formatPeriod, formatReportDate } from "@/lib/format";
import { statusPillFor } from "@/lib/campaign-view";

const PALETTE = [
  "var(--chirri-mint)",
  "var(--chirri-yellow-soft)",
  "var(--chirri-mint-deep)",
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
  const reportCount = campaign.published_report_count;
  const lastReport = campaign.last_published_at
    ? formatReportDate(campaign.last_published_at)
    : null;
  const pill = statusPillFor(campaign);

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
      }}
    >
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
        <div style={{ display: "flex", gap: 28, marginTop: 18, fontSize: 12, fontWeight: 700 }}>
          <span>{reportCount} reportes</span>
          {lastReport && <span>· último {lastReport}</span>}
        </div>
      </div>
      <div style={{ textAlign: "right" }}>
        <span className="btn btn-primary">Abrir →</span>
      </div>
    </Link>
  );
}
