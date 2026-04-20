import { notFound, redirect } from "next/navigation";
import { apiFetch, ApiError, type CampaignDetailDto } from "@/lib/api";
import { getAccessToken, getCurrentUser } from "@/lib/auth";
import TopBar from "@/components/top-bar";

import CampaignHeader from "./sections/CampaignHeader";
import StagesTimeline from "./sections/StagesTimeline";

export default async function CampaignDetailPage({
  params,
}: {
  params: { id: string };
}) {
  const user = await getCurrentUser();
  if (!user) redirect("/login");

  const token = getAccessToken();
  let campaign: CampaignDetailDto;
  try {
    campaign = await apiFetch<CampaignDetailDto>(`/api/campaigns/${params.id}/`, { token });
  } catch (err) {
    if (err instanceof ApiError && err.status === 404) notFound();
    console.error("campaigns_detail_fetch_failed", { id: params.id, err });
    throw err;
  }

  return (
    <>
      <TopBar user={user} active="campaigns" />
      <main className="page page-wide" style={{ background: "var(--chirri-pink)" }}>
        <CampaignHeader campaign={campaign} clientName={user.client?.name ?? "—"} />
        <StagesTimeline stages={campaign.stages_with_reports} />
      </main>
    </>
  );
}
