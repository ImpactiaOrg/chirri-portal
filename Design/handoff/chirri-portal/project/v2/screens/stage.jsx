// stage.jsx v2 — intermediate stage view, standalone (optional; campaign scroll already lists reports)
// Not currently routed to because campaign screen covers this. Kept minimal in case nav lands here.
function StageScreen({ data, campaignId, stageId, go }) {
  const campaign = data.campaigns.find(c => c.id === campaignId);
  const stage = data.stages[stageId];
  const reports = data.reportsByStage[stageId] || [];
  if (!stage || !campaign) {
    return <main className="page"><p>Etapa no encontrada.</p></main>;
  }
  return (
    <main className="page page-wide" style={{background: "var(--chirri-yellow)"}}>
      <section style={{marginBottom: 32}}>
        <div className="eyebrow">{campaign.name} · Acto {stage.num}</div>
        <h1 className="font-display" style={{fontSize: 96, lineHeight: 0.88, letterSpacing: "-0.03em", margin: "8px 0 0", textTransform: "lowercase"}}>
          {stage.name.toLowerCase()}.
        </h1>
        <p style={{fontSize: 16, maxWidth: 640, marginTop: 14, lineHeight: 1.5, fontWeight: 500}}>{stage.desc}</p>
      </section>

      <section>
        <div className="eyebrow" style={{marginBottom: 12}}>Reportes · {reports.length}</div>
        <div style={{display: "flex", flexDirection: "column", gap: 10}}>
          {reports.map(r => (
            <div key={r.id} onClick={() => go({ screen: "report", campaignId, stageId, reportId: r.id })}
              className="card" style={{cursor: "pointer"}}>
              <div style={{display: "flex", justifyContent: "space-between", alignItems: "center"}}>
                <div style={{fontSize: 16, fontWeight: 700}}>{r.title}</div>
                <span className="tag tag-neutral">{r.type}</span>
              </div>
              <div style={{fontSize: 12, color: "var(--chirri-muted)", marginTop: 4}}>{r.publishedDate} · {r.author}</div>
            </div>
          ))}
        </div>
      </section>
    </main>
  );
}

window.StageScreen = StageScreen;
