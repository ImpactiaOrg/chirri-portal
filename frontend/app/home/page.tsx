import { redirect } from "next/navigation";
import Link from "next/link";
import { apiFetch, type CampaignDto, type PagedResponse, type ReportDto } from "@/lib/api";
import { getAccessToken, getCurrentUser } from "@/lib/auth";
import { formatMonthYear } from "@/lib/format";
import TopBar from "@/components/top-bar";

function firstName(full: string, fallback: string): string {
  const first = full.trim().split(/\s+/)[0];
  return (first || fallback).toLowerCase();
}

function sumReach(report: ReportDto | null): number {
  if (!report) return 0;
  return report.metrics
    .filter((m) => m.metric_name === "reach")
    .reduce((acc, m) => acc + Number(m.value), 0);
}

function formatCompact(n: number): { value: string; unit: string } {
  if (n >= 1_000_000) return { value: (n / 1_000_000).toFixed(2).replace(/\.?0+$/, ""), unit: "M" };
  if (n >= 1_000) return { value: (n / 1_000).toFixed(0), unit: "K" };
  return { value: String(n), unit: "" };
}

export default async function HomePage() {
  const user = await getCurrentUser();
  if (!user) redirect("/login");

  const token = getAccessToken();
  const [campaignsRes, latest] = await Promise.all([
    apiFetch<PagedResponse<CampaignDto> | CampaignDto[]>("/api/campaigns/", { token }),
    apiFetch<ReportDto | null>("/api/reports/latest/", { token }),
  ]);
  const campaigns = Array.isArray(campaignsRes) ? campaignsRes : campaignsRes.results;
  const active = campaigns.filter((c) => c.status === "ACTIVE");
  const finished = campaigns.filter((c) => c.status === "FINISHED");
  const activeCampaign = active[0];

  const totalReach = formatCompact(sumReach(latest));
  const latestMonth = latest?.period_start ? formatMonthYear(latest.period_start) : null;
  const welcomeName = firstName(user.full_name || user.email, "hola");

  return (
    <>
      <TopBar user={user} active="home" />
      <main className="page" style={{ background: "var(--chirri-pink)" }}>
        <section
          style={{
            marginBottom: 40,
            display: "flex",
            alignItems: "flex-end",
            justifyContent: "space-between",
            gap: 40,
            flexWrap: "wrap",
          }}
        >
          <div>
            <div className="eyebrow">Chirri Portal · {user.client?.name ?? "—"}</div>
            <h1
              className="font-display"
              style={{
                fontSize: 88,
                lineHeight: 0.9,
                letterSpacing: "-0.03em",
                margin: "8px 0 0",
                textTransform: "lowercase",
              }}
            >
              buen día,
              <br />
              {welcomeName}.
            </h1>
            <p style={{ fontSize: 16, maxWidth: 520, marginTop: 16, lineHeight: 1.5, fontWeight: 500 }}>
              {latest
                ? <>Cerramos <b>{latestMonth!.month}</b>. Te lo dejamos listo acá abajo.</>
                : "Todavía no hay reportes publicados. En cuanto haya uno nuevo vas a verlo acá."}
            </p>
          </div>
          {latest?.conclusions_text && (
            <div className="chirri-note" style={{ maxWidth: 360 }}>
              {latest.conclusions_text}
              <span className="sig">— CHIRRI</span>
            </div>
          )}
        </section>

        {latest && (
          <Link
            href={`/reports/${latest.id}`}
            className="section-hero"
            style={{ display: "block", textDecoration: "none", color: "inherit", cursor: "pointer" }}
          >
            <div className="blob-mint" style={{ top: -40, right: 80, transform: "rotate(-20deg)" }} />
            <div className="blob-pink" style={{ bottom: -60, left: -40, transform: "rotate(20deg)" }} />
            <div
              style={{
                position: "relative",
                display: "grid",
                gridTemplateColumns: "1fr auto",
                gap: 40,
                alignItems: "end",
              }}
            >
              <div>
                <span className="pill-title" style={{ background: "var(--chirri-black)", color: "var(--chirri-yellow)", boxShadow: "3px 3px 0 var(--chirri-pink-deep)", fontSize: 16, padding: "8px 20px" }}>
                  ÚLTIMO REPORTE
                </span>
                <h2
                  className="font-display"
                  style={{
                    fontSize: 120,
                    lineHeight: 0.85,
                    letterSpacing: "-0.04em",
                    margin: "24px 0 0",
                    textTransform: "lowercase",
                  }}
                >
                  {latestMonth!.month} <span style={{ color: "var(--chirri-pink-deep)" }}>{latestMonth!.year}</span>
                </h2>
                <div style={{ display: "flex", gap: 10, alignItems: "center", marginTop: 12, flexWrap: "wrap" }}>
                  <span className="tag">{latest.campaign_name}</span>
                  <span style={{ fontSize: 12, fontWeight: 700 }}>· Etapa {latest.stage_name}</span>
                </div>
                <p style={{ fontSize: 18, maxWidth: 560, marginTop: 16, lineHeight: 1.5, fontWeight: 500 }}>
                  {latest.display_title}
                </p>
              </div>
              <div style={{ display: "flex", flexDirection: "column", gap: 20, alignItems: "flex-end", minWidth: 220 }}>
                <div style={{ textAlign: "right" }}>
                  <div style={{ fontSize: 10, letterSpacing: "0.14em", fontWeight: 800, textTransform: "uppercase" }}>
                    Total reach
                  </div>
                  <div className="font-display" style={{ fontSize: 96, lineHeight: 1, letterSpacing: "-0.04em" }}>
                    {totalReach.value}
                    <span style={{ fontSize: 36 }}>{totalReach.unit}</span>
                  </div>
                </div>
                <span className="btn btn-primary">Leer reporte →</span>
              </div>
            </div>
          </Link>
        )}

        <section className="grid-3" style={{ marginBottom: 48 }}>
          <Link href="/campaigns" className="card card-pink card-link">
            <div className="eyebrow">Tus campañas</div>
            <h3 className="font-display" style={{ fontSize: 34, margin: "8px 0", lineHeight: 1, textTransform: "lowercase" }}>
              {active.length} activa{active.length === 1 ? "" : "s"}
              <br />+ {finished.length} en archivo
            </h3>
            <p style={{ fontSize: 13, lineHeight: 1.5, margin: "0 0 14px", fontWeight: 500 }}>
              Mirá el recorrido completo o entrá a una campaña terminada.
            </p>
            <span style={{ fontSize: 13, fontWeight: 800, textDecoration: "underline" }}>Ver campañas →</span>
          </Link>

          {activeCampaign ? (
            <Link href={`/campaigns/${activeCampaign.id}`} className="card card-mint card-link">
              <div className="eyebrow">Campaña activa</div>
              <h3 className="font-display" style={{ fontSize: 34, margin: "8px 0", lineHeight: 1, textTransform: "lowercase" }}>
                {activeCampaign.name.toLowerCase()}
              </h3>
              <p style={{ fontSize: 13, lineHeight: 1.5, margin: "0 0 14px", fontWeight: 500 }}>
                {activeCampaign.stage_count} etapa{activeCampaign.stage_count === 1 ? "" : "s"} ·{" "}
                {activeCampaign.published_report_count} reporte
                {activeCampaign.published_report_count === 1 ? "" : "s"} publicado
                {activeCampaign.published_report_count === 1 ? "" : "s"}.
              </p>
              <span style={{ fontSize: 13, fontWeight: 800, textDecoration: "underline" }}>Abrir recorrido →</span>
            </Link>
          ) : (
            <div className="card card-paper" style={{ opacity: 0.72 }}>
              <div className="eyebrow">Campaña activa</div>
              <h3 className="font-display" style={{ fontSize: 28, margin: "8px 0", lineHeight: 1, color: "var(--chirri-muted)" }}>
                sin campañas<br />activas
              </h3>
            </div>
          )}

          <div className="card card-paper" style={{ opacity: 0.72, cursor: "not-allowed" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <div className="eyebrow">Cronograma</div>
              <span className="soon-tag">SOON</span>
            </div>
            <h3 className="font-display" style={{ fontSize: 34, margin: "8px 0", lineHeight: 1, textTransform: "lowercase", color: "var(--chirri-muted)" }}>
              posts por venir
            </h3>
            <p style={{ fontSize: 13, lineHeight: 1.5, margin: 0, fontWeight: 500, color: "var(--chirri-muted)" }}>
              Vas a poder ver y aprobar el cronograma IG acá. Pronto.
            </p>
          </div>
        </section>

        <section>
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 16, marginBottom: 24, flexWrap: "wrap" }}>
            <span className="pill-title mint">HISTORIAL</span>
            <span style={{ fontSize: 13, fontWeight: 500 }}>Últimas campañas</span>
          </div>
          <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
            {[...active, ...finished].map((c) => {
              const lastDate = c.last_published_at ? formatMonthYear(c.last_published_at) : null;
              return (
                <Link key={c.id} href={`/campaigns/${c.id}`} className="history-row clickable">
                  <div className="hr-date">
                    {c.name.toLowerCase()}
                  </div>
                  <div className="hr-subject">
                    {c.brief || <span className="muted">Sin brief cargado.</span>}
                  </div>
                  <div className="hr-kind">
                    {lastDate ? `${lastDate.month} ${lastDate.year}` : "—"}
                  </div>
                  <div className="hr-action">Abrir →</div>
                </Link>
              );
            })}
          </div>
        </section>
      </main>
    </>
  );
}
