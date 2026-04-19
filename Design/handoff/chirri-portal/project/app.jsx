// Entry app with router + tweaks

const TWEAK_DEFAULTS = /*EDITMODE-BEGIN*/{
  "defaultRoute": "home",
  "showStickers": true
}/*EDITMODE-END*/;

function App() {
  const [route, setRoute] = React.useState(() => {
    const saved = localStorage.getItem("chirri-route");
    return saved || "login";
  });
  const [activeHandle, setActiveHandle] = React.useState("@sofi.gonet");
  const [tweaksOn, setTweaksOn] = React.useState(false);
  const [tweaks, setTweaks] = React.useState(TWEAK_DEFAULTS);

  const data = window.CHIRRI_DATA;

  React.useEffect(() => { localStorage.setItem("chirri-route", route); }, [route]);

  React.useEffect(() => {
    const onMsg = (e) => {
      if (e.data?.type === "__activate_edit_mode") setTweaksOn(true);
      if (e.data?.type === "__deactivate_edit_mode") setTweaksOn(false);
    };
    window.addEventListener("message", onMsg);
    window.parent.postMessage({type: "__edit_mode_available"}, "*");
    return () => window.removeEventListener("message", onMsg);
  }, []);

  const go = (r) => setRoute(r);
  const openInfluencer = (h) => { setActiveHandle(h); setRoute("influencer"); };

  if (route === "login") {
    return <LoginScreen onLogin={() => setRoute("home")} />;
  }

  return (
    <div className="app">
      <TopBar route={route} go={go} tenant={data.client} user={data.user} />
      {route === "home" && <HomeScreen data={data} go={go} />}
      {route === "report" && <ReportScreen data={data} go={go} openInfluencer={openInfluencer} />}
      {route === "calendar" && <CalendarScreen data={data} go={go} />}
      {route === "campaign" && <CampaignScreen data={data} go={go} openInfluencer={openInfluencer} />}
      {route === "influencer" && <InfluencerScreen data={data} handle={activeHandle} go={go} />}
      {route === "export" && <ExportScreen data={data} go={go} />}

      {tweaksOn && (
        <div className="tweaks-panel">
          <h4>Tweaks</h4>
          <div className="tweak-row">
            <label>Pantalla de inicio</label>
            <div className="tweak-seg">
              <button className={route === "login" ? "on" : ""} onClick={() => setRoute("login")}>Login</button>
              <button className={route === "home" ? "on" : ""} onClick={() => setRoute("home")}>Home</button>
            </div>
          </div>
          <div className="tweak-row">
            <label>Ir a pantalla</label>
            <div style={{display: "grid", gridTemplateColumns: "1fr 1fr", gap: 6}}>
              {[["report","Reporte"],["calendar","Cronograma"],["campaign","Campaña"],["influencer","Influencer"],["export","Export PDF"]].map(([k,l]) => (
                <button key={k} className="btn btn-sm" style={{fontSize: 11, padding: "6px 10px", boxShadow: "2px 2px 0 var(--chirri-black)", background: route === k ? "var(--chirri-yellow)" : "white"}} onClick={() => setRoute(k)}>{l}</button>
              ))}
            </div>
          </div>
          <div style={{fontSize: 11, color: "var(--chirri-muted)", borderTop: "1px solid var(--chirri-line)", paddingTop: 10, marginTop: 4, fontWeight: 500}}>
            Este es un mockup navegable. Probá los links internos o saltá directo con estos botones.
          </div>
        </div>
      )}
    </div>
  );
}

const root = ReactDOM.createRoot(document.getElementById("root"));
root.render(<App />);
