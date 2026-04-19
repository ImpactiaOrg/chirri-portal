import Link from "next/link";
import type { ClientUserDto } from "@/lib/api";

function initialsOf(user: ClientUserDto): string {
  const name = (user.full_name || user.email).trim();
  const parts = name.split(/\s+/).filter(Boolean);
  const first = parts[0]?.[0] ?? "?";
  const second = parts[1]?.[0] ?? "";
  return (first + second).toUpperCase();
}

type Props = { user: ClientUserDto; active?: "home" | "campaigns" };

export default function TopBar({ user, active = "home" }: Props) {
  const tenantName = user.client?.name ?? "—";
  return (
    <header className="topbar">
      <div className="topbar-left">
        <Link href="/home" className="logo-chirri">chirri</Link>
        <span className="portal-pill">PORTAL</span>
        <nav className="nav">
          <Link href="/home" className={active === "home" ? "active" : ""}>Home</Link>
          <Link href="/campaigns" className={active === "campaigns" ? "active" : ""}>Campañas</Link>
          <span className="soon">
            Cronograma <span className="soon-tag">SOON</span>
          </span>
        </nav>
      </div>
      <div className="topbar-right">
        <div className="tenant-chip">
          <span className="tenant-dot" />
          <div style={{ display: "flex", flexDirection: "column", lineHeight: 1.15 }}>
            <span className="tenant-label">Cliente</span>
            <span>{tenantName}</span>
          </div>
        </div>
        <div className="user-chip" title={user.full_name || user.email}>
          {initialsOf(user)}
        </div>
        <form action="/logout" method="post" style={{ margin: 0 }}>
          <button type="submit" className="logout-btn">Salir</button>
        </form>
      </div>
    </header>
  );
}
