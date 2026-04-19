// campaign.jsx v2 — recorrido narrativo (scroll vertical) con stages que listan reportes
function CampaignScreen({ data, campaignId, go }) {
  const campaign = data.campaigns.find(c => c.id === campaignId) || data.campaigns[0];
  const stages = campaign.stages.map(sid => data.stages[sid]).filter(Boolean);
  const isFinished = campaign.status === "finished";

  return (
    <main className="page page-wide" style={{background: isFinished ? "var(--chirri-cream)" : "var(--chirri-yellow)"}}>
      <section style={{marginBottom: 56, position: "relative"}}>
        {!isFinished && <>
          <div className="blob-pink" style={{top: 60, right: -40, transform: "rotate(30deg)"}} />
          <div className="sticker" style={{top: 10, right: 220, fontSize: 38, color: "var(--chirri-mint-deep)", transform: "rotate(15deg)"}}>✳</div>
        </>}

        <div style={{display: "flex", alignItems: "center", gap: 10, marginBottom: 12}}>
          <span className={"status " + (isFinished ? "status-draft" : "status-approved")}>● {isFinished ? "CAMPAÑA TERMINADA" : "ACTIVA"}</span>
          <span style={{fontSize: 12, fontWeight: 700}}>{campaign.period}</span>
        </div>
        <h1 className="font-display" style={{fontSize: 120, lineHeight: 0.85, letterSpacing: "-0.04em", margin: "8px 0 0", textTransform: "lowercase", color: isFinished ? "var(--chirri-muted)" : "var(--chirri-black)"}}>
          {campaign.name.toLowerCase()}.
        </h1>
        <div style={{display: "flex", gap: 40, marginTop: 24, alignItems: "flex-end", flexWrap: "wrap"}}>
          <p style={{fontSize: 17, lineHeight: 1.5, maxWidth: 560, margin: 0, fontWeight: 500}}>{campaign.brief}</p>
          <div style={{display: "flex", gap: 30, marginLeft: "auto"}}>
            <Stat big={String(campaign.pieces)} small="piezas" />
            <Stat big={String(campaign.influencers)} small="influencers" />
            <Stat big={campaign.totalReach} small="alcance" />
          </div>
        </div>
        {isFinished && (
          <div className="anno" style={{background: "white", marginTop: 24, maxWidth: 700}}>
            <div style={{fontSize: 11, fontWeight: 800, letterSpacing: "0.12em", textTransform: "uppercase", marginBottom: 4}}>📁 Archivo</div>
            <div>Esta campaña cerró en {campaign.endDate}. Los reportes de cada etapa siguen disponibles para consulta histórica.</div>
          </div>
        )}
      </section>

      {/* Mini tracker sticky con los actos */}
      <nav style={{position: "sticky", top: 72, zIndex: 10, background: "white", border: "2px solid var(--chirri-black)", borderRadius: 999, padding: 6, display: "flex", gap: 6, marginBottom: 40, boxShadow: "3px 3px 0 var(--chirri-black)"}}>
        {stages.map(s => (
          <a key={s.id} href={"#stage-" + s.id} style={{flex: 1, textAlign: "center", padding: "8px 10px", borderRadius: 999, fontSize: 12, fontWeight: 700, textDecoration: "none", color: "var(--chirri-black)"}}>
            <span style={{fontFamily: "var(--font-mono)", opacity: 0.5, marginRight: 6}}>{s.num}</span>
            {s.name}
          </a>
        ))}
      </nav>

      {/* Un bloque grande por acto — en orden inverso: la más reciente primero */}
      {[...stages].reverse().map((s, idx) => {
        const reports = data.reportsByStage[s.id] || [];
        return (
          <section key={s.id} id={"stage-" + s.id} style={{paddingTop: 40, paddingBottom: 56, borderTop: idx > 0 ? "3px solid var(--chirri-black)" : "none"}}>
            <div style={{display: "grid", gridTemplateColumns: "260px 1fr", gap: 40, alignItems: "start"}}>
              <div style={{position: "sticky", top: 150}}>
                <div className="chapter-num" style={{fontSize: 120, color: "var(--chirri-pink-deep)", lineHeight: 1}}>{s.num}</div>
                <h2 className="font-display" style={{fontSize: 48, lineHeight: 0.92, letterSpacing: "-0.03em", margin: "4px 0 10px", textTransform: "lowercase", wordBreak: "break-word", overflowWrap: "break-word", hyphens: "auto"}}>{s.name.toLowerCase()}</h2>
                <div style={{fontSize: 12, fontWeight: 700, marginBottom: 10}}>{s.period}</div>
                <span className={"status " + (s.status === "active" ? "status-approved" : s.status === "finished" ? "status-draft" : "status-published")}>
                  ● {s.status === "active" ? "EN CURSO" : s.status === "finished" ? "CERRADA" : "PLANIFICADA"}
                </span>
                <p style={{fontSize: 14, lineHeight: 1.5, marginTop: 14, fontWeight: 500}}>{s.desc}</p>
                <div style={{display: "flex", gap: 16, marginTop: 14, fontFamily: "var(--font-mono)", fontSize: 12, fontWeight: 700}}>
                  <span>{s.reach} reach</span><span>· {s.pieces} piezas</span>
                </div>
              </div>

              <div>
                <div className="eyebrow" style={{marginBottom: 12}}>Reportes de esta etapa · {reports.length}</div>
                {reports.length > 0 ? (
                  <div style={{display: "flex", flexDirection: "column", gap: 10}}>
                    {reports.map(r => (
                      <ReportRow key={r.id} r={r} onOpen={() => go({ screen: "report", campaignId: campaign.id, stageId: s.id, reportId: r.id })} />
                    ))}
                  </div>
                ) : (
                  <div className="card card-flat" style={{textAlign: "center", padding: 28, background: "white"}}>
                    <div className="font-display" style={{fontSize: 24, textTransform: "lowercase", color: "var(--chirri-muted)"}}>sin reportes todavía.</div>
                  </div>
                )}
              </div>
            </div>
          </section>
        );
      })}
    </main>
  );
}

function ReportRow({ r, onOpen }) {
  const typeLabel = { general: "GENERAL", influencers: "INFLUENCERS", cierre: "CIERRE DE ETAPA", plan: "PLAN", mensual: "MENSUAL" };
  const typeBg = { general: "var(--chirri-yellow)", influencers: "#D4B8FF", cierre: "var(--chirri-mint)", plan: "white", mensual: "var(--chirri-pink)" };
  const isDraft = r.status === "draft";
  return (
    <div onClick={onOpen}
      style={{
        background: "white", border: "2px solid var(--chirri-black)",
        borderRadius: 14, padding: "16px 20px", boxShadow: "3px 3px 0 var(--chirri-black)",
        cursor: isDraft ? "default" : "pointer", display: "grid",
        gridTemplateColumns: "110px minmax(0, 1fr) 90px 70px", gap: 14, alignItems: "center",
        opacity: isDraft ? 0.55 : 1
      }}
      onMouseEnter={e => { if (!isDraft) { e.currentTarget.style.transform = "translate(-1px,-1px)"; e.currentTarget.style.boxShadow = "4px 4px 0 var(--chirri-pink-deep)"; } }}
      onMouseLeave={e => { if (!isDraft) { e.currentTarget.style.transform = "translate(0,0)"; e.currentTarget.style.boxShadow = "3px 3px 0 var(--chirri-black)"; } }}
    >
      <span className="tag" style={{background: typeBg[r.type] || "white", fontSize: 9.5, justifySelf: "start", whiteSpace: "normal", lineHeight: 1.15, textAlign: "center", padding: "4px 8px"}}>{typeLabel[r.type]}</span>
      <div style={{minWidth: 0}}>
        <div style={{fontSize: 15, fontWeight: 700, lineHeight: 1.2, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap"}}>
          {r.title}
          {r.isLatest && <span style={{marginLeft: 8, fontSize: 10, fontWeight: 800, padding: "2px 8px", background: "var(--chirri-pink-deep)", color: "white", borderRadius: 999, letterSpacing: "0.08em"}}>ÚLTIMO</span>}
        </div>
        <div style={{fontSize: 12, color: "var(--chirri-muted)", marginTop: 4, fontWeight: 500}}>
          Publicado {r.publishedDate} · firma {r.author}
        </div>
      </div>
      <div className="font-mono" style={{fontSize: 13, fontWeight: 700}}>{r.reach || "—"}</div>
      <div style={{textAlign: "right", fontSize: 12, fontWeight: 800, textDecoration: "underline"}}>
        {isDraft ? <span style={{textDecoration: "none", color: "var(--chirri-muted)"}}>BORRADOR</span> : "Leer →"}
      </div>
    </div>
  );
}

function Stat({ big, small }) {
  return (
    <div style={{textAlign: "right"}}>
      <div className="font-display" style={{fontSize: 44, lineHeight: 1, letterSpacing: "-0.03em"}}>{big}</div>
      <div style={{fontSize: 11, letterSpacing: "0.12em", textTransform: "uppercase", fontWeight: 800, marginTop: 4}}>{small}</div>
    </div>
  );
}

window.CampaignScreen = CampaignScreen;
