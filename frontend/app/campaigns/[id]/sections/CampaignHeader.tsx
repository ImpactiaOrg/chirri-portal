import type { CampaignDetailDto } from "@/lib/api";
import { formatPeriod } from "@/lib/format";
import { statusPillFor } from "@/lib/campaign-view";

type Props = {
  campaign: CampaignDetailDto;
};

export default function CampaignHeader({ campaign }: Props) {
  const period = formatPeriod(
    campaign.start_date,
    campaign.end_date,
    campaign.is_ongoing_operation,
  );
  const pill = statusPillFor(campaign);

  return (
    <header style={{ marginBottom: 56, position: "relative" }}>
      <div
        className="blob-pink"
        aria-hidden="true"
        style={{ top: 60, right: -40, transform: "rotate(30deg)" }}
      />
      <span
        className="sticker"
        aria-hidden="true"
        style={{
          top: 10,
          right: 220,
          fontSize: 38,
          color: "var(--chirri-mint-deep)",
          transform: "rotate(15deg)",
        }}
      >
        ✳
      </span>

      <h1
        className="font-display"
        style={{
          position: "relative",
          fontSize: 120,
          lineHeight: 0.85,
          letterSpacing: "-0.04em",
          margin: "8px 0 0",
          textTransform: "lowercase",
        }}
      >
        {campaign.name.toLowerCase()}.
      </h1>

      <div
        style={{
          display: "flex",
          gap: 14,
          alignItems: "center",
          marginTop: 14,
          position: "relative",
        }}
      >
        <span className={pill.className} aria-label={`Estado: ${pill.label.toLowerCase()}`}>
          ● {pill.label}
        </span>
        <span style={{ fontSize: 13, fontWeight: 700 }}>{period}</span>
      </div>

      {campaign.brief && (
        <p
          style={{
            fontSize: 17,
            maxWidth: 560,
            marginTop: 24,
            lineHeight: 1.5,
            fontWeight: 500,
            position: "relative",
          }}
        >
          {campaign.brief}
        </p>
      )}
    </header>
  );
}
