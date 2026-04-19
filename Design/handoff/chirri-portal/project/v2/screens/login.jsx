function LoginScreen({ onLogin }) {
  const [email, setEmail] = React.useState("belen.rizzo@balanz.com");
  const [pw, setPw] = React.useState("••••••••••");

  return (
    <div className="login-stage">
      <div className="login-art">
        <div className="blob-mint" style={{bottom: -40, right: -60, transform: "rotate(-20deg)"}} />
        <div className="blob-pink" style={{top: 120, left: -40, transform: "rotate(15deg)", opacity: 0.85}} />
        <div className="sticker" style={{top: 30, right: 60, fontSize: 40, color: "var(--chirri-mint-deep)", transform: "rotate(15deg)"}}>✳</div>
        <div className="sticker" style={{bottom: 80, right: 120, fontSize: 28, color: "var(--chirri-pink-deep)"}}>✳</div>
        <div className="sticker" style={{top: 240, right: 40}}>
          <div style={{width: 36, height: 36, background: "white", clipPath: "polygon(50% 0, 58% 42%, 100% 50%, 58% 58%, 50% 100%, 42% 58%, 0 50%, 42% 42%)"}} />
        </div>

        <div style={{position: "relative", display: "flex", alignItems: "center", gap: 10}}>
          <span className="logo-chirri">chirri</span>
          <span style={{fontSize: 11, fontWeight: 800, letterSpacing: "0.18em", background: "var(--chirri-black)", color: "var(--chirri-yellow)", padding: "4px 10px", borderRadius: 999}}>PORTAL</span>
        </div>

        <div style={{position: "relative"}}>
          <div className="login-art-tag">Tu espacio en Chirri.</div>
          <div className="login-art-big" style={{marginTop: 20}}>
            todo lo<br/>que está<br/><em>pasando</em><br/>en tus redes.
          </div>
        </div>

        <div style={{position: "relative", fontSize: 11, fontWeight: 700, letterSpacing: "0.12em"}}>
          CHIRRI PEPPERS · BUENOS AIRES · 2026
        </div>
      </div>

      <div className="login-form">
        <div className="sticker" style={{top: 40, right: 60, fontSize: 32, color: "var(--chirri-mint-deep)", transform: "rotate(-12deg)"}}>✳</div>

        <div>
          <div className="eyebrow">Chirri Portal · Acceso clientes</div>
          <h1 className="font-display" style={{fontSize: 64, lineHeight: 0.9, letterSpacing: "-0.03em", margin: "4px 0 0", textTransform: "lowercase"}}>
            hola de<br/>nuevo.
          </h1>
          <p style={{fontSize: 14, marginTop: 10, fontWeight: 500, maxWidth: 360}}>Entrá a <b>Chirri Portal</b> y mirá tu mes. Lo dejamos listo antes del directorio.</p>
        </div>

        <div className="input-row">
          <label>Email</label>
          <input type="email" value={email} onChange={e => setEmail(e.target.value)} />
        </div>
        <div className="input-row">
          <label>Contraseña</label>
          <input type="password" value={pw} onChange={e => setPw(e.target.value)} />
        </div>

        <div style={{display: "flex", justifyContent: "space-between", alignItems: "center", marginTop: 8}}>
          <a href="#" style={{fontSize: 13, fontWeight: 700, textDecoration: "underline"}}>¿Te olvidaste la clave?</a>
          <button className="btn btn-primary" onClick={onLogin}>
            Entrar →
          </button>
        </div>
      </div>
    </div>
  );
}

window.LoginScreen = LoginScreen;
