import Link from "next/link";

export type Crumb = { label: string; href?: string };

export default function Breadcrumb({ crumbs }: { crumbs: Crumb[] }) {
  if (crumbs.length === 0) return null;
  return (
    <nav
      aria-label="Breadcrumb"
      style={{
        background: "var(--chirri-cream)",
        borderBottom: "1.5px solid var(--chirri-line)",
        padding: "10px 28px",
        fontSize: 12,
        fontWeight: 700,
        display: "flex",
        alignItems: "center",
        gap: 8,
        flexWrap: "wrap",
      }}
    >
      {crumbs.map((c, i) => (
        <span key={i} style={{ display: "inline-flex", alignItems: "center", gap: 8 }}>
          {i > 0 && <span style={{ opacity: 0.4 }}>›</span>}
          {c.href ? (
            <Link
              href={c.href}
              style={{
                textDecoration: "none",
                color: "var(--chirri-black)",
                opacity: 0.7,
              }}
            >
              {c.label}
            </Link>
          ) : (
            <span>{c.label}</span>
          )}
        </span>
      ))}
    </nav>
  );
}
