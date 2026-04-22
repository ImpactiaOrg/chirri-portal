import type { StageWithReportsDto } from "@/lib/api";

export default function StagesTracker({
  stages,
}: {
  stages: StageWithReportsDto[];
}) {
  if (stages.length === 0) return null;

  return (
    <nav
      aria-label="Etapas de la campaña"
      style={{
        position: "sticky",
        top: 72,
        zIndex: 10,
        background: "white",
        border: "2px solid var(--chirri-black)",
        borderRadius: 999,
        padding: 6,
        display: "flex",
        gap: 6,
        marginBottom: 40,
        boxShadow: "3px 3px 0 var(--chirri-black)",
      }}
    >
      {stages.map((stage) => (
        <a
          key={stage.id}
          href={`#stage-${stage.id}`}
          style={{
            flex: 1,
            textAlign: "center",
            padding: "8px 10px",
            borderRadius: 999,
            fontSize: 12,
            fontWeight: 700,
            textDecoration: "none",
            color: "var(--chirri-black)",
          }}
        >
          <span
            style={{
              fontFamily: "var(--font-mono)",
              opacity: 0.5,
              marginRight: 6,
            }}
          >
            {String(stage.order).padStart(2, "0")}
          </span>
          {stage.name}
        </a>
      ))}
    </nav>
  );
}
