function InfluencerScreen({ data, handle, go }) {
  const inf = data.topInfluencers.find(i => i.handle === handle) || data.topInfluencers[0];
  const narrativeName = { awareness: "Awareness", educacion: "Educación", validacion: "Validación", conversion: "Conversión" };

  return (
    <main className="page" style={{background: "var(--chirri-pink)"}}>
      <button className="btn btn-sm" onClick={() => go({ screen: "campaign", campaignId: "ahorrista-inversor" })} style={{marginBottom: 20}}>← Volver a campaña</button>

      <section className="section-hero" style={{background: inf.avatarColor, marginBottom: 40}}>
        <div className="blob-yellow" style={{top: -40, right: -30, transform: "rotate(20deg)"}} />
        <div className="sticker" style={{bottom: 30, left: 40, fontSize: 30, color: "var(--chirri-mint-deep)", transform: "rotate(-12deg)"}}>✳</div>

        <div style={{position: "relative", display: "flex", gap: 36, alignItems: "center", flexWrap: "wrap"}}>
          <div style={{width: 200, height: 200, background: "white", border: "2.5px solid var(--chirri-black)", borderRadius: 20, display: "flex", alignItems: "center", justifyContent: "center", fontFamily: "var(--font-display)", fontSize: 120, boxShadow: "4px 4px 0 var(--chirri-black)"}}>
            {inf.initial}
          </div>
          <div style={{flex: 1, minWidth: 280}}>
            <div className="eyebrow">Influencer · {inf.network}</div>
            <h1 className="font-display" style={{fontSize: 80, lineHeight: 0.88, letterSpacing: "-0.03em", margin: "8px 0", textTransform: "lowercase"}}>
              {inf.name.toLowerCase()}
            </h1>
            <div style={{fontSize: 16, fontWeight: 700}}>{inf.handle} · {inf.followers} seguidores</div>
            <div style={{marginTop: 14, display: "flex", gap: 10, flexWrap: "wrap"}}>
              <StageTag id={inf.stage} name={narrativeName[inf.stage]} />
              <span className="tag">{inf.narrative}</span>
            </div>
          </div>
        </div>
      </section>

      <section style={{marginBottom: 40}}>
        <div style={{display: "flex", justifyContent: "center", marginBottom: 24}}>
          <Pill color="mint">PERFORMANCE MARZO</Pill>
        </div>
        <div className="grid-4">
          <div className="kpi"><div className="kpi-label">Reach</div><div className="kpi-value">{inf.reach}</div></div>
          <div className="kpi"><div className="kpi-label">Views</div><div className="kpi-value">{inf.views}</div></div>
          <div className="kpi"><div className="kpi-label">Likes</div><div className="kpi-value">{inf.likes}</div></div>
          <div className="kpi"><div className="kpi-label">Coments</div><div className="kpi-value">{inf.comments}</div></div>
        </div>
      </section>

      <section style={{display: "grid", gridTemplateColumns: "1fr 1fr", gap: 24, marginBottom: 40}}>
        <div className="card card-mint">
          <div className="eyebrow">Línea narrativa</div>
          <h3 className="font-display" style={{fontSize: 32, lineHeight: 1, margin: "8px 0 14px", textTransform: "lowercase"}}>"{inf.narrative}"</h3>
          <p style={{fontSize: 15, lineHeight: 1.5, fontWeight: 500}}>{inf.caption}</p>
        </div>
        <div className="card card-yellow">
          <div className="eyebrow">Observación del equipo</div>
          <p style={{fontSize: 16, lineHeight: 1.5, fontWeight: 500, marginTop: 8}}>{inf.notes}</p>
        </div>
      </section>

      <section>
        <div style={{display: "flex", justifyContent: "center", marginBottom: 24}}>
          <Pill color="yellow">INVERSIÓN · RESULTADOS</Pill>
        </div>
        <div className="grid-4">
          <div className="card"><div className="eyebrow">Fee</div><div className="font-display" style={{fontSize: 28, marginTop: 6}}>{inf.fee}</div></div>
          <div className="card"><div className="eyebrow">CPM</div><div className="font-display" style={{fontSize: 28, marginTop: 6}}>{inf.cpm}</div></div>
          <div className="card card-pink"><div className="eyebrow">Posts</div><div className="font-display" style={{fontSize: 28, marginTop: 6}}>{inf.posts}</div></div>
          <div className="card card-mint"><div className="eyebrow">Etapa</div><div className="font-display" style={{fontSize: 22, marginTop: 6, textTransform: "lowercase"}}>{narrativeName[inf.stage].toLowerCase()}</div></div>
        </div>
      </section>
    </main>
  );
}

window.InfluencerScreen = InfluencerScreen;
