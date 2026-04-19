function HomeScreen({ data, go }) {
  const { client, history } = data;
  const older = history.slice(1);

  return (
    <main className="page" style={{background: "var(--chirri-pink)"}}>
      <section style={{marginBottom: 40, display: "flex", alignItems: "flex-end", justifyContent: "space-between", gap: 40, flexWrap: "wrap"}}>
        <div>
          <div className="eyebrow">Portal {client.name} · Chirri</div>
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

      {/* Latest featured */}
      <section onClick={() => go("report")} className="section-hero"
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
            <p style={{fontSize: 18, maxWidth: 560, marginTop: 16, lineHeight: 1.5, fontWeight: 500}}>
              Mes de consolidación. La Validación con testimonios empujó fuerte — Sofi, Nacho y Marti combinaron <b>2.43M de alcance</b>.
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
            <button className="btn btn-primary">Ver reporte →</button>
          </div>
        </div>
      </section>

      {/* Shortcut grid */}
      <section className="grid-3" style={{marginBottom: 48}}>
        <div className="card card-mint" onClick={() => go("calendar")} style={{cursor: "pointer"}}>
          <div className="eyebrow">Próximamente</div>
          <h3 className="font-display" style={{fontSize: 34, margin: "8px 0", lineHeight: 1, textTransform: "lowercase"}}>3 posts en abril</h3>
          <p style={{fontSize: 13, lineHeight: 1.5, margin: "0 0 14px", fontWeight: 500}}>El calendario de IG. Uno aprobado, dos en borrador.</p>
          <span style={{fontSize: 13, fontWeight: 800, textDecoration: "underline"}}>Ver cronograma →</span>
        </div>
        <div className="card card-pink" onClick={() => go("campaign")} style={{cursor: "pointer"}}>
          <div className="eyebrow">Campaña</div>
          <h3 className="font-display" style={{fontSize: 34, margin: "8px 0", lineHeight: 1, textTransform: "lowercase"}}>de ahorrista<br/>a inversor</h3>
          <p style={{fontSize: 13, lineHeight: 1.5, margin: "0 0 14px", fontWeight: 500}}>4 etapas, 6 influencers, 35 piezas. La historia entera.</p>
          <span style={{fontSize: 13, fontWeight: 800, textDecoration: "underline"}}>Abrir narrativa →</span>
        </div>
        <div className="card card-yellow" onClick={() => go("export")} style={{cursor: "pointer"}}>
          <div className="eyebrow">Export</div>
          <h3 className="font-display" style={{fontSize: 34, margin: "8px 0", lineHeight: 1, textTransform: "lowercase"}}>pdf con<br/>tu marca</h3>
          <p style={{fontSize: 13, lineHeight: 1.5, margin: "0 0 14px", fontWeight: 500}}>Para presentar al directorio. Branding Balanz.</p>
          <span style={{fontSize: 13, fontWeight: 800, textDecoration: "underline"}}>Preparar →</span>
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
            <div key={i} onClick={() => go("report")}
              style={{
                background: "white",
                border: "2.5px solid var(--chirri-black)",
                borderRadius: 16,
                boxShadow: "3px 3px 0 var(--chirri-black)",
                display: "grid",
                gridTemplateColumns: "220px 1fr 140px 140px 100px",
                alignItems: "center",
                padding: "18px 24px",
                cursor: "pointer",
                transition: "transform 120ms"
              }}
              onMouseEnter={e => { e.currentTarget.style.transform = "translate(-1px, -1px)"; e.currentTarget.style.boxShadow = "4px 4px 0 var(--chirri-pink-deep)"; }}
              onMouseLeave={e => { e.currentTarget.style.transform = "translate(0, 0)"; e.currentTarget.style.boxShadow = "3px 3px 0 var(--chirri-black)"; }}
            >
              <div className="font-display" style={{fontSize: 32, lineHeight: 1, textTransform: "lowercase"}}>
                {r.month.toLowerCase()} <span style={{color: "var(--chirri-muted)"}}>{r.year}</span>
              </div>
              <div style={{fontSize: 13, fontWeight: 500}}>
                {r.month === "Febrero" ? "Validación + pico Sofi" : r.month === "Enero" ? "Arranque de campaña" : r.month === "Diciembre" ? "Cierre de año, Awareness" : "Pre-lanzamiento"}
              </div>
              <div className="font-display" style={{fontSize: 20, letterSpacing: "-0.02em"}}>{r.reach}</div>
              <div className="font-mono" style={{fontSize: 13, fontWeight: 700, color: r.delta.startsWith("+") ? "var(--organic)" : "var(--paid)"}}>
                {r.delta.startsWith("+") ? "▲" : "▼"} {r.delta}
              </div>
              <div style={{textAlign: "right", fontSize: 13, fontWeight: 800, textDecoration: "underline"}}>Abrir →</div>
            </div>
          ))}
        </div>
      </section>
    </main>
  );
}

window.HomeScreen = HomeScreen;
