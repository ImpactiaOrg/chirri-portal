import { notFound, redirect } from "next/navigation";
import { apiFetch, ApiError, type CampaignDetailDto } from "@/lib/api";
import { getAccessToken, getCurrentUser } from "@/lib/auth";
import TopBar from "@/components/top-bar";
import Breadcrumb from "@/components/breadcrumb";
import { campaignDetailCrumbs } from "@/lib/breadcrumbs";

import CampaignHeader from "./sections/CampaignHeader";
import StagesTimeline from "./sections/StagesTimeline";
import StagesTracker from "./sections/StagesTracker";

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
      <Breadcrumb crumbs={campaignDetailCrumbs(user, campaign.brand_name, campaign.name)} />
      <main
        className="page page-wide"
        style={{ background: "var(--chirri-yellow)", minHeight: "100vh" }}
      >
        <CampaignHeader campaign={campaign} />
        <StagesTracker stages={campaign.stages_with_reports} />
        <StagesTimeline stages={campaign.stages_with_reports} />
      </main>
    </>
  );
}
