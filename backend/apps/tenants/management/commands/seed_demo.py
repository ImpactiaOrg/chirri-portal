"""Seed demo data from the design handoff (Balanz · De Ahorrista a Inversor).

Idempotent: running multiple times updates existing rows rather than duplicating.
Usage:
    python manage.py seed_demo
    python manage.py seed_demo --wipe    # delete Balanz first, then reseed

Post-DEV-116: usa blocks tipados (KpiGridBlock, MetricsTableBlock, TopContentBlock,
AttributionTableBlock, ChartBlock). ReportMetric fue eliminado.
"""
from datetime import date, datetime, timezone
from decimal import Decimal
from pathlib import Path

from django.core.files import File
from django.core.management.base import BaseCommand
from django.db import transaction

from apps.campaigns.models import Campaign, NarrativeLine, Stage
from apps.influencers.models import CampaignInfluencer, Influencer
from apps.reports.choices import Network, SourceType
from apps.reports.models import (
    AttributionTableBlock,
    BrandFollowerSnapshot,
    ChartBlock,
    ChartDataPoint,
    KpiGridBlock,
    KpiTile,
    MetricsTableBlock,
    MetricsTableRow,
    OneLinkAttribution,
    Report,
    TopContent,
    TopContentBlock,
)
from apps.tenants.models import Brand, Client
from apps.users.models import ClientUser

DEMO_PASSWORD = "balanz2026"

BALANZ_BLUE = "#0B2D5B"
BALANZ_TEAL = "#00C9B7"


class Command(BaseCommand):
    help = "Seed demo data from the design handoff (Balanz)."

    def add_arguments(self, parser):
        parser.add_argument("--wipe", action="store_true", help="Delete Balanz data before seeding.")

    @transaction.atomic
    def handle(self, *args, wipe: bool = False, **options):
        if wipe:
            self.stdout.write("Wiping existing Balanz data…")
            Client.objects.filter(name="Balanz").delete()

        client = self._seed_client()
        brand = self._seed_brand(client)
        self._seed_user(client)
        campaigns = self._seed_campaigns(brand)
        stages = self._seed_stages(campaigns["ahorrista-inversor"])
        narrative_lines = self._seed_narrative_lines(campaigns["ahorrista-inversor"])
        influencers = self._seed_influencers(campaigns["ahorrista-inversor"], stages, narrative_lines)
        self._seed_reports(stages)
        self._seed_report_viewer_fixtures(brand)

        self.stdout.write(self.style.SUCCESS("\n✓ Demo data loaded."))
        self.stdout.write(f"  Client: {client.name}")
        self.stdout.write(f"  Brand: {brand.name}")
        self.stdout.write(f"  Campaigns: {len(campaigns)} (1 active + 2 finished)")
        self.stdout.write(f"  Stages (active campaign): {len(stages)}")
        self.stdout.write(f"  Influencers linked: {len(influencers)}")
        self.stdout.write("\n  Login portal:")
        self.stdout.write(self.style.WARNING(f"    email:    belen.rizzo@balanz.com"))
        self.stdout.write(self.style.WARNING(f"    password: {DEMO_PASSWORD}"))

    def _seed_client(self) -> Client:
        client, _ = Client.objects.update_or_create(
            name="Balanz",
            defaults={
                "logo_url": "",
                "primary_color": BALANZ_BLUE,
                "secondary_color": BALANZ_TEAL,
            },
        )
        return client

    def _seed_brand(self, client: Client) -> Brand:
        brand, _ = Brand.objects.update_or_create(
            client=client,
            name="Balanz",
            defaults={"description": "Balanz · broker y app de inversiones."},
        )
        return brand

    def _seed_user(self, client: Client) -> ClientUser:
        user, created = ClientUser.objects.get_or_create(
            email="belen.rizzo@balanz.com",
            defaults={
                "full_name": "Belén Rizzo",
                "client": client,
                "role": ClientUser.Role.ADMIN_CLIENT,
                "is_active": True,
            },
        )
        if created or not user.has_usable_password():
            user.set_password(DEMO_PASSWORD)
            user.save()
        return user

    def _seed_campaigns(self, brand: Brand) -> dict[str, Campaign]:
        specs = [
            {
                "slug": "ahorrista-inversor",
                "name": "De Ahorrista a Inversor",
                "status": Campaign.Status.ACTIVE,
                "start_date": date(2026, 1, 1),
                "end_date": None,
                "brief": (
                    "Acompañar al ahorrista argentino en su viaje a inversor. "
                    "4 actos: Awareness, Educación, Validación, Conversión."
                ),
            },
            {
                "slug": "harry-potter-2025",
                "name": "Harry Potter × Yelmo",
                "status": Campaign.Status.FINISHED,
                "start_date": date(2025, 10, 1),
                "end_date": date(2026, 2, 28),
                "brief": "Campaña cinematográfica alrededor del estreno. Cobranded con Yelmo cines.",
            },
            {
                "slug": "lanzamiento-app",
                "name": "Lanzamiento App v2",
                "status": Campaign.Status.FINISHED,
                "start_date": date(2025, 6, 1),
                "end_date": date(2025, 9, 30),
                "brief": "Relanzamiento de la app con onboarding nuevo. Foco en descargas + primera inversión.",
            },
        ]
        out: dict[str, Campaign] = {}
        for spec in specs:
            slug = spec.pop("slug")
            campaign, _ = Campaign.objects.update_or_create(
                brand=brand,
                name=spec["name"],
                defaults=spec,
            )
            out[slug] = campaign
        return out

    def _seed_stages(self, campaign: Campaign) -> dict[str, Stage]:
        specs = [
            ("awareness", 1, Stage.Kind.AWARENESS, "Awareness",
             "Plantar la idea: 'hay un mundo más allá del plazo fijo'.",
             date(2026, 1, 1), date(2026, 2, 28)),
            ("educacion", 2, Stage.Kind.EDUCATION, "Educación",
             "Bajar tecnicismos. Traducir CEDEARs, Bonos, FCI a humano.",
             date(2026, 2, 1), date(2026, 3, 31)),
            ("validacion", 3, Stage.Kind.VALIDATION, "Validación",
             "Testimonios reales. 'Yo tampoco sabía nada y empecé'.",
             date(2026, 3, 1), date(2026, 4, 30)),
            ("conversion", 4, Stage.Kind.CONVERSION, "Conversión",
             "El call to action. Descargá la app. Empezá hoy.",
             date(2026, 4, 1), date(2026, 5, 31)),
        ]
        out: dict[str, Stage] = {}
        for slug, order, kind, name, desc, start, end in specs:
            stage, _ = Stage.objects.update_or_create(
                campaign=campaign,
                order=order,
                defaults={
                    "kind": kind,
                    "name": name,
                    "description": desc,
                    "start_date": start,
                    "end_date": end,
                },
            )
            out[slug] = stage
        return out

    def _seed_narrative_lines(self, campaign: Campaign) -> dict[str, NarrativeLine]:
        specs = [
            ("Testimonios personales", "Historias reales de gente que empezó desde cero."),
            ("FOMO financiero", "Humor + punzada: 'todos invierten menos yo'."),
            ("Educación simple", "Traducir tecnicismos a lenguaje cotidiano."),
            ("Lo saqué del colchón", "El primer paso: dejar el efectivo parado."),
            ("Rol del asesor", "La figura del asesor financiero como guía."),
        ]
        out: dict[str, NarrativeLine] = {}
        for name, desc in specs:
            nl, _ = NarrativeLine.objects.update_or_create(
                campaign=campaign, name=name, defaults={"description": desc},
            )
            out[name] = nl
        return out

    def _seed_influencers(
        self,
        campaign: Campaign,
        stages: dict[str, Stage],
        narrative_lines: dict[str, NarrativeLine],
    ) -> list[CampaignInfluencer]:
        specs = [
            {
                "handle_ig": "@sofi.gonet", "followers_ig": 1_100_000, "er_ig": Decimal("4.8"),
                "niche": "Lifestyle · finanzas personales",
                "stage_slug": "validacion", "narrative": "Testimonios personales",
                "fee_ars": Decimal("4800000"), "status": CampaignInfluencer.Status.MUST,
                "notes": "Pico de downloads la noche de la publicación.",
            },
            {
                "handle_ig": "@nacho.elizalde", "followers_ig": 540_000, "er_ig": Decimal("6.2"),
                "niche": "Humor financiero",
                "stage_slug": "awareness", "narrative": "FOMO financiero",
                "fee_ars": Decimal("2900000"), "status": CampaignInfluencer.Status.MUST,
                "notes": "Reel con 18% de guardados.",
            },
            {
                "handle_ig": "@martibenza", "followers_ig": 1_000_000, "er_ig": Decimal("3.9"),
                "niche": "Educación financiera para mujeres",
                "stage_slug": "educacion", "narrative": "Educación simple",
                "fee_ars": Decimal("4100000"), "status": CampaignInfluencer.Status.MUST,
                "notes": "Audiencia femenina 25-34 respondió fuerte.",
            },
            {
                "handle_ig": "@flor.sosa", "followers_ig": 470_000, "er_ig": Decimal("4.1"),
                "niche": "Pop + finanzas",
                "stage_slug": "conversion", "narrative": "Lo saqué del colchón",
                "fee_ars": Decimal("2200000"), "status": CampaignInfluencer.Status.MUST,
                "notes": "Próximo mes.",
            },
            {
                "handle_ig": "@coni_fach", "followers_ig": 290_000, "er_ig": Decimal("5.3"),
                "niche": "Educación",
                "stage_slug": None, "narrative": "Educación simple",
                "fee_ars": None, "status": CampaignInfluencer.Status.ALTERNATIVE,
                "notes": "Propuesta.",
            },
            {
                "handle_ig": "@jazmin.bardach", "followers_ig": 340_000, "er_ig": Decimal("4.6"),
                "niche": "Asesoría financiera",
                "stage_slug": None, "narrative": "Rol del asesor",
                "fee_ars": None, "status": CampaignInfluencer.Status.NEGOTIATE_FEE,
                "notes": "Propuesta.",
            },
        ]
        out: list[CampaignInfluencer] = []
        for spec in specs:
            inf, _ = Influencer.objects.update_or_create(
                handle_ig=spec["handle_ig"],
                defaults={
                    "followers_ig": spec["followers_ig"],
                    "er_ig": spec["er_ig"],
                    "niche": spec["niche"],
                    "size_tier": (
                        Influencer.SizeTier.MEGA if spec["followers_ig"] >= 1_000_000
                        else Influencer.SizeTier.MACRO
                    ),
                },
            )
            ci, _ = CampaignInfluencer.objects.update_or_create(
                campaign=campaign, influencer=inf,
                defaults={
                    "stage": stages.get(spec["stage_slug"]) if spec["stage_slug"] else None,
                    "narrative_line": narrative_lines.get(spec["narrative"]),
                    "status": spec["status"],
                    "fee_ars": spec["fee_ars"],
                    "notes": spec["notes"],
                },
            )
            out.append(ci)
        return out

    def _seed_reports(self, stages: dict[str, Stage]) -> None:
        pub = lambda y, m, d: datetime(y, m, d, 12, 0, tzinfo=timezone.utc)

        report_specs = [
            # stage_slug, kind, period_start, period_end, title, status, published, conclusions
            ("awareness", Report.Kind.CIERRE_ETAPA, date(2026, 2, 1), date(2026, 2, 28),
             "Cierre de Awareness", Report.Status.PUBLISHED, pub(2026, 3, 5),
             "Plantamos la duda. El 'hay algo más que el plazo fijo' llegó."),
            ("awareness", Report.Kind.GENERAL, date(2026, 1, 1), date(2026, 1, 31),
             "Reporte general · Enero", Report.Status.PUBLISHED, pub(2026, 2, 2),
             "Primer mes de campaña. Baseline establecido."),

            ("educacion", Report.Kind.GENERAL, date(2026, 3, 1), date(2026, 3, 31),
             "Reporte general · Marzo", Report.Status.PUBLISHED, pub(2026, 4, 2),
             (
                 "Marzo fue el mes donde la campaña dejó de ser un experimento y "
                 "empezó a tener patrón. El carrusel de los 5 errores del ahorrista "
                 "se volvió el contenido más guardado del trimestre (8.2K saves)."
             )),
            ("educacion", Report.Kind.INFLUENCER, date(2026, 3, 1), date(2026, 3, 31),
             "Reporte de influencers · Marzo", Report.Status.PUBLISHED, pub(2026, 4, 2),
             "Marti Benza llevó la narrativa 'educación simple' al prime del mes."),
            ("educacion", Report.Kind.GENERAL, date(2026, 2, 1), date(2026, 2, 28),
             "Reporte general · Febrero", Report.Status.PUBLISHED, pub(2026, 3, 3),
             "Crecimiento sostenido en guardados."),

            ("validacion", Report.Kind.GENERAL, date(2026, 3, 1), date(2026, 3, 31),
             "Reporte general · Marzo", Report.Status.PUBLISHED, pub(2026, 4, 2),
             "Sofi Gonet disparó el pico de downloads la noche del reel."),
            ("validacion", Report.Kind.INFLUENCER, date(2026, 3, 1), date(2026, 3, 31),
             "Reporte de influencers · Marzo", Report.Status.PUBLISHED, pub(2026, 4, 2),
             "Testimonios personales — la narrativa más performante del trimestre."),

            ("conversion", Report.Kind.GENERAL, date(2026, 4, 1), date(2026, 5, 31),
             "Plan de la etapa", Report.Status.DRAFT, None,
             "Borrador del plan de conversión. Llegada de Flor Sosa."),
        ]

        for stage_slug, kind, start, end, title, status, published, conclusions in report_specs:
            stage = stages[stage_slug]
            report, _ = Report.objects.update_or_create(
                stage=stage,
                title=title,
                defaults={
                    "kind": kind,
                    "period_start": start,
                    "period_end": end,
                    "status": status,
                    "published_at": published,
                    "conclusions_text": conclusions,
                },
            )

            # Reset blocks for idempotency (polymorphic delete cascades children).
            report.blocks.all().delete()

            if (
                kind == Report.Kind.GENERAL
                and stage.kind in {Stage.Kind.EDUCATION, Stage.Kind.VALIDATION}
                and start.month == 3
            ):
                _seed_full_layout(report)
            elif status == Report.Status.PUBLISHED:
                _seed_minimal_layout(report)

    def _seed_report_viewer_fixtures(self, brand: Brand) -> None:
        """Populate the Report Viewer fixtures (TopContent, OneLink, FollowerSnapshots).

        Applies to every published report tied at the latest period_start so the
        viewer has renderable data regardless of tie-breaking. Idempotent via
        delete-then-create for per-report fixtures and update_or_create for
        brand-level snapshots.
        """
        fixtures = Path(__file__).parent / "fixtures"

        latest = (
            Report.objects.filter(status=Report.Status.PUBLISHED)
            .order_by("-period_start")
            .first()
        )
        if latest is None:
            return

        target_reports = Report.objects.filter(
            status=Report.Status.PUBLISHED,
            period_start=latest.period_start,
        )

        intro = (
            "Cerramos un mes con crecimiento sostenido en alcance orgánico y un pico "
            "de downloads vía influencers. Acá va el detalle."
        )

        top_content_specs = [
            ("", "placeholder_post_1.jpg"),
            ("", "placeholder_post_2.jpg"),
            ("@pasaje.en.mano", "placeholder_creator_1.jpg"),
        ]
        onelink_specs = [
            ("@pasaje.en.mano", 1200, 180),
            ("@financierapopular", 800, 95),
            ("@pymes_ar", 400, 30),
        ]

        for report in target_reports:
            report.intro_text = intro
            report.save(update_fields=["intro_text"])

            post_block = TopContentBlock.objects.filter(
                report=report, kind="POST",
            ).first()
            creator_block = TopContentBlock.objects.filter(
                report=report, kind="CREATOR",
            ).first()
            attribution_block = AttributionTableBlock.objects.filter(
                report=report,
            ).first()

            # Delete-then-create for idempotency (rerun must not duplicate).
            if post_block is not None:
                TopContent.objects.filter(block=post_block).delete()
            if creator_block is not None:
                TopContent.objects.filter(block=creator_block).delete()
            if attribution_block is not None:
                OneLinkAttribution.objects.filter(attribution_block=attribution_block).delete()

            for i, (handle, fname) in enumerate(top_content_specs, start=1):
                is_creator = bool(handle)
                block = creator_block if is_creator else post_block
                if block is None:
                    continue  # skip if the report wasn't seeded with a matching block
                tc = TopContent(
                    block=block,
                    kind=TopContent.Kind.CREATOR if is_creator else TopContent.Kind.POST,
                    network=Network.INSTAGRAM,
                    source_type=(
                        SourceType.INFLUENCER if is_creator else SourceType.ORGANIC
                    ),
                    rank=i,
                    handle=handle,
                    caption=f"Contenido destacado #{i}",
                    metrics={"likes": 500 * i, "reach": 10000 * i, "er": 3.5 + i * 0.4},
                )
                with open(fixtures / fname, "rb") as fh:
                    tc.thumbnail.save(fname, File(fh), save=False)
                tc.save()

            if attribution_block is not None:
                for handle, clicks, downloads in onelink_specs:
                    OneLinkAttribution.objects.create(
                        attribution_block=attribution_block,
                        influencer_handle=handle,
                        clicks=clicks,
                        app_downloads=downloads,
                    )

        # Brand-level snapshots: one per month, keyed by (brand, network, as_of).
        for month, count in [(1, 99_500), (2, 104_568), (3, 107_072)]:
            BrandFollowerSnapshot.objects.update_or_create(
                brand=brand,
                network=Network.INSTAGRAM,
                as_of=date(latest.period_start.year, month, 28),
                defaults={"followers_count": count},
            )


# ---------------------------------------------------------------------------
# Layout seeders — typed blocks (DEV-116)
# ---------------------------------------------------------------------------

# Follower counts per month (used by follower charts; mirrors BrandFollowerSnapshot).
_IG_FOLLOWERS = [("Enero", 99_500), ("Febrero", 104_568), ("Marzo", 107_072)]
_TIKTOK_FOLLOWERS = [("Enero", 42_000), ("Febrero", 48_300), ("Marzo", 54_100)]
_X_FOLLOWERS = [("Enero", 18_200), ("Febrero", 19_400), ("Marzo", 20_850)]


def _seed_full_layout(report) -> None:
    """11 typed blocks for the rich monthly General report (Educación/Validación Marzo).

    Layout (order 1..11):
      1 KpiGridBlock    — "KPIs del mes" (3 tiles)
      2 MetricsTableBlock — "Mes a mes" (cross-network, delta vs prev month)
      3 MetricsTableBlock — "Instagram" (reach por source_type)
      4 MetricsTableBlock — "TikTok"    (reach por source_type)
      5 MetricsTableBlock — "X / Twitter" (reach por source_type)
      6 TopContentBlock — "Posts del mes"   (kind=POST)
      7 TopContentBlock — "Creators del mes" (kind=CREATOR)
      8 AttributionTableBlock — (show_total=True)
      9 ChartBlock — "Followers IG"      (line, data puntos mensuales)
     10 ChartBlock — "Followers TikTok"  (bar)
     11 ChartBlock — "Followers X"       (bar)
    """
    # 1) KPI Grid
    kpi_grid = KpiGridBlock.objects.create(
        report=report, order=1, title="KPIs del mes",
    )
    KpiTile.objects.bulk_create([
        KpiTile(kpi_grid_block=kpi_grid, order=1,
                label="Reach total", value=Decimal("2840000")),
        KpiTile(kpi_grid_block=kpi_grid, order=2,
                label="Reach orgánico", value=Decimal("412000"),
                period_comparison=Decimal("6.1")),
        KpiTile(kpi_grid_block=kpi_grid, order=3,
                label="Reach influencer", value=Decimal("2430000"),
                period_comparison=Decimal("14.8")),
    ])

    # 2) Mes a mes — cross-network (network=null)
    mtm = MetricsTableBlock.objects.create(
        report=report, order=2, title="Mes a mes", network=None,
    )
    MetricsTableRow.objects.bulk_create([
        MetricsTableRow(metrics_table_block=mtm, order=1,
                        metric_name="engagement_rate", value=Decimal("4.8"),
                        source_type=SourceType.ORGANIC,
                        period_comparison=Decimal("0.3")),
        MetricsTableRow(metrics_table_block=mtm, order=2,
                        metric_name="followers_gained", value=Decimal("18400"),
                        source_type=SourceType.ORGANIC,
                        period_comparison=Decimal("24")),
    ])

    # 3) Instagram — reach per source_type
    ig = MetricsTableBlock.objects.create(
        report=report, order=3, title="Instagram", network=Network.INSTAGRAM,
    )
    MetricsTableRow.objects.bulk_create([
        MetricsTableRow(metrics_table_block=ig, order=1,
                        metric_name="reach", value=Decimal("284000"),
                        source_type=SourceType.ORGANIC,
                        period_comparison=Decimal("6.1")),
        MetricsTableRow(metrics_table_block=ig, order=2,
                        metric_name="reach", value=Decimal("512000"),
                        source_type=SourceType.PAID),
        MetricsTableRow(metrics_table_block=ig, order=3,
                        metric_name="reach", value=Decimal("1640000"),
                        source_type=SourceType.INFLUENCER,
                        period_comparison=Decimal("14.8")),
    ])

    # 4) TikTok
    tk = MetricsTableBlock.objects.create(
        report=report, order=4, title="TikTok", network=Network.TIKTOK,
    )
    MetricsTableRow.objects.bulk_create([
        MetricsTableRow(metrics_table_block=tk, order=1,
                        metric_name="reach", value=Decimal("98000"),
                        source_type=SourceType.ORGANIC),
        MetricsTableRow(metrics_table_block=tk, order=2,
                        metric_name="reach", value=Decimal("180000"),
                        source_type=SourceType.PAID),
        MetricsTableRow(metrics_table_block=tk, order=3,
                        metric_name="reach", value=Decimal("620000"),
                        source_type=SourceType.INFLUENCER),
    ])

    # 5) X / Twitter
    x = MetricsTableBlock.objects.create(
        report=report, order=5, title="X / Twitter", network=Network.X,
    )
    MetricsTableRow.objects.bulk_create([
        MetricsTableRow(metrics_table_block=x, order=1,
                        metric_name="reach", value=Decimal("30000"),
                        source_type=SourceType.ORGANIC),
        MetricsTableRow(metrics_table_block=x, order=2,
                        metric_name="reach", value=Decimal("42000"),
                        source_type=SourceType.PAID),
        MetricsTableRow(metrics_table_block=x, order=3,
                        metric_name="reach", value=Decimal("170000"),
                        source_type=SourceType.INFLUENCER),
    ])

    # 6) Top Posts
    TopContentBlock.objects.create(
        report=report, order=6, title="Posts del mes", kind="POST", limit=6,
    )
    # 7) Top Creators
    TopContentBlock.objects.create(
        report=report, order=7, title="Creators del mes", kind="CREATOR", limit=6,
    )

    # 8) Attribution table
    AttributionTableBlock.objects.create(
        report=report, order=8, show_total=True,
    )

    # 9) Chart IG — line (DEV-128: follower growth es una curva temporal)
    ig_chart = ChartBlock.objects.create(
        report=report, order=9, title="Followers IG",
        network=Network.INSTAGRAM, chart_type="line",
    )
    ChartDataPoint.objects.bulk_create([
        ChartDataPoint(chart_block=ig_chart, order=i, label=label,
                       value=Decimal(str(value)))
        for i, (label, value) in enumerate(_IG_FOLLOWERS, start=1)
    ])

    # 10) Chart TikTok
    tk_chart = ChartBlock.objects.create(
        report=report, order=10, title="Followers TikTok",
        network=Network.TIKTOK, chart_type="bar",
    )
    ChartDataPoint.objects.bulk_create([
        ChartDataPoint(chart_block=tk_chart, order=i, label=label,
                       value=Decimal(str(value)))
        for i, (label, value) in enumerate(_TIKTOK_FOLLOWERS, start=1)
    ])

    # 11) Chart X
    x_chart = ChartBlock.objects.create(
        report=report, order=11, title="Followers X",
        network=Network.X, chart_type="bar",
    )
    ChartDataPoint.objects.bulk_create([
        ChartDataPoint(chart_block=x_chart, order=i, label=label,
                       value=Decimal(str(value)))
        for i, (label, value) in enumerate(_X_FOLLOWERS, start=1)
    ])


def _seed_minimal_layout(report) -> None:
    """Minimal typed blocks for published reports that don't get the full layout.

    Goal: ensure the viewer has *something* to render and the TopContent fixture
    pipeline has somewhere to attach its items. Keeps it simple: TOP_CONTENT
    (POST + CREATOR).
    """
    TopContentBlock.objects.create(
        report=report, order=1, title="Posts del mes", kind="POST", limit=6,
    )
    TopContentBlock.objects.create(
        report=report, order=2, title="Creators del mes", kind="CREATOR", limit=6,
    )
