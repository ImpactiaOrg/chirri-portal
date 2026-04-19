// Rewritten for Chirri brand: sans-serif Archivo Black, pills, blobs, stickers

function Pill({ children, color = "mint", className = "", style }) {
  return <span className={"pill-title " + color + " " + className} style={style}>{children}</span>;
}

function StageTag({ id, name }) {
  const colors = {
    awareness: "tag-neutral",
    educacion: "tag-organic",
    validacion: "tag-influencer",
    conversion: "tag-paid"
  };
  return <span className={"tag " + (colors[id] || "tag-neutral")}>{name}</span>;
}

function SourceLegend() {
  return (
    <div style={{display: "flex", gap: 18, fontSize: 12, fontWeight: 700, alignItems: "center", flexWrap: "wrap"}}>
      <span style={{display: "inline-flex", alignItems: "center", gap: 6}}>
        <span className="dot-source dot-organic" /> ORGÁNICO
      </span>
      <span style={{display: "inline-flex", alignItems: "center", gap: 6}}>
        <span className="dot-source dot-influencer" /> INFLUENCER
      </span>
      <span style={{display: "inline-flex", alignItems: "center", gap: 6}}>
        <span className="dot-source dot-paid" /> PAUTA
      </span>
    </div>
  );
}

function Kpi({ label, value, unit, delta, ctx, color = "white" }) {
  const up = typeof delta === "number" && delta > 0;
  const dn = typeof delta === "number" && delta < 0;
  const bg = color === "white" ? "white" : color === "pink" ? "var(--chirri-pink)" : color === "mint" ? "var(--chirri-mint)" : color === "yellow" ? "var(--chirri-yellow)" : "white";
  return (
    <div className="kpi" style={{background: bg}}>
      <div className="kpi-label">{label}</div>
      <div className="kpi-value">
        <span>{value}</span>
        {unit && <span className="unit">{unit}</span>}
      </div>
      <div className={"kpi-delta " + (up ? "up" : dn ? "down" : "")}>
        {up ? "▲" : dn ? "▼" : "·"} {Math.abs(delta)}% vs feb
      </div>
    </div>
  );
}

function Donut({ segments, size = 240, stroke = 36 }) {
  const total = segments.reduce((a, b) => a + b.value, 0);
  const r = (size - stroke) / 2;
  const c = 2 * Math.PI * r;
  let offset = 0;
  return (
    <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`} style={{transform: "rotate(-90deg)"}}>
      <circle cx={size/2} cy={size/2} r={r} fill="none" stroke="white" strokeWidth={stroke} />
      <circle cx={size/2} cy={size/2} r={r + stroke/2} fill="none" stroke="var(--chirri-black)" strokeWidth={2.5} />
      <circle cx={size/2} cy={size/2} r={r - stroke/2} fill="none" stroke="var(--chirri-black)" strokeWidth={2.5} />
      {segments.map((s, i) => {
        const len = (s.value / total) * c;
        const circle = (
          <circle key={i} cx={size/2} cy={size/2} r={r} fill="none" stroke={s.color}
            strokeWidth={stroke} strokeDasharray={`${len} ${c - len}`} strokeDashoffset={-offset}
            style={{transition: "stroke-dasharray 800ms ease"}}
          />
        );
        offset += len;
        return circle;
      })}
    </svg>
  );
}

function fmtK(n) {
  if (n >= 1_000_000) return (n / 1_000_000).toFixed(n >= 10_000_000 ? 0 : 2) + "M";
  if (n >= 1000) return (n / 1000).toFixed(n >= 100000 ? 0 : 1) + "K";
  return String(n);
}

function BalanzMark({ size = 28, dark = false }) {
  return (
    <span style={{
      display: "inline-flex", alignItems: "center", gap: 6,
      fontFamily: "'Archivo Black', sans-serif",
      fontSize: size, color: dark ? "white" : "var(--balanz-blue)",
      letterSpacing: "-0.02em", lineHeight: 1
    }}>
      <span style={{
        width: size * 0.78, height: size * 0.78,
        background: "var(--balanz-teal)",
        borderRadius: size * 0.14,
        transform: "rotate(45deg)", display: "inline-block"
      }} />
      <span>Balanz</span>
    </span>
  );
}

function TenantDot() {
  return (
    <div style={{
      width: 26, height: 26, borderRadius: "50%",
      background: "var(--balanz-blue)",
      display: "flex", alignItems: "center", justifyContent: "center",
      border: "1.5px solid var(--chirri-black)"
    }}>
      <div style={{
        width: 10, height: 10, background: "var(--balanz-teal)",
        transform: "rotate(45deg)", borderRadius: 2
      }} />
    </div>
  );
}

// Decorative sticker cluster (matches PDF scrapbook vibe)
function Stickers({ variant = "corner" }) {
  if (variant === "corner") {
    return (
      <>
        <div className="blob-mint" style={{top: -60, left: -40, transform: "rotate(-20deg)"}} />
        <div className="blob-pink" style={{bottom: -80, right: -60, transform: "rotate(30deg)"}} />
        <div className="sticker" style={{top: 20, right: 80, fontSize: 36, color: "var(--chirri-mint-deep)", transform: "rotate(12deg)"}}>✳</div>
        <div className="sticker" style={{bottom: 40, left: 60, fontSize: 28, color: "var(--chirri-pink-deep)", transform: "rotate(-8deg)"}}>✳</div>
      </>
    );
  }
  return null;
}

function IgTile({ label = "Reel", bg = "linear-gradient(135deg, #FFE74C, #FFB3D1)" }) {
  return (
    <div className="ig-tile" style={{background: bg}}>
      <div style={{
        position: "absolute", left: 10, top: 10,
        fontFamily: "var(--font-mono)", fontSize: 10, textTransform: "uppercase",
        letterSpacing: "0.12em", color: "var(--chirri-black)",
        background: "white", padding: "3px 8px", borderRadius: 4,
        border: "1.5px solid var(--chirri-black)", fontWeight: 700
      }}>{label}</div>
    </div>
  );
}

Object.assign(window, { Pill, StageTag, SourceLegend, Kpi, Donut, fmtK, BalanzMark, TenantDot, Stickers, IgTile });
