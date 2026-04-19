// app.jsx v2 — object-based router with crumbs

function App() {
  const [route, setRoute] = React.useState(() => {
    try {
      const saved = JSON.parse(localStorage.getItem("chirri-route-v2") || "null");
      if (saved && saved.screen) return saved;
    } catch {}
    return { screen: "login" };
  });
  const [tweaksOn, setTweaksOn] = React.useState(false);
  const [activeHandle, setActiveHandle] = React.useState("@sofi.gonet");

  const data = window.CHIRRI_DATA;

  React.useEffect(() => { localStorage.setItem("chirri-route-v2", JSON.stringify(route)); }, [route]);

  React.useEffect(() => {
    const onMsg = (e) => {
      if (e.data?.type === "__activate_edit_mode") setTweaksOn(true);
      if (e.data?.type === "__deactivate_edit_mode") setTweaksOn(false);
    };
    window.addEventListener("message", onMsg);
    window.parent.postMessage({type: "__edit_mode_available"}, "*");
    return () => window.removeEventListener("message", onMsg);
  }, []);

  const go = (r) => {
    if (typeof r === "string") r = { screen: r };
    setRoute(r);
    window.scrollTo(0, 0);
  };
  const openInfluencer = (h) => { setActiveHandle(h); setRoute({ screen: "influencer" }); };

  if (route.screen === "login") {
    return <LoginScreen onLogin={() => setRoute({ screen: "home" })} />;
  }

  // Build crumbs
  const crumbs = { screen: route.screen, crumbs: [] };
  const campaign = route.campaignId ? data.campaigns.find(c => c.id === route.campaignId) : null;
  const stage = route.stageId ? data.stages[route.stageId] : null;
  const report = (route.reportId && route.stageId) ? (data.reportsByStage[route.stageId] || []).find(r => r.id === route.reportId) : null;
  const base = [{ label: "Balanz", route: { screen: "home" } }];
  if (route.screen === "campaigns") crumbs.crumbs = [...base, { label: "Campañas" }];
  else if (route.screen === "campaign" && campaign) crumbs.crumbs = [...base, { label: "Campañas", route: { screen: "campaigns" } }, { label: campaign.name }];
  else if (route.screen === "stage" && campaign && stage) crumbs.crumbs = [...base, { label: campaign.name, route: { screen: "campaign", campaignId: campaign.id } }, { label: stage.name }];
  else if (route.screen === "report" && campaign && stage && report) crumbs.crumbs = [
    ...base,
    { label: campaign.name, route: { screen: "campaign", campaignId: campaign.id } },
    { label: stage.name, route: { screen: "campaign", campaignId: campaign.id } },
    { label: report.title }
  ];
  else if (route.screen === "influencer") crumbs.crumbs = [...base, { label: "Campañas", route: { screen: "campaigns" } }, { label: activeHandle }];
  else if (route.screen === "export" && report) crumbs.crumbs = [...base, { label: report.title, route: { screen: "report", ...route } }, { label: "Descargar" }];
  else if (route.screen === "calendar") crumbs.crumbs = [...base, { label: "Cronograma (soon)" }];

  return (
    <div className="app">
      <TopBar crumbs={crumbs} go={go} tenant={data.client} user={data.user} />
      {route.screen === "home" && <HomeScreen data={data} go={go} />}
      {route.screen === "campaigns" && <CampaignsScreen data={data} go={go} />}
      {route.screen === "campaign" && <CampaignScreen data={data} campaignId={route.campaignId} go={go} />}
      {route.screen === "stage" && <StageScreen data={data} campaignId={route.campaignId} stageId={route.stageId} go={go} />}
      {route.screen === "report" && <ReportScreen data={data} campaignId={route.campaignId} stageId={route.stageId} reportId={route.reportId} go={go} openInfluencer={openInfluencer} />}
      {route.screen === "influencer" && <InfluencerScreen data={data} handle={activeHandle} go={(r) => go(typeof r === "string" ? { screen: r } : r)} />}
      {route.screen === "calendar" && <CalendarScreen data={data} go={go} />}
      {route.screen === "export" && <ExportScreen data={data} go={(r) => go(typeof r === "string" ? { screen: r } : r)} />}

      {tweaksOn && (
        <div className="tweaks-panel">
          <h4>Tweaks</h4>
          <div className="tweak-row">
            <label>Saltar a</label>
            <div style={{display: "grid", gridTemplateColumns: "1fr 1fr", gap: 6}}>
              {[
                ["Login", { screen: "login" }],
                ["Home", { screen: "home" }],
                ["Campañas", { screen: "campaigns" }],
                ["Campaña activa", { screen: "campaign", campaignId: "ahorrista-inversor" }],
                ["Campaña terminada", { screen: "campaign", campaignId: "harry-potter-2025" }],
                ["Reporte Marzo", { screen: "report", campaignId: "ahorrista-inversor", stageId: "validacion", reportId: "va-mar-2026" }],
                ["Influencer", { screen: "influencer" }],
                ["Export", { screen: "export", campaignId: "ahorrista-inversor", stageId: "validacion", reportId: "va-mar-2026" }],
                ["Cronograma SOON", { screen: "calendar" }]
              ].map(([l, r]) => (
                <button key={l} className="btn btn-sm" style={{fontSize: 11, padding: "6px 10px", background: route.screen === r.screen ? "var(--chirri-yellow)" : "white"}} onClick={() => go(r)}>{l}</button>
              ))}
            </div>
          </div>
          <div style={{fontSize: 11, color: "var(--chirri-muted)", borderTop: "1px solid var(--chirri-line)", paddingTop: 10, marginTop: 4, fontWeight: 500}}>
            Portal v2 · Campañas + etapas + reportes jerárquicos. El cronograma queda en "soon".
          </div>
        </div>
      )}
    </div>
  );
}

const root = ReactDOM.createRoot(document.getElementById("root"));
root.render(<App />);
