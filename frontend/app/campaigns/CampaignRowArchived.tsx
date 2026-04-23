import Link from "next/link";
import type { CampaignDto } from "@/lib/api";
import { formatPeriod, formatReportDate } from "@/lib/format";

type Props = {
  campaign: CampaignDto;
};

export default function CampaignRowArchived({ campaign }: Props) {
  const period = formatPeriod(
    campaign.start_date,
    campaign.end_date,
    campaign.is_ongoing_operation,
  );
  const reportCount = campaign.published_report_count;
  const lastReport = campaign.last_published_at
    ? formatReportDate(campaign.last_published_at)
    : null;
  const briefShort = campaign.brief.length > 80
    ? `${campaign.brief.slice(0, 80)}…`
    : campaign.brief;

  return (
    <Link
      href={`/campaigns/${campaign.id}`}
      className="card-link campaign-row-archived"
      style={{
        background: "white",
        border: "2px solid var(--chirri-black)",
        borderRadius: 14,
        padding: "16px 22px",
        boxShadow: "2px 2px 0 var(--chirri-black)",
        display: "grid",
        gridTemplateColumns: "1fr 200px 140px 140px 80px",
        alignItems: "center",
        gap: 20,
        textDecoration: "none",
        color: "inherit",
        opacity: 0.88,
      }}
    >
      <div>
        <div
          className="font-display"
          style={{ fontSize: 24, lineHeight: 1, textTransform: "lowercase" }}
        >
          {campaign.name.toLowerCase()}
        </div>
        <div
          style={{
            fontSize: 12,
            color: "var(--chirri-muted)",
            marginTop: 4,
            fontWeight: 500,
          }}
        >
          {briefShort}
        </div>
      </div>
      <div style={{ fontSize: 12, fontWeight: 700 }}>{period}</div>
      <div style={{ fontSize: 12, fontWeight: 700 }}>{reportCount} reportes</div>
      <div style={{ fontSize: 11, fontWeight: 600, color: "var(--chirri-muted)" }}>
        {lastReport ? `último ${lastReport}` : ""}
      </div>
      <div style={{ textAlign: "right", fontWeight: 800, fontSize: 12, textDecoration: "underline" }}>
        Abrir →
      </div>
    </Link>
  );
}
