import { notFound, redirect } from "next/navigation";
import { apiFetch, ApiError, type ReportDto } from "@/lib/api";
import { getAccessToken, getCurrentUser } from "@/lib/auth";
import TopBar from "@/components/top-bar";

import HeaderSection from "./sections/HeaderSection";
import IntroText from "./sections/IntroText";
import ConclusionsSection from "./sections/ConclusionsSection";
import BlockRenderer from "./blocks/BlockRenderer";

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
        {report.blocks.map((block) => (
          <BlockRenderer key={block.id} block={block} report={report} />
        ))}
        <ConclusionsSection report={report} />
      </main>
    </>
  );
}
