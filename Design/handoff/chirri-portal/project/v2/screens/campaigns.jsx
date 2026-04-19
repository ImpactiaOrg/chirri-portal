// campaigns.jsx — lista de campañas activas y terminadas
function CampaignsScreen({ data, go }) {
  const active = data.campaigns.filter(c => c.status === "active");
  const finished = data.campaigns.filter(c => c.status === "finished");

  return (
    <main className="page page-wide" style={{background: "var(--chirri-pink)"}}>
      <section style={{marginBottom: 40}}>
        <div className="eyebrow">Chirri Portal · Balanz</div>
        <h1 className="font-display" style={{fontSize: 96, lineHeight: 0.9, letterSpacing: "-0.03em", margin: "8px 0 0", textTransform: "lowercase"}}>
          campañas.
        </h1>
        <p style={{fontSize: 16, maxWidth: 620, marginTop: 14, lineHeight: 1.5, fontWeight: 500}}>
          Las activas arriba. Abajo quedan archivadas las terminadas — podés abrir cualquiera para ver el cierre y los reportes de esa etapa.
        </p>
      </section>

      <section style={{marginBottom: 48}}>
        <div style={{display: "flex", alignItems: "center", gap: 14, marginBottom: 20}}>
          <Pill color="mint">ACTIVAS · {active.length}</Pill>
        </div>
        <div style={{display: "flex", flexDirection: "column", gap: 20}}>
          {active.map(c => <CampaignCardBig key={c.id} c={c} go={go} />)}
        </div>
      </section>

      <section style={{borderTop: "3px solid var(--chirri-black)", paddingTop: 36, marginTop: 48}}>
        <div style={{display: "flex", alignItems: "center", gap: 14, marginBottom: 20}}>
          <Pill color="white">ARCHIVO · {finished.length}</Pill>
          <span style={{fontSize: 12, fontWeight: 600, color: "var(--chirri-muted)"}}>Campañas terminadas</span>
        </div>
        <div style={{display: "flex", flexDirection: "column", gap: 10}}>
          {finished.map(c => <CampaignRow key={c.id} c={c} go={go} />)}
        </div>
      </section>
    </main>
  );
}

function CampaignCardBig({ c, go }) {
  return (
    <div onClick={() => go({ screen: "campaign", campaignId: c.id })}
      style={{
        background: c.heroColor, border: "2.5px solid var(--chirri-black)",
        borderRadius: 22, padding: 36, boxShadow: "4px 4px 0 var(--chirri-black)",
        cursor: "pointer", position: "relative", overflow: "hidden",
        display: "grid", gridTemplateColumns: "1fr auto", gap: 40, alignItems: "end"
      }}
      onMouseEnter={e => e.currentTarget.style.boxShadow = "6px 6px 0 var(--chirri-pink-deep)"}
      onMouseLeave={e => e.currentTarget.style.boxShadow = "4px 4px 0 var(--chirri-black)"}
    >
      <div className="blob-mint" style={{top: -40, right: 80, transform: "rotate(-20deg)", opacity: 0.5}} />
      <div style={{position: "relative"}}>
        <div style={{display: "flex", alignItems: "center", gap: 10, marginBottom: 12}}>
          <span className="status status-approved">● ACTIVA</span>
          <span style={{fontSize: 12, fontWeight: 700}}>{c.period}</span>
        </div>
        <h2 className="font-display" style={{fontSize: 64, lineHeight: 0.88, letterSpacing: "-0.03em", margin: "0 0 10px", textTransform: "lowercase"}}>
          {c.name.toLowerCase()}
        </h2>
        <p style={{fontSize: 15, maxWidth: 520, lineHeight: 1.5, fontWeight: 500}}>{c.brief}</p>
        <div style={{display: "flex", gap: 28, marginTop: 18, fontSize: 12, fontWeight: 700}}>
          <span>{c.pieces} piezas</span>
          <span>· {c.influencers} influencers</span>
          <span>· último reporte {c.lastReportDate}</span>
        </div>
      </div>
      <div style={{textAlign: "right", position: "relative"}}>
        <div style={{fontSize: 10, letterSpacing: "0.14em", fontWeight: 800, textTransform: "uppercase"}}>Alcance total</div>
        <div className="font-display" style={{fontSize: 72, lineHeight: 1, letterSpacing: "-0.03em"}}>{c.totalReach}</div>
        <button className="btn btn-primary" style={{marginTop: 14}}>Abrir →</button>
      </div>
    </div>
  );
}

function CampaignRow({ c, go }) {
  return (
    <div onClick={() => go({ screen: "campaign", campaignId: c.id })}
      style={{
        background: "white", border: "2px solid var(--chirri-black)",
        borderRadius: 14, padding: "16px 22px", boxShadow: "2px 2px 0 var(--chirri-black)",
        cursor: "pointer",
        display: "grid", gridTemplateColumns: "1fr 200px 120px 120px 80px",
        alignItems: "center", gap: 20,
        opacity: 0.88
      }}
      onMouseEnter={e => { e.currentTarget.style.opacity = "1"; e.currentTarget.style.transform = "translate(-1px,-1px)"; e.currentTarget.style.boxShadow = "3px 3px 0 var(--chirri-black)"; }}
      onMouseLeave={e => { e.currentTarget.style.opacity = "0.88"; e.currentTarget.style.transform = "translate(0,0)"; e.currentTarget.style.boxShadow = "2px 2px 0 var(--chirri-black)"; }}
    >
      <div>
        <div className="font-display" style={{fontSize: 24, lineHeight: 1, textTransform: "lowercase"}}>{c.name.toLowerCase()}</div>
        <div style={{fontSize: 12, color: "var(--chirri-muted)", marginTop: 4, fontWeight: 500}}>{c.brief.slice(0, 80)}…</div>
      </div>
      <div style={{fontSize: 12, fontWeight: 700}}>{c.period}</div>
      <div className="font-display" style={{fontSize: 22, letterSpacing: "-0.02em"}}>{c.totalReach}</div>
      <div style={{fontSize: 11, fontWeight: 600, color: "var(--chirri-muted)"}}>{c.lastReportDate}</div>
      <div style={{textAlign: "right", fontWeight: 800, fontSize: 12, textDecoration: "underline"}}>Abrir →</div>
    </div>
  );
}

window.CampaignsScreen = CampaignsScreen;
