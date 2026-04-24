# Handoff — Logo update (header, login, favicon)

Cambios quirúrgicos al logo del Portal. **No toques nada más del sistema.** Son tres cosas:

1. El wordmark "chirri" se estira verticalmente y engruesa
2. El pill "PORTAL" queda invertido (amarillo con borde y sombra rosa, ✳ menta adentro) y rotado -3°
3. Se agrega un favicon nuevo: monograma "ch" (mismo estilo que el logo, amarillo sobre negro)

---

## 1. Header (topbar)

**Archivo:** wherever `TopBar` lives (probablemente `components/TopBar.jsx` o similar — el bloque que contiene `className="topbar-left"` + el logo anchor).

**Reemplazar el bloque del logo + pill PORTAL por esto:**

```jsx
<a
  href="/"
  className="logo-chirri"
  onClick={(e) => { e.preventDefault(); /* nav a home */ }}
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
</a>

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
  <span style={{ color: "var(--chirri-mint-deep)", fontFamily: "Georgia, serif", fontSize: 11, marginTop: -1 }}>✳</span>
  PORTAL
</span>

{/* Separador entre logo-block y nav, para que el pill no compita con el estado activo del nav */}
<span style={{ width: 1, height: 22, background: "var(--chirri-line-strong)", marginLeft: 8, marginRight: 4 }} />
```

**Claves a no romper:**

- El pill **NO** debe ser negro con texto amarillo — eso chocaba visualmente con el estado activo del nav (también negro con amarillo).
- El `scaleY(1.18)` + `WebkitTextStroke: 0.3px` es lo que le da el aspecto "estirado y gordo" sin que las letras "rri" se peguen. No subas el stroke ni bajes más el letter-spacing — las letras se fusionan.

---

## 2. Pantalla de login

**Archivo:** `screens/Login.jsx` (o donde tengas el hero del login con `"chirri" + PORTAL`).

**Reemplazar el bloque del logo + pill por esto** (versión grande, mismos principios que el header pero a escala hero):

```jsx
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
    <span style={{ color: "var(--chirri-mint-deep)", fontFamily: "Georgia, serif", fontSize: 14 }}>✳</span>
    PORTAL
  </span>
</div>
```

**Nota:** en el login SÍ usamos el pill negro con texto amarillo (la versión "marca plena"), porque en el hero no hay nav activo al lado con el que pueda confundirse. Es una decisión contextual — header usa pill invertido, login usa pill normal.

---

## 3. Favicon — monograma "ch"

**Archivos ya listos en este handoff folder** (copialos tal cual al proyecto):

- `favicon.svg` → `public/favicon.svg`
- `favicon-32.png` → `public/favicon-32.png`
- `favicon-180.png` → `public/apple-touch-icon.png` (renombrar)
- `favicon-512.png` → `public/icon-512.png` (opcional, para PWA manifest)

**HTML — agregar en `<head>` del `index.html`:**

```html
<link rel="icon" type="image/svg+xml" href="/favicon.svg" />
<link rel="icon" type="image/png" sizes="32x32" href="/favicon-32.png" />
<link rel="apple-touch-icon" sizes="180x180" href="/apple-touch-icon.png" />
```

---

## 4. Loading spinner — monograma "ch" pulsante

**Archivo nuevo:** `components/Spinner.jsx`

Mismo monograma del favicon, animado. Dos variantes: pulse (default) y rotate. El "ch" estirado aparece sobre un cuadrado negro con borde redondeado — matchea la identidad del header.

```jsx
// components/Spinner.jsx
export function ChSpinner({ size = 64, variant = "pulse" }) {
  const animation = variant === "rotate"
    ? "ch-spin-rotate 1.2s ease-in-out infinite"
    : "ch-spin-pulse 1.1s ease-in-out infinite";

  return (
    <div
      role="status"
      aria-label="Cargando"
      style={{
        width: size,
        height: size,
        borderRadius: size * 0.22,
        background: "var(--chirri-black)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        animation,
        boxShadow: `${size * 0.06}px ${size * 0.06}px 0 var(--chirri-pink-deep)`,
      }}
    >
      <span
        style={{
          fontFamily: "var(--font-display)",
          fontWeight: 900,
          fontSize: size * 0.7,
          color: "var(--chirri-yellow)",
          letterSpacing: "-0.04em",
          display: "inline-block",
          transform: "scaleY(1.2)",
          transformOrigin: "center",
          lineHeight: 0.9,
          WebkitTextStroke: `${size * 0.008}px currentColor`,
          userSelect: "none",
        }}
      >
        ch
      </span>
    </div>
  );
}
```

**CSS global — agregar a tu stylesheet:**

```css
@keyframes ch-spin-pulse {
  0%, 100% { transform: scale(1) rotate(-2deg); }
  50%      { transform: scale(1.08) rotate(2deg); }
}

@keyframes ch-spin-rotate {
  0%   { transform: rotate(-8deg); }
  50%  { transform: rotate(8deg); }
  100% { transform: rotate(-8deg); }
}
```

**Uso:**

```jsx
<ChSpinner />                      // default: 64px pulse
<ChSpinner size={96} />             // más grande
<ChSpinner size={40} variant="rotate" />  // variante wiggle
```

**Para pantalla de loading a página completa:**

```jsx
<div style={{
  position: "fixed", inset: 0,
  display: "flex", alignItems: "center", justifyContent: "center",
  flexDirection: "column", gap: 20,
  background: "var(--chirri-cream, #FFF6E3)",
  zIndex: 9999
}}>
  <ChSpinner size={80} />
  <div style={{ fontFamily: "var(--font-display)", fontSize: 14, letterSpacing: "0.08em" }}>
    cargando…
  </div>
</div>
```

---

## Variables CSS que se usan

Todos estos valores asumen que ya tenés en tu stylesheet global:

```css
:root {
  --chirri-yellow: #FFE74C;
  --chirri-pink-deep: #F478A8;
  --chirri-mint-deep: #00C9B7; /* o el que estés usando */
  --chirri-black: #121212;
  --chirri-line-strong: rgba(18, 18, 18, 0.32);
  --font-display: "Archivo Black", Impact, sans-serif;
}
```

Si faltan, agregalos. No inventes valores nuevos.

---

## Checklist final

- [ ] Header: logo "chirri" estirado + pill PORTAL amarillo-con-borde + separador
- [ ] Login: logo "chirri" estirado (más grande) + pill PORTAL negro (versión hero)
- [ ] `favicon.svg` + PNGs copiados a `public/` y linkeados en `index.html`
- [ ] `components/Spinner.jsx` creado + keyframes CSS agregados
- [ ] Verificar que el "rri" no queda pegado (stroke bajo, letter-spacing moderado)
- [ ] Verificar que el estado activo del nav (negro + amarillo) no se confunde con el pill PORTAL del header
