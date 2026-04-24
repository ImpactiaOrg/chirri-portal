import { redirect } from "next/navigation";
import { getCurrentUser } from "@/lib/auth";
import LoginForm from "./login-form";

export default async function LoginPage() {
  // Validate the user actually exists, not just that a cookie is present.
  // A leftover token pointing to a wiped user would otherwise redirect
  // to /home which redirects back → infinite loop. Seen after seed_demo --wipe.
  const user = await getCurrentUser();
  if (user) redirect("/home");

  return (
    <div className="login-stage">
      <div className="login-art">
        <div className="blob-mint" style={{ bottom: -40, right: -60, transform: "rotate(-20deg)" }} />
        <div className="blob-pink" style={{ top: 120, left: -40, transform: "rotate(15deg)", opacity: 0.85 }} />

        <div style={{ position: "relative", display: "flex", alignItems: "center", gap: 10 }}>
          <span
            className="logo-chirri"
            style={{
              fontSize: 56,
              letterSpacing: "-0.03em",
              display: "inline-block",
              transform: "scaleY(1.2)",
              transformOrigin: "center bottom",
              paddingTop: 8,
              fontWeight: 900,
              WebkitTextStroke: "0.5px currentColor",
            }}
          >
            chirri
          </span>
          <span
            style={{
              display: "inline-flex",
              alignItems: "center",
              gap: 6,
              fontSize: 15,
              fontWeight: 800,
              letterSpacing: "0.12em",
              background: "var(--chirri-black)",
              color: "var(--chirri-yellow)",
              padding: "7px 14px 8px",
              borderRadius: 999,
              border: "2.5px solid var(--chirri-black)",
              boxShadow: "3px 3px 0 var(--chirri-pink-deep)",
              transform: "rotate(-3deg)",
              fontFamily: "var(--font-display)",
            }}
          >
            <span
              style={{
                color: "var(--chirri-mint-deep)",
                fontFamily: "Georgia, serif",
                fontSize: 14,
              }}
            >
              ✳
            </span>
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
