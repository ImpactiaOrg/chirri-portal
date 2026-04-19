// chrome v2 — topbar with breadcrumb + Cronograma disabled

function TopBar({ crumbs, go, tenant, user }) {
  const items = [
    { id: "home", label: "Home", route: { screen: "home" } },
    { id: "campaigns", label: "Campañas", route: { screen: "campaigns" } },
    { id: "calendar", label: "Cronograma", route: { screen: "calendar" }, disabled: true }
  ];
  const currentScreen = crumbs.screen;
  const activeFor = (id) => {
    if (id === "home" && currentScreen === "home") return true;
    if (id === "campaigns" && ["campaigns","campaign","stage","report","influencer","export"].includes(currentScreen)) return true;
    if (id === "calendar" && currentScreen === "calendar") return true;
    return false;
  };
  return (
    <>
      <header className="topbar">
        <div className="topbar-left">
          <a href="#" className="logo-chirri" onClick={(e) => { e.preventDefault(); go({ screen: "home" }); }}>chirri</a>
          <span style={{fontSize: 10, fontWeight: 800, letterSpacing: "0.14em", padding: "3px 8px", background: "var(--chirri-black)", color: "var(--chirri-yellow)", borderRadius: 999}}>PORTAL</span>
          <nav className="nav">
            {items.map(it => (
              <button key={it.id}
                className={activeFor(it.id) ? "active" : ""}
                disabled={it.disabled}
                onClick={() => !it.disabled && go(it.route)}
                style={it.disabled ? {opacity: 0.4, cursor: "not-allowed"} : undefined}
              >
                {it.label}
                {it.disabled && <span style={{fontSize: 9, marginLeft: 6, padding: "1px 6px", background: "var(--chirri-muted)", color: "white", borderRadius: 999, fontWeight: 800}}>SOON</span>}
              </button>
            ))}
          </nav>
        </div>
        <div className="topbar-right">
          <div className="tenant-chip">
            <TenantDot />
            <div style={{display: "flex", flexDirection: "column", lineHeight: 1.15}}>
              <span className="tenant-label">Cliente</span>
              <span>{tenant.name}</span>
            </div>
          </div>
          <div className="user-chip">{user.initials}</div>
        </div>
      </header>
      {crumbs.crumbs && crumbs.crumbs.length > 0 && (
        <div style={{background: "var(--chirri-cream)", borderBottom: "1.5px solid var(--chirri-line)", padding: "10px 28px", fontSize: 12, fontWeight: 700, display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap"}}>
          {crumbs.crumbs.map((c, i) => (
            <React.Fragment key={i}>
              {i > 0 && <span style={{opacity: 0.4}}>›</span>}
              {c.route ? (
                <a href="#" onClick={(e) => { e.preventDefault(); go(c.route); }} style={{textDecoration: "none", color: "var(--chirri-black)", opacity: 0.7}}>{c.label}</a>
              ) : (
                <span style={{color: "var(--chirri-black)"}}>{c.label}</span>
              )}
            </React.Fragment>
          ))}
        </div>
      )}
    </>
  );
}

window.TopBar = TopBar;
