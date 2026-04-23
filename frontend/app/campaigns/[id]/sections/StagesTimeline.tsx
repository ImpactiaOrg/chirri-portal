import type { StageWithReportsDto } from "@/lib/api";
import StageBlock from "./StageBlock";

function pickLatestReportId(stages: StageWithReportsDto[]): number | null {
  const reports = stages.flatMap((s) => s.reports);
  if (reports.length === 0) return null;
  return reports.reduce((best, r) => {
    const diff = new Date(r.published_at).getTime() - new Date(best.published_at).getTime();
    if (diff > 0) return r;
    if (diff === 0 && r.id > best.id) return r;
    return best;
  }).id;
}

export default function StagesTimeline({
  stages,
}: {
  stages: StageWithReportsDto[];
}) {
  if (stages.length === 0) {
    return (
      <section
        style={{
          padding: 28,
          border: "2px dashed var(--chirri-black)",
          borderRadius: 18,
          background: "rgba(0,0,0,0.03)",
          marginBottom: 40,
        }}
      >
        <p style={{ margin: 0, fontSize: 14, fontWeight: 600 }}>
          Esta campaña todavía no tiene etapas publicadas.
        </p>
      </section>
    );
  }

  const latestReportId = pickLatestReportId(stages);
  const reversed = [...stages].reverse();
  return (
    <section style={{ marginBottom: 40 }}>
      <ol
        style={{
          listStyle: "none",
          padding: 0,
          margin: 0,
          borderBottom: "2px solid var(--chirri-black)",
        }}
      >
        {reversed.map((stage) => (
          <StageBlock key={stage.id} stage={stage} latestReportId={latestReportId} />
        ))}
      </ol>
    </section>
  );
}
