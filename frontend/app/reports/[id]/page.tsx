import { Fragment } from "react";
import { notFound, redirect } from "next/navigation";
import { apiFetch, ApiError, type ReportDto } from "@/lib/api";
import { getAccessToken, getCurrentUser } from "@/lib/auth";
import TopBar from "@/components/top-bar";
import Breadcrumb from "@/components/breadcrumb";
import { reportDetailCrumbs } from "@/lib/breadcrumbs";

import HeaderSection from "./sections/HeaderSection";
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
      <TopBar user={user} active="campaigns" />
      <Breadcrumb
        crumbs={reportDetailCrumbs(user, {
          brandName: report.brand_name,
          campaignId: report.campaign_id,
          campaignName: report.campaign_name,
          stageId: report.stage_id,
          stageName: report.stage_name,
        })}
      />
      <main className="page" style={{ background: "var(--chirri-pink)" }}>
        <HeaderSection report={report} />
        {report.blocks.length === 0 ? (
          <>
            <ConclusionsSection report={report} />
            <section
              data-testid="report-empty-state"
              style={{
                marginBottom: 48,
                padding: 24,
                border: "2px dashed rgba(0,0,0,0.25)",
                borderRadius: 12,
                color: "rgba(0,0,0,0.65)",
                textAlign: "center",
              }}
            >
              Este reporte aún no tiene contenido cargado.
            </section>
          </>
        ) : (
          (() => {
            const kpiIdx = report.blocks.findIndex((b) => b.type === "KPI_GRID");
            // Conclusions land right after the first KPI_GRID block so the
            // takeaway sits next to the top-line numbers. When the report has
            // no KPI_GRID, fall through and render conclusions before the
            // block list so it stays at the top of the page.
            return (
              <>
                {kpiIdx === -1 && <ConclusionsSection report={report} />}
                {report.blocks.map((block, i) => (
                  <Fragment key={block.id}>
                    <BlockRenderer block={block} report={report} />
                    {i === kpiIdx && <ConclusionsSection report={report} />}
                  </Fragment>
                ))}
              </>
            );
          })()
        )}
      </main>
    </>
  );
}
