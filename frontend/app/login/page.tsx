import { redirect } from "next/navigation";
import { cookies } from "next/headers";
import LoginForm from "./login-form";

export default function LoginPage() {
  const token = cookies().get("chirri_access")?.value;
  if (token) redirect("/home");

  return (
    <div className="login-stage">
      <div className="login-art">
        <div className="blob-mint" style={{ bottom: -40, right: -60, transform: "rotate(-20deg)" }} />
        <div className="blob-pink" style={{ top: 120, left: -40, transform: "rotate(15deg)", opacity: 0.85 }} />

        <div style={{ position: "relative", display: "flex", alignItems: "center", gap: 10 }}>
          <span className="logo-chirri" style={{ fontFamily: "var(--font-display)", fontSize: 28 }}>chirri</span>
          <span
            style={{
              fontSize: 11,
              fontWeight: 800,
              letterSpacing: "0.18em",
              background: "var(--chirri-black)",
              color: "var(--chirri-yellow)",
              padding: "4px 10px",
              borderRadius: 999,
            }}
          >
            PORTAL
          </span>
        </div>

        <div style={{ position: "relative" }}>
          <div className="login-art-tag">Tu espacio en Chirri.</div>
          <div className="login-art-big" style={{ marginTop: 20 }}>
            todo lo<br />que está<br /><em>pasando</em><br />en tus redes.
          </div>
        </div>

        <div style={{ position: "relative", fontSize: 11, fontWeight: 700, letterSpacing: "0.12em" }}>
          CHIRRI PEPPERS · BUENOS AIRES · 2026
        </div>
      </div>

      <LoginForm />
    </div>
  );
}
