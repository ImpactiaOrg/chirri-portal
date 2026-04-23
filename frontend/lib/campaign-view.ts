import type { CampaignDto, CampaignDetailDto } from "./api";

type Status = CampaignDto["status"];

export const STATUS_PILL: Record<Status, { label: string; className: string }> = {
  ACTIVE: { label: "ACTIVA", className: "status status-approved" },
  FINISHED: { label: "TERMINADA", className: "status status-archived" },
  PAUSED: { label: "PAUSADA", className: "status status-paused" },
};

export function statusPillFor(
  campaign: CampaignDto | CampaignDetailDto,
): { label: string; className: string } {
  return STATUS_PILL[campaign.status];
}
