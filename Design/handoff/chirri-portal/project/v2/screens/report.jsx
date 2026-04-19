// report.jsx v2 — documento publicado con metadata de autor/fecha/tipo
function ReportScreen({ data, campaignId, stageId, reportId, go, openInfluencer }) {
  const campaign = data.campaigns.find(c => c.id === campaignId) || data.campaigns[0];
  const stage = data.stages[stageId] || data.stages.validacion;
  const reports = data.reportsByStage[stage.id] || [];
  const report = reports.find(r => r.id === reportId) || reports[0];

  const [network, setNetwork] = React.useState("instagram");
  const dist = data.distribution[network];
  const total = dist.organic + dist.paid + dist.influencer;
  const donutSegments = [
    { value: dist.organic, color: "var(--chirri-mint)", label: "Orgánico" },
    { value: dist.influencer, color: "#D4B8FF", label: "Influencer" },
    { value: dist.paid, color: "var(--chirri-pink)", label: "Pauta" }
  ];
  const kpiColors = ["yellow", "mint", "white", "pink", "white"];
  const typeLabel = { general: "Reporte general", influencers: "Reporte de influencers", cierre: "Cierre de etapa", plan: "Plan", mensual: "Reporte mensual" };

  return (
    <main className="page page-wide" style={{background: "var(--chirri-pink)"}}>
      {/* Document header */}
      <article style={{background: "white", border: "2.5px solid var(--chirri-black)", borderRadius: 24, padding: "48px 56px 40px", boxShadow: "5px 5px 0 var(--chirri-black)", marginBottom: 40, position: "relative", overflow: "hidden"}}>
        <div className="blob-mint" style={{top: -60, right: 40, opacity: 0.5}} />
        <div className="sticker" style={{top: 30, right: 40, fontSize: 32, color: "var(--chirri-mint-deep)", transform: "rotate(12deg)"}}>✳</div>

        <div style={{position: "relative"}}>
          <div style={{display: "flex", gap: 10, alignItems: "center", marginBottom: 14, flexWrap: "wrap"}}>
            <Pill color="mint">{(typeLabel[report.type] || report.type).toUpperCase()}</Pill>
            <span className="tag tag-neutral">{stage.name}</span>
            {report.isLatest && <span className="status status-approved">● ÚLTIMO PUBLICADO</span>}
          </div>
          <h1 className="font-display" style={{fontSize: 96, lineHeight: 0.88, letterSpacing: "-0.04em", margin: "6px 0 14px", textTransform: "lowercase"}}>
            {report.title.toLowerCase()}
          </h1>
          <div style={{display: "flex", gap: 28, alignItems: "center", flexWrap: "wrap", fontSize: 13, fontWeight: 600}}>
            <span>📅 <b>Publicado</b> {report.publishedDate}</span>
            <span>✍️ <b>Firma</b> {report.author} · Chirri</span>
            <span>📍 <b>Etapa</b> {stage.name}</span>
          </div>
          <p style={{fontSize: 17, maxWidth: 620, marginTop: 20, lineHeight: 1.5, fontWeight: 500}}>
            Reporte validado por el equipo de {campaign.name}. Si algo no cierra, mandanos tus comentarios desde el botón abajo.
          </p>
          <div style={{display: "flex", gap: 10, marginTop: 20, flexWrap: "wrap"}}>
            <button className="btn btn-primary" onClick={() => go({ screen: "export", campaignId, stageId, reportId })}>↓ Descargar</button>
            <button className="btn">💬 Dejar comentario</button>
          </div>
        </div>
      </article>

      {/* Body */}
      <section style={{marginBottom: 48}}>
        <div style={{display: "flex", justifyContent: "center", marginBottom: 28}}>
          <Pill color="mint">BIG NUMBERS</Pill>
        </div>
        <div className="kpi-row">
          {data.kpis.map((k, i) => <Kpi key={i} {...k} color={kpiColors[i]} />)}
        </div>
      </section>

      <section style={{display: "grid", gridTemplateColumns: "2fr 3fr", gap: 30, marginBottom: 56, alignItems: "start"}}>
        <div className="chirri-note" style={{background: "var(--chirri-mint)", fontSize: 17}}>
          "{data.note.body}"
          <span className="sig">— {data.note.author}</span>
        </div>
        <div className="card card-yellow">
          <div className="eyebrow" style={{marginBottom: 14}}>Comparativa Q1 2026</div>
          <QuarterlySpark />
        </div>
      </section>

      <section style={{marginBottom: 56}}>
        <div style={{display: "flex", justifyContent: "center", marginBottom: 24}}>
          <Pill color="pink">ALCANCE, DESARMADO</Pill>
        </div>
        <div style={{display: "flex", alignItems: "flex-end", justifyContent: "space-between", marginBottom: 24, gap: 20, flexWrap: "wrap"}}>
          <div>
            <h2 className="section-title" style={{textTransform: "lowercase"}}>¿de dónde vino la atención?</h2>
            <p className="section-sub">Cuánto fue orgánico, cuánto pauta, cuánto influencer.</p>
          </div>
          <div className="tweak-seg" style={{minWidth: 280}}>
            {["instagram", "tiktok", "x"].map(n => (
              <button key={n} className={network === n ? "on" : ""} onClick={() => setNetwork(n)}>
                {n === "instagram" ? "Instagram" : n === "tiktok" ? "TikTok" : "X"}
              </button>
            ))}
          </div>
        </div>

        <div className="split-viz">
          <div className="card">
            <div style={{display: "grid", gridTemplateColumns: "auto 1fr", gap: 24, alignItems: "center"}}>
              <div style={{position: "relative"}}>
                <Donut segments={donutSegments} size={220} stroke={40} />
                <div style={{position: "absolute", inset: 0, display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", textAlign: "center"}}>
                  <div className="font-display" style={{fontSize: 44, lineHeight: 0.9, letterSpacing: "-0.03em"}}>{fmtK(total)}</div>
                  <div className="eyebrow" style={{marginTop: 6, fontSize: 10}}>ALCANCE</div>
                </div>
              </div>
              <div className="split-bars">
                <SplitRow color="organic" label="Orgánico" value={dist.organic} total={total} />
                <SplitRow color="influencer" label="Influencer" value={dist.influencer} total={total} />
                <SplitRow color="paid" label="Pauta" value={dist.paid} total={total} />
              </div>
            </div>
          </div>

          <div className="card card-black">
            <div className="eyebrow" style={{color: "var(--chirri-yellow)", opacity: 1}}>Traducción humana</div>
            <div className="font-display" style={{fontSize: 26, lineHeight: 1.15, color: "var(--chirri-yellow)", marginTop: 10, textTransform: "lowercase"}}>
              de cada 10 personas que te vieron,
            </div>
            <div style={{marginTop: 20, display: "flex", flexDirection: "column", gap: 14}}>
              <TenRow count={Math.round(dist.influencer/total*10)} color="#D4B8FF" label="llegaron por un influencer" detail="curaduría + fee" />
              <TenRow count={Math.round(dist.paid/total*10)} color="var(--chirri-pink)" label="llegaron por pauta" detail="presupuesto invertido" />
              <TenRow count={10 - Math.round(dist.influencer/total*10) - Math.round(dist.paid/total*10)} color="var(--chirri-mint)" label="llegaron solas al feed" detail="criterio + timing" />
            </div>
          </div>
        </div>
      </section>

      <section style={{marginBottom: 56}}>
        <div style={{display: "flex", justifyContent: "center", marginBottom: 24}}>
          <Pill color="pink">TOP CONTENIDOS</Pill>
        </div>
        <div className="grid-2">
          <div>
            <div style={{display: "flex", alignItems: "center", gap: 8, marginBottom: 14}}>
              <span className="dot-source dot-organic" />
              <span style={{fontWeight: 800, fontSize: 13, letterSpacing: "0.04em"}}>ORGÁNICO</span>
            </div>
            <div className="rank-list">
              {data.topOrganic.map((p, i) => (
                <div className="rank-item" key={i}>
                  <div className="rank-num">{p.rank}</div>
                  <div className="rank-meta">
                    <div className="handle">{p.title}</div>
                    <div className="caption">{p.format} · {p.saves.toLocaleString()} guardados · ER {p.er}</div>
                  </div>
                  <div className="rank-metric">{p.reach}<span className="unit">reach</span></div>
                </div>
              ))}
            </div>
          </div>
          <div>
            <div style={{display: "flex", alignItems: "center", gap: 8, marginBottom: 14}}>
              <span className="dot-source dot-influencer" />
              <span style={{fontWeight: 800, fontSize: 13, letterSpacing: "0.04em"}}>INFLUENCERS</span>
            </div>
            <div className="rank-list">
              {data.topInfluencers.map((p, i) => (
                <div className="rank-item" key={i} onClick={() => openInfluencer(p.handle)}>
                  <div className="rank-num">{p.rank}</div>
                  <div className="rank-meta">
                    <div className="handle">{p.handle}</div>
                    <div className="caption">{p.narrative} · {p.posts} post{p.posts > 1 ? "s" : ""}</div>
                  </div>
                  <div className="rank-metric">{p.reach}<span className="unit">reach</span></div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>

      <section style={{marginBottom: 40}}>
        <div style={{display: "flex", justifyContent: "center", marginBottom: 20}}>
          <Pill color="yellow">ONELINK · DESCARGAS APP</Pill>
        </div>
        <div className="card" style={{padding: 0, overflow: "hidden"}}>
          <table style={{width: "100%", borderCollapse: "collapse"}}>
            <thead>
              <tr style={{background: "var(--chirri-paper)"}}>
                {["Influencer", "Clicks", "Descargas", "CTR", "Conversión"].map(h => (
                  <th key={h} style={{textAlign: "left", padding: "14px 20px", fontSize: 10, letterSpacing: "0.14em", textTransform: "uppercase", fontWeight: 800}}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {data.utm.map((r, i) => (
                <tr key={i} style={{borderTop: "2px solid var(--chirri-line)"}}>
                  <td style={{padding: "14px 20px", fontWeight: 700, fontSize: 14}}>{r.handle}</td>
                  <td style={{padding: "14px 20px", fontFamily: "var(--font-mono)", fontSize: 13}}>{r.clicks.toLocaleString()}</td>
                  <td style={{padding: "14px 20px", fontFamily: "var(--font-mono)", fontSize: 14, fontWeight: 800}}>{r.downloads.toLocaleString()}</td>
                  <td style={{padding: "14px 20px", fontFamily: "var(--font-mono)", fontSize: 13, color: "var(--chirri-muted)"}}>{r.ctr}</td>
                  <td style={{padding: "14px 20px", fontFamily: "var(--font-mono)", fontSize: 13, fontWeight: 800, color: "var(--organic)"}}>{r.cvr}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section style={{display: "flex", gap: 12, justifyContent: "space-between", alignItems: "center", marginTop: 40, padding: "24px 0", borderTop: "2px solid var(--chirri-black)", flexWrap: "wrap"}}>
        <div style={{fontSize: 13, fontWeight: 600}}>
          Próximo reporte estimado: <b>{campaign.nextReportDate || "TBD"}</b>
        </div>
        <div style={{display: "flex", gap: 10}}>
          <button className="btn" onClick={() => go({ screen: "campaign", campaignId })}>← Volver a la campaña</button>
          <button className="btn btn-primary" onClick={() => go({ screen: "export", campaignId, stageId, reportId })}>Descargar reporte →</button>
        </div>
      </section>
    </main>
  );
}

function SplitRow({ color, label, value, total }) {
  const pct = (value / total) * 100;
  return (
    <div className="split-row">
      <div className="lbl"><span className={"dot-source dot-" + color} />{label}</div>
      <div className="bar">
        <div className={"fill fill-" + color} style={{transform: `scaleX(${pct/100})`}} />
        <div className="amt">{pct.toFixed(0)}%</div>
      </div>
      <div className="val">{fmtK(value)}</div>
    </div>
  );
}

function TenRow({ count, color, label, detail }) {
  return (
    <div style={{display: "grid", gridTemplateColumns: "auto 1fr", gap: 14, alignItems: "center"}}>
      <div style={{display: "flex", gap: 3}}>
        {Array.from({length: 10}).map((_, i) => (
          <div key={i} style={{width: 14, height: 22, borderRadius: 3,
            background: i < count ? color : "rgba(255,255,255,0.12)",
            border: i < count ? "1.5px solid var(--chirri-black)" : "1.5px solid rgba(255,255,255,0.12)"}} />
        ))}
      </div>
      <div>
        <div style={{fontSize: 15, fontWeight: 700, color: "var(--chirri-cream)"}}>{label}</div>
        <div style={{fontSize: 11.5, opacity: 0.55, marginTop: 2}}>{detail}</div>
      </div>
    </div>
  );
}

function QuarterlySpark() {
  const d = [{m: "ENE", v: 2.34}, {m: "FEB", v: 2.53}, {m: "MAR", v: 2.84}];
  const max = 3.2;
  return (
    <div style={{display: "flex", alignItems: "flex-end", gap: 24, justifyContent: "space-around", height: 180, padding: "0 8px"}}>
      {d.map((x, i) => {
        const h = (x.v / max) * 160;
        const cur = i === d.length - 1;
        return (
          <div key={i} style={{flex: 1, display: "flex", flexDirection: "column", alignItems: "center", gap: 10}}>
            <div className="font-mono" style={{fontSize: 13, fontWeight: 700}}>{x.v}M</div>
            <div style={{width: "100%", height: h, background: cur ? "var(--chirri-pink-deep)" : "white", border: "2px solid var(--chirri-black)", borderRadius: "10px 10px 0 0"}} />
            <div style={{fontSize: 11, letterSpacing: "0.12em", fontWeight: 800}}>{x.m}</div>
          </div>
        );
      })}
    </div>
  );
}

window.ReportScreen = ReportScreen;
