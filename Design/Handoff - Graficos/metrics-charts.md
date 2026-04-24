# Handoff — Sección de métricas con gráfico (Polaroid)

Dos variantes del mismo bloque, apiladas: **misma card con gráfico de líneas** y **misma card con gráfico de barras**. Ambas comparten layout, tipografía, paleta y helpers — solo cambia el chart.

Esto es un módulo **autocontenido**. No depende del resto del reporte ni de otras secciones del portal. Podés meterlo en cualquier página que tenga las variables CSS base de Chirri (ver al final).

---

## 1. Estructura del bloque

```
┌───────────────────────────────────────────────────┐
│                  [ NÚMEROS · MARZO ]              │   ← Pill centrado
├───────────────────────────────────────────────────┤
│  Card 1 · Polaroid + gráfico de LÍNEAS            │
├───────────────────────────────────────────────────┤
│  Card 2 · Polaroid + gráfico de BARRAS            │
└───────────────────────────────────────────────────┘
```

Cada card tiene la misma anatomía:

```
┌─────────────────────────────────────────────┐
│  ● [ 📸 followers instagram ]               │   pill con emoji + label
│                                              │
│  cuántas personas nos siguen                 │   caption grande (font-display)
│  al cierre de cada mes.                      │
│                                              │
│  ┌──────────────┐   ┌──────────────────────┐│
│  │ CIERRE MARZO │   │     ▄▄▄▄▄▄▄▄         ││
│  │              │   │   [ polaroid con     ││
│  │   110.240    │   │     cinta amarilla   ││
│  │              │   │     arriba y chart ] ││
│  │  [▲ +3.0%]   │   │                      ││
│  └──────────────┘   │  dic · ene · feb·mar ││
│                     └──────────────────────┘│
└─────────────────────────────────────────────┘
```

- **Izquierda (~40%):** label "cierre marzo" + número XXL + pill de delta negro/amarillo.
- **Derecha (~60%):** "polaroid" (card blanca con borde negro + sombra dura) con una cinta amarilla translúcida pegada arriba, el chart adentro, y pie de foto con los meses abreviados.
- **Blob de color** (círculo grande) atrás arriba-derecha, con `opacity: 0.55`, del color accent de la métrica.

---

## 2. Código completo — pegable tal cual

Archivo sugerido: `components/MetricsPolaroid.jsx`

```jsx
// ============================================================
// Helpers de formato y cálculo
// ============================================================
function fmtNum(v, unit) {
  if (unit === "%") return v.toFixed(1) + "%";
  if (unit === "M") return v.toFixed(2) + "M";
  if (v >= 1000) return v.toLocaleString("es-AR");
  return String(v);
}

function calcDelta(values) {
  const prev = values[values.length - 2];
  const curr = values[values.length - 1];
  return (curr - prev) / prev * 100;
}

function accentBg(a) {
  return {
    pink:   "var(--chirri-pink)",
    mint:   "var(--chirri-mint)",
    yellow: "var(--chirri-yellow)",
  }[a] || "var(--chirri-cream)";
}

function accentDeep(a) {
  return {
    pink:   "var(--chirri-pink-deep)",
    mint:   "var(--chirri-mint-deep)",
    yellow: "#E5B800",
  }[a] || "var(--chirri-black)";
}

// ============================================================
// Pill con emoji + label
// ============================================================
function MetricPill({ metric }) {
  return (
    <div style={{
      alignSelf: "flex-start",
      display: "inline-flex", alignItems: "center", gap: 6,
      padding: "5px 11px",
      background: accentBg(metric.accent),
      border: "2px solid var(--chirri-black)",
      borderRadius: 999,
      fontSize: 10.5, fontWeight: 800,
      letterSpacing: "0.12em", textTransform: "uppercase"
    }}>
      <span style={{ fontSize: 12 }}>{metric.emoji}</span>
      {metric.label}
    </div>
  );
}

// ============================================================
// Chart · LÍNEAS
// ============================================================
function LineChart({ values, accent, months }) {
  const w = 640, h = 220, padL = 40, padR = 28, padT = 28, padB = 32;
  const max = Math.max(...values);
  const min = Math.min(...values);
  const range = max - min || 1;
  const pts = values.map((v, i) => ({
    x: padL + i / (values.length - 1) * (w - padL - padR),
    y: padT + (1 - (v - min) / range) * (h - padT - padB),
    v,
  }));
  const path = pts.map((p, i) => (i === 0 ? "M" : "L") + p.x + " " + p.y).join(" ");
  return (
    <svg viewBox={`0 0 ${w} ${h}`} style={{ width: "100%", height: "auto", display: "block" }}>
      <line x1={padL} x2={w - padR} y1={h - padB} y2={h - padB}
            stroke="var(--chirri-black)" strokeWidth="1.5" />
      <path d={path} fill="none" stroke={accentDeep(accent)}
            strokeWidth="3.5" strokeLinejoin="round" strokeLinecap="round" />
      {pts.map((p, i) => {
        const isLast = i === pts.length - 1;
        return (
          <circle key={i} cx={p.x} cy={p.y} r={isLast ? 7 : 5}
                  fill={isLast ? accentDeep(accent) : "white"}
                  stroke={accentDeep(accent)} strokeWidth="3" />
        );
      })}
      {pts.map((p, i) => (
        <text key={"m" + i} x={p.x} y={h - 12} textAnchor="middle"
              fontFamily="var(--font-ui)" fontSize="11.5"
              fontWeight={i === pts.length - 1 ? 800 : 600}
              fill={i === pts.length - 1 ? "var(--chirri-black)" : "var(--chirri-muted)"}>
          {months[i]}
        </text>
      ))}
    </svg>
  );
}

// ============================================================
// Chart · BARRAS
// ============================================================
function BarsChart({ values, accent, months }) {
  const w = 640, h = 220, padL = 28, padR = 28, padT = 28, padB = 32;
  const max = Math.max(...values) * 1.05;
  const barGap = 28;
  const availW = w - padL - padR - barGap * (values.length - 1);
  const barW = availW / values.length;
  return (
    <svg viewBox={`0 0 ${w} ${h}`} style={{ width: "100%", height: "auto", display: "block" }}>
      <line x1={padL} x2={w - padR} y1={h - padB} y2={h - padB}
            stroke="var(--chirri-black)" strokeWidth="2" />
      {values.map((v, i) => {
        const isLast = i === values.length - 1;
        const x = padL + i * (barW + barGap);
        const bh = v / max * (h - padT - padB);
        const y = h - padB - bh;
        return (
          <g key={i}>
            <rect x={x} y={y} width={barW} height={bh}
                  fill={isLast ? accentDeep(accent) : accentBg(accent)}
                  stroke="var(--chirri-black)" strokeWidth="2" rx="3" />
            <text x={x + barW / 2} y={h - 12} textAnchor="middle"
                  fontFamily="var(--font-ui)" fontSize="11.5"
                  fontWeight={isLast ? 800 : 600}
                  fill={isLast ? "var(--chirri-black)" : "var(--chirri-muted)"}>
              {months[i]}
            </text>
          </g>
        );
      })}
    </svg>
  );
}

// ============================================================
// Card · Polaroid (layout compartido por ambas variantes)
// ============================================================
function PolaroidCard({ metric, months, Chart }) {
  const curr = metric.values[metric.values.length - 1];
  const monthPct = calcDelta(metric.values);
  const up = monthPct >= 0;
  const prevMonthName = months[months.length - 2];

  return (
    <div style={{
      background: "var(--chirri-cream)",
      border: "2.5px solid var(--chirri-black)",
      borderRadius: 20,
      boxShadow: "5px 5px 0 var(--chirri-black)",
      padding: "28px 32px 36px",
      position: "relative",
      overflow: "hidden",
    }}>
      {/* Blob decorativo */}
      <div style={{
        position: "absolute", top: -60, right: -40,
        width: 220, height: 220, borderRadius: "50%",
        background: accentBg(metric.accent), opacity: 0.55,
      }} />

      {/* Header: pill + caption grande */}
      <div style={{
        position: "relative", zIndex: 1,
        display: "flex", flexDirection: "column", gap: 14, marginBottom: 24,
      }}>
        <MetricPill metric={metric} />
        <p className="font-display" style={{
          margin: 0, fontSize: 34, lineHeight: 1.1, fontWeight: 400,
          letterSpacing: "-0.02em", textTransform: "lowercase", maxWidth: 760,
        }}>
          {metric.caption.toLowerCase()}
        </p>
      </div>

      {/* Body: número + polaroid */}
      <div style={{
        position: "relative", zIndex: 1,
        display: "grid",
        gridTemplateColumns: "minmax(240px, 0.7fr) minmax(380px, 1.3fr)",
        gap: 32, alignItems: "center",
      }}>
        {/* Izquierda: número + delta */}
        <div>
          <div style={{
            fontSize: 11, fontWeight: 700, letterSpacing: "0.14em",
            opacity: 0.55, textTransform: "uppercase", marginBottom: 6,
          }}>
            cierre marzo
          </div>
          <div className="font-display" style={{
            fontSize: 92, lineHeight: 0.85, letterSpacing: "-0.04em",
          }}>
            {fmtNum(curr, metric.unit)}
          </div>
          <div style={{
            marginTop: 14,
            display: "inline-flex", alignItems: "center", gap: 6,
            padding: "5px 12px",
            background: "var(--chirri-black)",
            color: "var(--chirri-yellow)",
            borderRadius: 999, fontSize: 13, fontWeight: 800,
          }}>
            {up ? "▲" : "▼"} {up ? "+" : ""}{monthPct.toFixed(1)}% vs {prevMonthName.toLowerCase()}
          </div>
        </div>

        {/* Derecha: polaroid con cinta amarilla */}
        <div style={{
          background: "white",
          border: "2px solid var(--chirri-black)",
          boxShadow: "3px 3px 0 var(--chirri-black)",
          padding: "20px 20px 16px",
          position: "relative",
        }}>
          {/* Cinta washi amarilla translúcida */}
          <div style={{
            position: "absolute", top: -11, left: "50%",
            transform: "translateX(-50%)",
            width: 84, height: 22,
            background: "rgba(255,220,120,0.75)",
            border: "1px solid rgba(0,0,0,0.15)",
          }} />

          <Chart values={metric.values} accent={metric.accent} months={months} />

          <div style={{
            marginTop: 8,
            fontFamily: "var(--font-mono)", fontSize: 10,
            letterSpacing: "0.1em", opacity: 0.55, textAlign: "center",
          }}>
            dic · ene · feb · mar
          </div>
        </div>
      </div>
    </div>
  );
}

// ============================================================
// Bloque completo — pill + 2 cards apilados
// ============================================================
export function MetricsPolaroidSection({ metric, months, monthLabel }) {
  return (
    <section style={{ marginBottom: 64 }}>
      {/* Pill de título */}
      <div style={{ display: "flex", justifyContent: "center", marginBottom: 28 }}>
        <span style={{
          display: "inline-flex", alignItems: "center", gap: 6,
          padding: "5px 12px",
          background: "var(--chirri-yellow)",
          border: "2px solid var(--chirri-black)",
          borderRadius: 999,
          fontSize: 11, fontWeight: 800,
          letterSpacing: "0.14em", textTransform: "uppercase",
          fontFamily: "var(--font-display)",
        }}>
          NÚMEROS · {monthLabel.toUpperCase()}
        </span>
      </div>

      {/* Card con líneas */}
      <div style={{ marginBottom: 24 }}>
        <PolaroidCard metric={metric} months={months} Chart={LineChart} />
      </div>

      {/* Card con barras */}
      <div>
        <PolaroidCard metric={metric} months={months} Chart={BarsChart} />
      </div>
    </section>
  );
}
```

---

## 3. Cómo usarlo

```jsx
<MetricsPolaroidSection
  monthLabel="Marzo 2026"
  months={["Diciembre", "Enero", "Febrero", "Marzo"]}
  metric={{
    id: "followers_ig",
    label: "Followers Instagram",
    emoji: "📸",
    unit: "",                                // "", "%", o "M"
    values: [99500, 104568, 107072, 110240], // 4 meses
    accent: "pink",                          // "pink" | "mint" | "yellow"
    caption: "Cuántas personas nos siguen al cierre de cada mes.",
  }}
/>
```

**Shape de `metric`:**

| Campo     | Tipo          | Notas                                                    |
|-----------|---------------|----------------------------------------------------------|
| `label`   | string        | Título corto del pill                                    |
| `emoji`   | string        | 1 emoji — va dentro del pill                             |
| `unit`    | `"" \| "%" \| "M"` | Cómo formatear el número grande                     |
| `values`  | number[4]     | Un valor por mes, ordenados cronológicamente             |
| `accent`  | `"pink" \| "mint" \| "yellow"` | Define blob, pill y color del chart     |
| `caption` | string        | Frase explicativa — se renderiza en lowercase            |

`values` **debe tener 4 elementos** (dic-ene-feb-mar). Si cambiás la cantidad de meses, actualizá también `months` y el "dic · ene · feb · mar" hardcodeado en el pie del polaroid.

---

## 4. Variables CSS requeridas

Asumen que ya están en tu stylesheet global (son las mismas que usa el resto del portal):

```css
:root {
  --chirri-cream:      #FFF6E3;
  --chirri-black:      #121212;
  --chirri-muted:      rgba(18, 18, 18, 0.55);

  --chirri-yellow:     #FFE74C;
  --chirri-pink:       #FFD6E4;
  --chirri-pink-deep:  #F478A8;
  --chirri-mint:       #BFEFE4;
  --chirri-mint-deep:  #00C9B7;

  --font-display: "Archivo Black", Impact, sans-serif;
  --font-ui:      "Inter", system-ui, sans-serif;
  --font-mono:    "JetBrains Mono", ui-monospace, monospace;
}
```

Si alguna no existe en tu proyecto, copiala tal cual — no inventes equivalencias.

---

## 5. Notas de diseño (para no romper el look)

- **La "polaroid" es literal:** fondo blanco, borde negro 2px, sombra `3px 3px 0` negra. La cinta arriba NO es un rect colorido sólido — es `rgba(255,220,120,0.75)` para que se lea como washi tape translúcido.
- **El blob de fondo** usa `opacity: 0.55` — no lo subas, el chart pierde contraste.
- **El número grande** es `font-display` a 92px con `lineHeight: 0.85`. No uses line-height default o el delta pill queda muy separado.
- **El pill de delta** es negro con texto amarillo — es consistente con otros pills "de acento" del portal. No usar colores semánticos (verde/rojo) para delta; todo Chirri evita eso.
- **El chart de barras** resalta el último mes con `accentDeep` (el color "fuerte") y el resto con `accentBg` (el pastel). El de líneas hace lo mismo con el último punto: círculo más grande y relleno en lugar de hueco.
- **Los meses en el eje X** están abreviados (`DIC · ENE · FEB · MAR`) **dos veces**: como `<text>` dentro del SVG Y como pie de foto debajo del polaroid. Parece redundante pero refuerza la metáfora de "foto con caption".

---

## 6. Checklist

- [ ] `components/MetricsPolaroid.jsx` creado con el código de arriba
- [ ] Variables CSS presentes en el stylesheet global
- [ ] Fuentes cargadas (`Archivo Black`, `Inter`, `JetBrains Mono`)
- [ ] Testear con al menos una métrica de cada `accent` (pink/mint/yellow)
- [ ] Testear con `unit: "%"` y `unit: "M"` para confirmar formato del número grande
