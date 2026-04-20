import type { StageWithReportsDto } from "@/lib/api";
import StageBlock from "./StageBlock";

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
        {stages.map((stage) => (
          <StageBlock key={stage.id} stage={stage} />
        ))}
      </ol>
    </section>
  );
}
