import { redirect } from "next/navigation";
import { apiFetch, type CampaignDto, type PagedResponse } from "@/lib/api";
import { getAccessToken, getCurrentUser } from "@/lib/auth";
import TopBar from "@/components/top-bar";
import Breadcrumb from "@/components/breadcrumb";
import { campaignsListCrumbs } from "@/lib/breadcrumbs";
import CampaignCardBig from "./CampaignCardBig";
import CampaignRowArchived from "./CampaignRowArchived";

export default async function CampaignsPage() {
  const user = await getCurrentUser();
  if (!user) redirect("/login");

  const token = getAccessToken();

  let campaigns: CampaignDto[] = [];
  try {
    const res = await apiFetch<PagedResponse<CampaignDto> | CampaignDto[]>(
      "/api/campaigns/",
      { token },
    );
    campaigns = Array.isArray(res) ? res : res.results;
  } catch (err) {
    console.error("campaigns_fetch_failed", {
      url: "/api/campaigns/",
      error: err instanceof Error ? err.message : String(err),
      hasJwt: !!token,
    });
  }

  const active = campaigns.filter((c) => c.status === "ACTIVE");
  const archived = campaigns.filter((c) => c.status !== "ACTIVE");

  return (
    <>
      <TopBar user={user} active="campaigns" />
      <Breadcrumb crumbs={campaignsListCrumbs(user)} />
      <main className="page page-wide" style={{ background: "var(--chirri-pink)" }}>
        <section style={{ marginBottom: 40 }}>
          <h1 className="display-xl">campañas.</h1>
          <p
            style={{
              fontSize: 16,
              maxWidth: 620,
              marginTop: 14,
              lineHeight: 1.5,
              fontWeight: 500,
            }}
          >
            Las activas arriba. Abajo quedan archivadas las terminadas — podés abrir cualquiera para ver el cierre y los reportes de esa etapa.
          </p>
        </section>

        <section style={{ marginBottom: 48 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 14, marginBottom: 20 }}>
            <span className="pill-title mint">ACTIVAS · {active.length}</span>
          </div>
          <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
            {active.map((c, i) => (
              <CampaignCardBig key={c.id} campaign={c} colorIndex={i} />
            ))}
          </div>
        </section>

        <section
          style={{
            borderTop: "3px solid var(--chirri-black)",
            paddingTop: 36,
            marginTop: 48,
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: 14, marginBottom: 20 }}>
            <span className="pill-title white">ARCHIVO · {archived.length}</span>
            <span style={{ fontSize: 12, fontWeight: 600, color: "var(--chirri-muted)" }}>
              Campañas terminadas
            </span>
          </div>
          <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
            {archived.map((c) => (
              <CampaignRowArchived key={c.id} campaign={c} />
            ))}
          </div>
        </section>
      </main>
    </>
  );
}
