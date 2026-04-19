function TopBar({ route, go, tenant, user }) {
  const items = [
    { id: "home", label: "Home" },
    { id: "report", label: "Reporte" },
    { id: "calendar", label: "Cronograma" },
    { id: "campaign", label: "Campaña" }
  ];
  const activeFor = (id) => {
    if (route === id) return true;
    if (route === "influencer" && id === "campaign") return true;
    if (route === "export" && id === "report") return true;
    return false;
  };
  return (
    <header className="topbar">
      <div className="topbar-left">
        <a href="#" className="logo-chirri" onClick={(e) => { e.preventDefault(); go("home"); }}>chirri</a>
        <nav className="nav">
          {items.map(it => (
            <button key={it.id} className={activeFor(it.id) ? "active" : ""} onClick={() => go(it.id)}>
              {it.label}
            </button>
          ))}
        </nav>
      </div>
      <div className="topbar-right">
        <div className="tenant-chip" title="Estás en el espacio de Balanz">
          <TenantDot />
          <div style={{display: "flex", flexDirection: "column", lineHeight: 1.15}}>
            <span className="tenant-label">Cliente</span>
            <span>{tenant.name}</span>
          </div>
        </div>
        <div className="user-chip" title={user.name}>{user.initials}</div>
      </div>
    </header>
  );
}

window.TopBar = TopBar;
