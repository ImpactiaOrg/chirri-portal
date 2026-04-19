function CalendarScreen({ data, go }) {
  const { upcoming } = data;
  const [selected, setSelected] = React.useState(0);
  const post = upcoming[selected];

  const statusLabel = { draft: "Borrador", approved: "Aprobado", published: "Publicado" };
  const narrativeName = { awareness: "Awareness", educacion: "Educación", validacion: "Validación", conversion: "Conversión" };

  return (
    <main className="page" style={{background: "var(--chirri-mint)"}}>
      <section style={{marginBottom: 32}}>
        <div className="eyebrow">Cronograma Instagram · Abril 2026</div>
        <h1 className="font-display" style={{fontSize: 88, lineHeight: 0.9, letterSpacing: "-0.03em", margin: "8px 0 0", textTransform: "lowercase"}}>
          lo que <span style={{color: "var(--chirri-pink-deep)"}}>viene</span>.
        </h1>
        <p style={{fontSize: 16, maxWidth: 640, marginTop: 14, lineHeight: 1.5, fontWeight: 500}}>
          Tres posts espaciados cada ~15 días. Los borradores los miramos con vos antes de publicar.
        </p>
      </section>

      <section style={{marginBottom: 40}}>
        <div style={{position: "relative", padding: "28px 20px 12px", background: "white", border: "2.5px solid var(--chirri-black)", borderRadius: 18, boxShadow: "3px 3px 0 var(--chirri-black)"}}>
          <div style={{position: "absolute", left: 80, right: 80, top: 82, height: 3, background: "var(--chirri-black)", borderRadius: 999}} />
          <div style={{display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 20, position: "relative"}}>
            {upcoming.map((p, i) => {
              const active = selected === i;
              return (
                <div key={i} onClick={() => setSelected(i)} style={{cursor: "pointer", display: "flex", flexDirection: "column", alignItems: "center", textAlign: "center"}}>
                  <div className="font-mono" style={{fontSize: 12, fontWeight: 700, marginBottom: 14}}>
                    {p.date} · {p.time}
                  </div>
                  <div style={{
                    width: 28, height: 28, borderRadius: "50%",
                    background: active ? "var(--chirri-pink-deep)" : "white",
                    border: "2.5px solid var(--chirri-black)",
                    marginBottom: 14, transition: "all 160ms"
                  }} />
                  <StageTag id={p.stage} name={narrativeName[p.stage]} />
                  <div style={{fontSize: 14, fontWeight: 800, marginTop: 10}}>{p.format}</div>
                </div>
              );
            })}
          </div>
        </div>
      </section>

      <section style={{display: "grid", gridTemplateColumns: "360px 1fr", gap: 40, alignItems: "start"}}>
        <div style={{position: "sticky", top: 100}}>
          <div style={{border: "2.5px solid var(--chirri-black)", borderRadius: 18, overflow: "hidden", background: "white", boxShadow: "4px 4px 0 var(--chirri-black)"}}>
            <div style={{padding: "12px 14px", display: "flex", alignItems: "center", gap: 10, borderBottom: "2px solid var(--chirri-black)"}}>
              <TenantDot />
              <div>
                <div style={{fontSize: 13, fontWeight: 800}}>balanz</div>
                <div style={{fontSize: 10.5, color: "var(--chirri-muted)"}}>Buenos Aires, AR</div>
              </div>
              <div style={{marginLeft: "auto", fontSize: 18}}>···</div>
            </div>
            <div style={{aspectRatio: "4/5", background: post.stage === "educacion" ? "linear-gradient(135deg, #0B2D5B, #00C9B7)" : post.stage === "validacion" ? "linear-gradient(135deg, #FFB3D1, #F478A8)" : "linear-gradient(135deg, #FFE74C, #A8F0A8)", position: "relative", display: "flex", alignItems: "flex-end", padding: 20, borderBottom: "2px solid var(--chirri-black)"}}>
              <div style={{fontFamily: "var(--font-mono)", fontSize: 10, fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.12em", background: "white", color: "var(--chirri-black)", padding: "4px 10px", borderRadius: 4, border: "1.5px solid var(--chirri-black)"}}>
                {post.format} · placeholder
              </div>
            </div>
            <div style={{padding: "10px 14px", display: "flex", gap: 14, borderBottom: "2px solid var(--chirri-line)"}}>
              <span style={{fontSize: 20}}>♡</span><span style={{fontSize: 20}}>💬</span><span style={{fontSize: 20}}>↗</span>
              <span style={{marginLeft: "auto", fontSize: 20}}>🔖</span>
            </div>
            <div style={{padding: "10px 14px 16px"}}>
              <div style={{fontSize: 13, lineHeight: 1.45}}>
                <b>balanz</b> {post.caption}
              </div>
              <div style={{fontSize: 12, color: "var(--chirri-pink-deep)", marginTop: 6, fontWeight: 700}}>{post.hashtags}</div>
            </div>
          </div>
          <div style={{textAlign: "center", marginTop: 12, fontSize: 11, fontWeight: 700, letterSpacing: "0.12em"}}>VISTA PREVIA · IG FEED</div>
        </div>

        <div style={{display: "flex", flexDirection: "column", gap: 20}}>
          <div>
            <div style={{display: "flex", alignItems: "center", gap: 10, marginBottom: 8, flexWrap: "wrap"}}>
              <span className={"status status-" + post.status}>
                <span style={{width: 6, height: 6, borderRadius: "50%", background: "currentColor"}} />
                {statusLabel[post.status]}
              </span>
              <StageTag id={post.stage} name={narrativeName[post.stage]} />
            </div>
            <h2 className="font-display" style={{fontSize: 56, lineHeight: 0.95, letterSpacing: "-0.03em", margin: "8px 0 4px", textTransform: "lowercase"}}>
              {post.format.toLowerCase()} · {post.date.toLowerCase()}
            </h2>
            <div className="font-mono" style={{fontSize: 13, fontWeight: 600}}>Publica {post.time} · GMT-3</div>
          </div>

          <div className="card">
            <div className="eyebrow">Copy propuesto</div>
            <div style={{fontSize: 16, lineHeight: 1.5, marginTop: 8, fontWeight: 500}}>{post.caption}</div>
            <div style={{fontSize: 13, color: "var(--chirri-pink-deep)", marginTop: 8, fontWeight: 700}}>{post.hashtags}</div>
          </div>

          <div className="anno">
            <div style={{fontSize: 11, fontWeight: 800, letterSpacing: "0.12em", textTransform: "uppercase", marginBottom: 4}}>📌 Nota del equipo</div>
            <div>{post.copy}</div>
          </div>

          <div className="grid-3" style={{gap: 12}}>
            <div className="card card-yellow" style={{padding: 16}}>
              <div className="eyebrow" style={{fontSize: 10}}>Objetivo</div>
              <div style={{fontSize: 15, marginTop: 4, fontWeight: 700}}>
                {post.stage === "awareness" ? "Alcance + FOMO" : post.stage === "educacion" ? "Guardados + autoridad" : post.stage === "validacion" ? "Trust + coms" : "Descargas app"}
              </div>
            </div>
            <div className="card card-pink" style={{padding: 16}}>
              <div className="eyebrow" style={{fontSize: 10}}>Audiencia</div>
              <div style={{fontSize: 15, marginTop: 4, fontWeight: 700}}>25-34 AMBA</div>
            </div>
            <div className="card" style={{padding: 16}}>
              <div className="eyebrow" style={{fontSize: 10}}>Pauta</div>
              <div style={{fontSize: 15, marginTop: 4, fontWeight: 700}}>
                {post.status === "approved" ? "U$S 800" : "A definir"}
              </div>
            </div>
          </div>

          {post.status !== "published" && (
            <div style={{display: "flex", gap: 10, marginTop: 4}}>
              <button className="btn">Pedir cambios</button>
              <button className="btn btn-primary">{post.status === "approved" ? "✓ Aprobado" : "Aprobar post"}</button>
            </div>
          )}
        </div>
      </section>
    </main>
  );
}

window.CalendarScreen = CalendarScreen;
