function CampaignScreen({ data, go, openInfluencer }) {
  const { stages, topInfluencers, pipeline, client } = data;
  const [activeStage, setActiveStage] = React.useState("validacion");

  const influencersByStage = {};
  topInfluencers.forEach(i => {
    if (!influencersByStage[i.stage]) influencersByStage[i.stage] = [];
    influencersByStage[i.stage].push(i);
  });

  const active = stages.find(s => s.id === activeStage);
  const activeInf = influencersByStage[activeStage] || [];

  return (
    <main className="page page-wide" style={{background: "var(--chirri-yellow)"}}>
      <section style={{marginBottom: 48, position: "relative"}}>
        <div className="blob-pink" style={{top: 60, right: -40, transform: "rotate(30deg)"}} />
        <div className="sticker" style={{top: 10, right: 220, fontSize: 38, color: "var(--chirri-mint-deep)", transform: "rotate(15deg)"}}>✳</div>

        <div className="eyebrow">Campaña · {client.name}</div>
        <h1 className="font-display" style={{fontSize: 136, lineHeight: 0.82, letterSpacing: "-0.04em", margin: "12px 0 0", textTransform: "lowercase", position: "relative"}}>
          de <span style={{color: "var(--chirri-pink-deep)"}}>ahorrista</span><br/>
          a <span style={{color: "var(--chirri-pink-deep)"}}>inversor</span>.
        </h1>
        <div style={{display: "flex", gap: 40, marginTop: 32, alignItems: "flex-end", flexWrap: "wrap"}}>
          <p style={{fontSize: 18, lineHeight: 1.5, maxWidth: 560, margin: 0, fontWeight: 500}}>
            La campaña no es una pila de posts — es una <b>historia en 4 actos</b>. Cada influencer entra donde su voz tiene más sentido.
          </p>
          <div style={{display: "flex", gap: 30, marginLeft: "auto"}}>
            <Stat big="35" small="piezas publicadas" />
            <Stat big="6" small="influencers activos" />
            <Stat big="2.84M" small="alcance total" />
          </div>
        </div>
      </section>

      <section style={{marginBottom: 40}}>
        <div style={{display: "flex", justifyContent: "center", marginBottom: 24}}>
          <Pill color="mint">LOS 4 ACTOS</Pill>
        </div>
        <div className="grid-4" style={{gap: 14}}>
          {stages.map((s) => {
            const act = s.id === activeStage;
            return (
              <div key={s.id} onClick={() => setActiveStage(s.id)}
                style={{
                  cursor: "pointer", padding: 20, borderRadius: 16,
                  background: act ? "var(--chirri-black)" : "white",
                  color: act ? "var(--chirri-cream)" : "var(--chirri-black)",
                  border: "2.5px solid var(--chirri-black)",
                  boxShadow: act ? "4px 4px 0 var(--chirri-pink-deep)" : "3px 3px 0 var(--chirri-black)",
                  transition: "all 160ms"
                }}
              >
                <div className="chapter-num" style={{color: act ? "var(--chirri-yellow)" : "var(--chirri-pink-deep)"}}>{s.num}</div>
                <div className="font-display" style={{fontSize: 30, lineHeight: 1, marginTop: 6, textTransform: "lowercase"}}>{s.name.toLowerCase()}</div>
                <div style={{fontSize: 13, lineHeight: 1.4, marginTop: 10, opacity: act ? 0.85 : 0.75, fontWeight: 500}}>{s.desc}</div>
                <div style={{display: "flex", gap: 16, marginTop: 14, fontFamily: "var(--font-mono)", fontSize: 11, fontWeight: 700, opacity: 0.8}}>
                  <span>{s.reach}</span><span>· {s.pieces} piezas</span>
                </div>
              </div>
            );
          })}
        </div>
      </section>

      <section style={{marginBottom: 56}}>
        <div style={{display: "grid", gridTemplateColumns: "1fr 2fr", gap: 40, alignItems: "start"}}>
          <div>
            <Pill color="pink">ACTO {active.num}</Pill>
            <h2 className="font-display" style={{fontSize: 76, lineHeight: 0.95, letterSpacing: "-0.03em", margin: "16px 0", textTransform: "lowercase"}}>
              {active.name.toLowerCase()}
            </h2>
            <p style={{fontSize: 17, lineHeight: 1.5, fontWeight: 500}}>{active.desc}</p>
            <div className="anno" style={{marginTop: 20, background: "white"}}>
              <div style={{fontSize: 11, fontWeight: 800, letterSpacing: "0.12em", textTransform: "uppercase", marginBottom: 4}}>📌 Por qué esta etapa, ahora</div>
              {activeStage === "awareness" && <div>Arrancamos acá porque la audiencia no sabe que querés hablarle. Sembramos curiosidad con voces masivas.</div>}
              {activeStage === "educacion" && <div>Una vez que te vieron, hay que bajar tecnicismos. Marti explica CEDEAR, bonos y FCI sin que te sientas tonto.</div>}
              {activeStage === "validacion" && <div>Acá entra Sofi: testimonio real, primera persona. "Yo tampoco sabía". Es el acto que más conversión arrastra.</div>}
              {activeStage === "conversion" && <div>Cierre con Flor: de la historia al click. CTA claro, asesor como diferencial.</div>}
            </div>
          </div>

          <div>
            <div className="eyebrow" style={{marginBottom: 12}}>Quién cuenta este acto</div>
            {activeInf.length > 0 ? (
              <div style={{display: "flex", flexDirection: "column", gap: 14}}>
                {activeInf.map((inf, i) => (
                  <div key={i} className="inf-card" onClick={() => openInfluencer(inf.handle)}>
                    <div className="inf-avatar" style={{background: inf.avatarColor}}>
                      {inf.initial}
                    </div>
                    <div style={{display: "flex", flexDirection: "column", gap: 6, minWidth: 0}}>
                      <div style={{display: "flex", alignItems: "center", gap: 10, flexWrap: "wrap"}}>
                        <div className="font-display" style={{fontSize: 28, lineHeight: 1, textTransform: "lowercase"}}>{inf.name.toLowerCase()}</div>
                        <span className="tag tag-neutral" style={{fontSize: 10}}>{inf.network}</span>
                      </div>
                      <div style={{fontSize: 13, color: "var(--chirri-muted)", fontWeight: 600}}>{inf.handle} · {inf.followers}</div>
                      <div style={{fontSize: 16, lineHeight: 1.4, fontWeight: 500, marginTop: 4}}>"{inf.caption}"</div>
                      <div style={{display: "flex", gap: 20, marginTop: 6, fontSize: 12, fontWeight: 700, fontFamily: "var(--font-mono)"}}>
                        <span>{inf.reach} reach</span>
                        <span>· {inf.likes} likes</span>
                        <span>· {inf.comments} coms</span>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="card card-pink" style={{textAlign: "center", padding: 32}}>
                <div className="font-display" style={{fontSize: 28, textTransform: "lowercase"}}>
                  este acto todavía no tuvo pieza en marzo.
                </div>
                <div style={{fontSize: 13, marginTop: 8, fontWeight: 600}}>Planeado para abril con @flor.sosa.</div>
              </div>
            )}

            <div style={{marginTop: 28}}>
              <div className="eyebrow" style={{marginBottom: 10}}>En conversación</div>
              <div style={{display: "flex", gap: 10, flexWrap: "wrap"}}>
                {pipeline.map((p, i) => (
                  <div key={i} className="tag tag-neutral" style={{padding: "8px 14px", fontSize: 12}}>
                    {p.handle} · <span style={{opacity: 0.6, marginLeft: 4}}>{p.followers}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      </section>
    </main>
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
