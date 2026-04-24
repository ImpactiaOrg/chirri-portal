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
        <Link
          href="/home"
          className="logo-chirri"
          style={{
            fontSize: 26,
            letterSpacing: "-0.03em",
            display: "inline-block",
            transform: "scaleY(1.18)",
            transformOrigin: "center bottom",
            paddingTop: 4,
            fontWeight: 900,
            WebkitTextStroke: "0.3px currentColor",
          }}
        >
          chirri
        </Link>
        <span
          style={{
            display: "inline-flex",
            alignItems: "center",
            gap: 5,
            fontSize: 11,
            fontWeight: 800,
            letterSpacing: "0.12em",
            padding: "4px 10px 5px",
            background: "var(--chirri-yellow)",
            color: "var(--chirri-black)",
            borderRadius: 999,
            border: "2px solid var(--chirri-black)",
            boxShadow: "2px 2px 0 var(--chirri-pink-deep)",
            transform: "rotate(-3deg)",
            fontFamily: "var(--font-display)",
            marginLeft: 4,
          }}
        >
          <span
            style={{
              color: "var(--chirri-mint-deep)",
              fontFamily: "Georgia, serif",
              fontSize: 11,
              marginTop: -1,
            }}
          >
            ✳
          </span>
          PORTAL
        </span>
        <span
          aria-hidden="true"
          style={{
            width: 1,
            height: 22,
            background: "var(--chirri-line-strong)",
            marginLeft: 8,
            marginRight: 4,
          }}
        />
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
