"use client";

import { useState, useTransition } from "react";
import { loginAction } from "./actions";

export default function LoginForm() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [pending, startTransition] = useTransition();

  const submit = (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    startTransition(async () => {
      const result = await loginAction({ email, password });
      if (result?.error) setError(result.error);
    });
  };

  return (
    <form className="login-form" onSubmit={submit}>
      <div>
        <div
          style={{
            fontSize: 11,
            fontWeight: 800,
            letterSpacing: "0.14em",
            textTransform: "uppercase",
          }}
        >
          Chirri Portal · Acceso clientes
        </div>
        <h1
          className="font-display"
          style={{
            fontSize: 64,
            lineHeight: 0.9,
            letterSpacing: "-0.03em",
            margin: "4px 0 0",
            textTransform: "lowercase",
          }}
        >
          hola de<br />nuevo.
        </h1>
        <p style={{ fontSize: 14, marginTop: 10, fontWeight: 500, maxWidth: 360 }}>
          Entrá a <b>Chirri Portal</b> y mirá tu mes.
        </p>
      </div>

      {error && <div className="error-banner">{error}</div>}

      <div className="input-row">
        <label htmlFor="email">Email</label>
        <input
          id="email"
          type="email"
          required
          autoComplete="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          disabled={pending}
        />
      </div>
      <div className="input-row">
        <label htmlFor="password">Contraseña</label>
        <input
          id="password"
          type="password"
          required
          autoComplete="current-password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          disabled={pending}
        />
      </div>

      <div
        style={{
          display: "flex",
          justifyContent: "flex-end",
          alignItems: "center",
          marginTop: 8,
        }}
      >
        <button type="submit" className="btn btn-primary" disabled={pending}>
          {pending ? "Entrando…" : "Entrar →"}
        </button>
      </div>
    </form>
  );
}
