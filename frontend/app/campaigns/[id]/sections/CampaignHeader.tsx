import Link from "next/link";
import type { CampaignDetailDto } from "@/lib/api";
import { formatPeriod } from "@/lib/format";

const STATUS_PILL: Record<
  CampaignDetailDto["status"],
  { label: string; className: string }
> = {
  ACTIVE: { label: "ACTIVA", className: "status status-approved" },
  FINISHED: { label: "TERMINADA", className: "status status-archived" },
  PAUSED: { label: "PAUSADA", className: "status status-paused" },
};

type Props = {
  campaign: CampaignDetailDto;
  clientName: string;
};

export default function CampaignHeader({ campaign, clientName }: Props) {
  const period = formatPeriod(
    campaign.start_date,
    campaign.end_date,
    campaign.is_ongoing_operation,
  );
  const pill = STATUS_PILL[campaign.status];

  return (
    <header style={{ marginBottom: 40 }}>
      <nav className="eyebrow" aria-label="Breadcrumb">
        Chirri Portal · {clientName} ·{" "}
        <Link href="/campaigns" style={{ textDecoration: "underline" }}>
          campañas
        </Link>
      </nav>
      <h1
        className="font-display"
        style={{
          fontSize: 96,
          lineHeight: 0.9,
          letterSpacing: "-0.03em",
          margin: "8px 0 0",
          textTransform: "lowercase",
        }}
      >
        {campaign.name.toLowerCase()}
      </h1>
      <div style={{ display: "flex", gap: 14, alignItems: "center", marginTop: 14 }}>
        <span className={pill.className} aria-label={`Estado: ${pill.label.toLowerCase()}`}>
          ● {pill.label}
        </span>
        <span style={{ fontSize: 13, fontWeight: 700 }}>{period}</span>
      </div>
      {campaign.brief && (
        <p style={{ fontSize: 16, maxWidth: 720, marginTop: 18, lineHeight: 1.5, fontWeight: 500 }}>
          {campaign.brief}
        </p>
      )}
    </header>
  );
}
