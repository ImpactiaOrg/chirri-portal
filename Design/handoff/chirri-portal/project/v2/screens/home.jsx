// home.jsx v2 — mantiene la home que le gusta, pero linkea al último reporte published
function HomeScreen({ data, go }) {
  const { client, history } = data;
  const activeCampaign = data.campaigns.find(c => c.status === "active");
  const latestReport = data.reportsByStage.validacion.find(r => r.isLatest) || data.reportsByStage.validacion[0];
  const latestStage = data.stages[latestReport ? "validacion" : "educacion"];
  const older = history.slice(1);

  const openLatest = () => go({ screen: "report", campaignId: activeCampaign.id, stageId: latestStage.id, reportId: latestReport.id });

  return (
    <main className="page" style={{background: "var(--chirri-pink)"}}>
      <section style={{marginBottom: 40, display: "flex", alignItems: "flex-end", justifyContent: "space-between", gap: 40, flexWrap: "wrap"}}>
        <div>
          <div className="eyebrow">Chirri Portal · {client.name}</div>
          <h1 className="font-display" style={{fontSize: 88, lineHeight: 0.9, letterSpacing: "-0.03em", margin: "8px 0 0", textTransform: "lowercase"}}>
            buen día,<br/>belén.
          </h1>
          <p style={{fontSize: 16, maxWidth: 520, marginTop: 16, lineHeight: 1.5, fontWeight: 500}}>
            Cerramos <b>marzo</b>. Fue el mes más fuerte del trimestre. Te lo dejamos listo acá abajo.
          </p>
        </div>
        <div className="chirri-note" style={{maxWidth: 360}}>
          "Este mes nos sorprendió Sofi. El post del 14 rompió todo. Miralo."
          <span className="sig">— VICKY · 31 MAR · 18:42</span>
        </div>
      </section>

      {/* Latest featured report */}
      <section onClick={openLatest} className="section-hero"
        style={{cursor: "pointer", background: "var(--chirri-yellow)", padding: 48}}
      >
        <div className="blob-mint" style={{top: -40, right: 80, transform: "rotate(-20deg)"}} />
        <div className="blob-pink" style={{bottom: -60, left: -40, transform: "rotate(20deg)"}} />
        <div className="sticker" style={{top: 30, right: 40, fontSize: 38, color: "var(--chirri-mint-deep)", transform: "rotate(12deg)"}}>✳</div>

        <div style={{position: "relative", display: "grid", gridTemplateColumns: "1fr auto", gap: 40, alignItems: "end"}}>
          <div>
            <Pill color="black" style={{background: "var(--chirri-black)", color: "var(--chirri-yellow)", boxShadow: "3px 3px 0 var(--chirri-pink-deep)"}}>ÚLTIMO REPORTE</Pill>
            <h2 className="font-display" style={{fontSize: 120, lineHeight: 0.85, letterSpacing: "-0.04em", margin: "24px 0 0", textTransform: "lowercase"}}>
              marzo <span style={{color: "var(--chirri-pink-deep)"}}>2026</span>
            </h2>
            <div style={{display: "flex", gap: 10, alignItems: "center", marginTop: 12, flexWrap: "wrap"}}>
              <span className="tag">{activeCampaign.name}</span>
              <span style={{fontSize: 12, fontWeight: 700}}>· Etapa {latestStage.name}</span>
              <span style={{fontSize: 12, fontWeight: 600}}>· Firma {latestReport.author}</span>
            </div>
            <p style={{fontSize: 18, maxWidth: 560, marginTop: 16, lineHeight: 1.5, fontWeight: 500}}>
              Mes de consolidación. La Validación con testimonios empujó — Sofi, Nacho y Marti combinaron <b>2.43M de alcance</b>.
            </p>
          </div>
          <div style={{display: "flex", flexDirection: "column", gap: 20, alignItems: "flex-end", minWidth: 220, position: "relative"}}>
            <div style={{textAlign: "right"}}>
              <div style={{fontSize: 10, letterSpacing: "0.14em", fontWeight: 800, textTransform: "uppercase"}}>Total reach</div>
              <div className="font-display" style={{fontSize: 96, lineHeight: 1, letterSpacing: "-0.04em"}}>
                2.84<span style={{fontSize: 36}}>M</span>
              </div>
              <div className="font-mono" style={{fontSize: 13, color: "var(--organic)", marginTop: 4, fontWeight: 700}}>▲ 12.4% vs feb</div>
            </div>
            <button className="btn btn-primary">Leer reporte →</button>
          </div>
        </div>
      </section>

      {/* Shortcut grid */}
      <section className="grid-3" style={{marginBottom: 48}}>
        <div className="card card-pink" onClick={() => go({ screen: "campaigns" })} style={{cursor: "pointer"}}>
          <div className="eyebrow">Tus campañas</div>
          <h3 className="font-display" style={{fontSize: 34, margin: "8px 0", lineHeight: 1, textTransform: "lowercase"}}>1 activa<br/>+ 2 en archivo</h3>
          <p style={{fontSize: 13, lineHeight: 1.5, margin: "0 0 14px", fontWeight: 500}}>Mirá el recorrido completo o entrá a una campaña terminada.</p>
          <span style={{fontSize: 13, fontWeight: 800, textDecoration: "underline"}}>Ver campañas →</span>
        </div>
        <div className="card card-mint" onClick={() => go({ screen: "campaign", campaignId: activeCampaign.id })} style={{cursor: "pointer"}}>
          <div className="eyebrow">Campaña activa</div>
          <h3 className="font-display" style={{fontSize: 34, margin: "8px 0", lineHeight: 1, textTransform: "lowercase"}}>de ahorrista<br/>a inversor</h3>
          <p style={{fontSize: 13, lineHeight: 1.5, margin: "0 0 14px", fontWeight: 500}}>4 actos, 6 influencers, 35 piezas. Todos los reportes por etapa.</p>
          <span style={{fontSize: 13, fontWeight: 800, textDecoration: "underline"}}>Abrir recorrido →</span>
        </div>
        <div className="card" style={{background: "var(--chirri-paper)", opacity: 0.72, cursor: "not-allowed"}}>
          <div style={{display: "flex", justifyContent: "space-between", alignItems: "center"}}>
            <div className="eyebrow">Cronograma</div>
            <span style={{fontSize: 9, fontWeight: 800, padding: "2px 8px", background: "var(--chirri-muted)", color: "white", borderRadius: 999, letterSpacing: "0.12em"}}>SOON</span>
          </div>
          <h3 className="font-display" style={{fontSize: 34, margin: "8px 0", lineHeight: 1, textTransform: "lowercase", color: "var(--chirri-muted)"}}>posts por venir</h3>
          <p style={{fontSize: 13, lineHeight: 1.5, margin: "0", fontWeight: 500, color: "var(--chirri-muted)"}}>Vas a poder ver y aprobar el cronograma IG acá. Pronto.</p>
        </div>
      </section>

      {/* History */}
      <section>
        <div style={{display: "flex", alignItems: "center", gap: 16, marginBottom: 24, justifyContent: "space-between", flexWrap: "wrap"}}>
          <Pill color="mint">HISTORIAL</Pill>
          <span style={{fontSize: 13, fontWeight: 500}}>Los últimos 5 meses</span>
        </div>
        <div style={{display: "flex", flexDirection: "column", gap: 10}}>
          {older.map((r, i) => (
            <div key={i} onClick={() => r.reportId ? go({ screen: "report", campaignId: activeCampaign.id, stageId: r.stageId, reportId: r.reportId }) : null}
              style={{
                background: "white", border: "2.5px solid var(--chirri-black)",
                borderRadius: 16, boxShadow: "3px 3px 0 var(--chirri-black)",
                display: "grid", gridTemplateColumns: "220px 1fr 140px 140px 100px",
                alignItems: "center", padding: "18px 24px",
                cursor: r.reportId ? "pointer" : "default", opacity: r.reportId ? 1 : 0.5
              }}
            >
              <div className="font-display" style={{fontSize: 32, lineHeight: 1, textTransform: "lowercase"}}>
                {r.month.toLowerCase()} <span style={{color: "var(--chirri-muted)"}}>{r.year}</span>
              </div>
              <div style={{fontSize: 13, fontWeight: 500}}>
                {r.month === "Febrero" ? "Validación + pico Sofi" : r.month === "Enero" ? "Arranque de campaña" : r.month === "Diciembre" ? "Pre-campaña" : "Harry Potter × Yelmo"}
              </div>
              <div className="font-display" style={{fontSize: 20, letterSpacing: "-0.02em"}}>{r.reach}</div>
              <div className="font-mono" style={{fontSize: 13, fontWeight: 700, color: r.delta.startsWith("+") ? "var(--organic)" : "var(--paid)"}}>
                {r.delta.startsWith("+") ? "▲" : "▼"} {r.delta}
              </div>
              <div style={{textAlign: "right", fontSize: 13, fontWeight: 800, textDecoration: r.reportId ? "underline" : "none"}}>
                {r.reportId ? "Abrir →" : "—"}
              </div>
            </div>
          ))}
        </div>
      </section>
    </main>
  );
}

window.HomeScreen = HomeScreen;
