import { notFound, redirect } from "next/navigation";
import { apiFetch, ApiError, type ReportDto } from "@/lib/api";
import { getAccessToken, getCurrentUser } from "@/lib/auth";
import TopBar from "@/components/top-bar";

import HeaderSection from "./sections/HeaderSection";
import IntroText from "./sections/IntroText";
import KpisSummary from "./sections/KpisSummary";
import MonthlyCompare from "./sections/MonthlyCompare";
import YoyComparison from "./sections/YoyComparison";
import NetworkSection from "./sections/NetworkSection";
import BestContentChapter from "./sections/BestContentChapter";
import OneLinkTable from "./sections/OneLinkTable";
import FollowerGrowthSection from "./sections/FollowerGrowthSection";
import Q1RollupTable from "./sections/Q1RollupTable";
import ConclusionsSection from "./sections/ConclusionsSection";

export default async function ReportPage({ params }: { params: { id: string } }) {
  const user = await getCurrentUser();
  if (!user) redirect("/login");

  const token = getAccessToken();
  let report: ReportDto;
  try {
    report = await apiFetch<ReportDto>(`/api/reports/${params.id}/`, { token });
  } catch (err) {
    if (err instanceof ApiError && err.status === 404) notFound();
    console.error("reports_fetch_failed", { id: params.id, err });
    throw err;
  }

  return (
    <>
      <TopBar user={user} active="home" />
      <main className="page" style={{ background: "var(--chirri-pink)" }}>
        <HeaderSection report={report} />
        <IntroText report={report} />
        <KpisSummary report={report} />
        <MonthlyCompare report={report} />
        <YoyComparison report={report} />
        <NetworkSection report={report} network="INSTAGRAM" />
        <NetworkSection report={report} network="TIKTOK" />
        <NetworkSection report={report} network="X" />
        <BestContentChapter report={report} />
        <OneLinkTable report={report} />
        <FollowerGrowthSection report={report} />
        <Q1RollupTable report={report} />
        <ConclusionsSection report={report} />
      </main>
    </>
  );
}
