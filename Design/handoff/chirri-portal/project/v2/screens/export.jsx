function ExportScreen({ data, go }) {
  const [format, setFormat] = React.useState("pdf");

  return (
    <main className="page" style={{background: "var(--chirri-mint)"}}>
      <button className="btn btn-sm" onClick={() => window.history.back()} style={{marginBottom: 20}}>← Volver</button>

      <section style={{marginBottom: 32}}>
        <div className="eyebrow">Export · Marzo 2026</div>
        <h1 className="font-display" style={{fontSize: 80, lineHeight: 0.9, letterSpacing: "-0.03em", margin: "8px 0 0", textTransform: "lowercase"}}>
          bajá el reporte <span style={{color: "var(--chirri-pink-deep)"}}>con tu marca</span>.
        </h1>
        <p style={{fontSize: 16, maxWidth: 640, marginTop: 14, lineHeight: 1.5, fontWeight: 500}}>
          En pantalla ves el trabajo de Chirri. El archivo que bajás para el directorio (PDF, PPTX o Excel) va con identidad Balanz — Chirri firma chiquito al pie.
        </p>
      </section>

      <section style={{display: "grid", gridTemplateColumns: "320px 1fr", gap: 30, alignItems: "start"}}>
        {/* Options sidebar */}
        <div style={{display: "flex", flexDirection: "column", gap: 18, position: "sticky", top: 100}}>
          <div className="card card-flat">
            <div className="eyebrow" style={{marginBottom: 10}}>Formato</div>
            <div className="tweak-seg">
              <button className={format === "pdf" ? "on" : ""} onClick={() => setFormat("pdf")}>PDF</button>
              <button className={format === "pptx" ? "on" : ""} onClick={() => setFormat("pptx")}>PPTX</button>
              <button className={format === "xls" ? "on" : ""} onClick={() => setFormat("xls")}>Excel</button>
            </div>
            <div style={{fontSize: 11, color: "var(--chirri-muted)", marginTop: 10, lineHeight: 1.5, fontWeight: 500}}>
              {format === "pdf" && "Listo para compartir o imprimir. 8 páginas A4."}
              {format === "pptx" && "Editable en PowerPoint / Keynote. Una slide por sección, 16:9."}
              {format === "xls" && "Planilla con métricas por post y por red. Para análisis propio."}
            </div>
          </div>
          <div className="card card-flat">
            <div className="eyebrow" style={{marginBottom: 10}}>Branding</div>
            <div style={{display: "flex", flexDirection: "column", gap: 8}}>
              <label style={{display: "flex", gap: 10, alignItems: "center", fontSize: 14, fontWeight: 600}}>
                <input type="radio" checked readOnly /> <BalanzMark size={16} /> <span style={{marginLeft: "auto", fontSize: 11, fontWeight: 800, color: "var(--chirri-pink-deep)"}}>RECOMENDADO</span>
              </label>
              <label style={{display: "flex", gap: 10, alignItems: "center", fontSize: 14, fontWeight: 600, opacity: 0.6}}>
                <input type="radio" readOnly /> Chirri (interno)
              </label>
              <label style={{display: "flex", gap: 10, alignItems: "center", fontSize: 14, fontWeight: 600, opacity: 0.6}}>
                <input type="radio" readOnly /> Plantilla neutra
              </label>
            </div>
          </div>
          <div className="card card-flat">
            <div className="eyebrow" style={{marginBottom: 10}}>Incluir</div>
            <div style={{display: "flex", flexDirection: "column", gap: 8}}>
              {["Big numbers", "Top contenidos", "Top influencers", "OneLink / descargas", "Conclusiones del mes"].map(it => (
                <label key={it} style={{display: "flex", gap: 10, alignItems: "center", fontSize: 14, fontWeight: 600}}>
                  <input type="checkbox" defaultChecked /> {it}
                </label>
              ))}
            </div>
          </div>
          <button className="btn btn-primary" style={{justifyContent: "center"}}>↓ Descargar {format.toUpperCase()}</button>
          <div style={{fontSize: 11, color: "var(--chirri-muted)", lineHeight: 1.5, padding: "0 4px", fontWeight: 600}}>
            Se genera en ~20s. Te mandamos un mail cuando esté.
          </div>
        </div>

        {/* PDF preview (Balanz branded) */}
        <div>
          <div style={{display: "flex", alignItems: "center", gap: 10, marginBottom: 12, justifyContent: "space-between"}}>
            <span className="eyebrow" style={{margin: 0}}>Vista previa · PDF</span>
            <span style={{fontSize: 11, fontWeight: 700}}>{format === "pptx" ? "Slide 1 de 8 · 16:9" : format === "xls" ? "Hoja 1 de 4" : "Página 1 de 8 · A4"}</span>
          </div>
          <div className="balanz-doc">
            <div className="balanz-hero">
              <div style={{display: "flex", justifyContent: "space-between", alignItems: "center"}}>
                <BalanzMark size={28} dark />
                <div style={{fontFamily: "'JetBrains Mono', monospace", fontSize: 11, color: "rgba(255,255,255,0.6)", letterSpacing: "0.12em"}}>REPORTE · MARZO 2026</div>
              </div>
              <h1>Redes sociales<br/><em>Marzo 2026</em></h1>
              <div style={{marginTop: 16, fontSize: 14, opacity: 0.85, maxWidth: 520, lineHeight: 1.5}}>
                Campaña "De Ahorrista a Inversor" — Awareness, Educación, Validación y Conversión.
              </div>
            </div>

            <div style={{padding: 48, background: "white", color: "var(--balanz-blue)"}}>
              <div style={{display: "flex", alignItems: "center", gap: 14, marginBottom: 24}}>
                <div style={{width: 4, height: 32, background: "var(--balanz-teal)"}} />
                <h3 style={{margin: 0, fontFamily: "'Archivo Black', sans-serif", fontSize: 22, letterSpacing: "-0.02em"}}>Big numbers del mes</h3>
              </div>

              <div style={{display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 20, marginBottom: 36}}>
                {data.kpis.slice(0, 4).map((k, i) => (
                  <div key={i} style={{padding: 20, background: i === 0 ? "var(--balanz-blue)" : "#F4F7FB", color: i === 0 ? "white" : "var(--balanz-blue)", borderRadius: 12, border: "1px solid rgba(11,45,91,0.1)"}}>
                    <div style={{fontSize: 10, letterSpacing: "0.14em", textTransform: "uppercase", opacity: 0.7, fontWeight: 700}}>{k.label}</div>
                    <div style={{fontFamily: "'Archivo Black', sans-serif", fontSize: 38, lineHeight: 1, letterSpacing: "-0.03em", marginTop: 8}}>
                      {k.value}<span style={{fontSize: 18, opacity: 0.7}}>{k.unit}</span>
                    </div>
                    <div style={{fontFamily: "'JetBrains Mono', monospace", fontSize: 11, marginTop: 6, color: i === 0 ? "var(--balanz-teal)" : "#2C8F6E", fontWeight: 600}}>
                      ▲ {k.delta}% vs feb
                    </div>
                  </div>
                ))}
              </div>

              <div style={{padding: 24, background: "#F4F7FB", borderRadius: 12, borderLeft: "4px solid var(--balanz-teal)"}}>
                <div style={{fontSize: 10, letterSpacing: "0.14em", textTransform: "uppercase", fontWeight: 700, opacity: 0.7, marginBottom: 8}}>Resumen del mes</div>
                <p style={{margin: 0, fontSize: 14, lineHeight: 1.6}}>{data.note.body}</p>
              </div>

              <div style={{marginTop: 36, paddingTop: 16, borderTop: "1px solid rgba(11,45,91,0.1)", display: "flex", justifyContent: "space-between", fontSize: 10, letterSpacing: "0.1em", color: "rgba(11,45,91,0.5)", textTransform: "uppercase", fontWeight: 700}}>
                <span>Balanz · Redes · Marzo 2026</span>
                <span>Preparado por Chirri Peppers</span>
                <span>{format === "pptx" ? "SLIDE 01 / 08" : "01 / 08"}</span>
              </div>
            </div>
          </div>

          <div style={{display: "flex", justifyContent: "center", gap: 10, marginTop: 16, fontSize: 12, fontWeight: 700}}>
            <button className="btn btn-sm">← Página anterior</button>
            <span style={{padding: "7px 14px"}}>1 / 8</span>
            <button className="btn btn-sm">Siguiente →</button>
          </div>
        </div>
      </section>
    </main>
  );
}

window.ExportScreen = ExportScreen;
