"""Seed demo data from the design handoff (Balanz · De Ahorrista a Inversor).

Idempotent: running multiple times updates existing rows rather than duplicating.
Usage:
    python manage.py seed_demo
    python manage.py seed_demo --wipe    # delete Balanz first, then reseed
"""
from datetime import date, datetime, timezone
from decimal import Decimal
from pathlib import Path

from django.core.files import File
from django.core.management.base import BaseCommand
from django.db import transaction

from apps.campaigns.models import Campaign, NarrativeLine, Stage
from apps.influencers.models import CampaignInfluencer, Influencer
from apps.reports.models import (
    BrandFollowerSnapshot,
    OneLinkAttribution,
    Report,
    ReportMetric,
    TopContent,
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
            # stage_slug, kind, period_start, period_end, title, status, published, conclusions, metrics
            ("awareness", Report.Kind.CIERRE_ETAPA, date(2026, 2, 1), date(2026, 2, 28),
             "Cierre de Awareness", Report.Status.PUBLISHED, pub(2026, 3, 5),
             "Plantamos la duda. El 'hay algo más que el plazo fijo' llegó.",
             [("INSTAGRAM", "ORGANIC", "reach", 920_000, Decimal("22"))]),
            ("awareness", Report.Kind.GENERAL, date(2026, 1, 1), date(2026, 1, 31),
             "Reporte general · Enero", Report.Status.PUBLISHED, pub(2026, 2, 2),
             "Primer mes de campaña. Baseline establecido.",
             [("INSTAGRAM", "ORGANIC", "reach", 480_000, None)]),

            ("educacion", Report.Kind.GENERAL, date(2026, 3, 1), date(2026, 3, 31),
             "Reporte general · Marzo", Report.Status.PUBLISHED, pub(2026, 4, 2),
             (
                 "Marzo fue el mes donde la campaña dejó de ser un experimento y "
                 "empezó a tener patrón. El carrusel de los 5 errores del ahorrista "
                 "se volvió el contenido más guardado del trimestre (8.2K saves)."
             ),
             [
                 ("INSTAGRAM", "ORGANIC", "reach", 284_000, Decimal("6.1")),
                 ("INSTAGRAM", "PAID", "reach", 512_000, None),
                 ("INSTAGRAM", "INFLUENCER", "reach", 1_640_000, Decimal("14.8")),
                 ("TIKTOK", "ORGANIC", "reach", 98_000, None),
                 ("TIKTOK", "PAID", "reach", 180_000, None),
                 ("TIKTOK", "INFLUENCER", "reach", 620_000, None),
                 ("X", "ORGANIC", "reach", 30_000, None),
                 ("X", "PAID", "reach", 42_000, None),
                 ("X", "INFLUENCER", "reach", 170_000, None),
                 ("INSTAGRAM", "ORGANIC", "engagement_rate", Decimal("4.8"), Decimal("0.3")),
                 ("INSTAGRAM", "ORGANIC", "followers_gained", 18_400, Decimal("24")),
             ]),
            ("educacion", Report.Kind.INFLUENCER, date(2026, 3, 1), date(2026, 3, 31),
             "Reporte de influencers · Marzo", Report.Status.PUBLISHED, pub(2026, 4, 2),
             "Marti Benza llevó la narrativa 'educación simple' al prime del mes.",
             [("INSTAGRAM", "INFLUENCER", "reach", 228_000, None)]),
            ("educacion", Report.Kind.GENERAL, date(2026, 2, 1), date(2026, 2, 28),
             "Reporte general · Febrero", Report.Status.PUBLISHED, pub(2026, 3, 3),
             "Crecimiento sostenido en guardados.",
             [("INSTAGRAM", "ORGANIC", "reach", 320_000, None)]),

            ("validacion", Report.Kind.GENERAL, date(2026, 3, 1), date(2026, 3, 31),
             "Reporte general · Marzo", Report.Status.PUBLISHED, pub(2026, 4, 2),
             "Sofi Gonet disparó el pico de downloads la noche del reel.",
             [
                 ("INSTAGRAM", "INFLUENCER", "reach", 2_430_000, Decimal("14.8")),
                 ("INSTAGRAM", "ORGANIC", "reach", 412_000, Decimal("6.1")),
             ]),
            ("validacion", Report.Kind.INFLUENCER, date(2026, 3, 1), date(2026, 3, 31),
             "Reporte de influencers · Marzo", Report.Status.PUBLISHED, pub(2026, 4, 2),
             "Testimonios personales — la narrativa más performante del trimestre.",
             [("INSTAGRAM", "INFLUENCER", "reach", 2_100_000, None)]),

            ("conversion", Report.Kind.GENERAL, date(2026, 4, 1), date(2026, 5, 31),
             "Plan de la etapa", Report.Status.DRAFT, None,
             "Borrador del plan de conversión. Llegada de Flor Sosa.",
             []),
        ]

        for stage_slug, kind, start, end, title, status, published, conclusions, metrics in report_specs:
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
            report.metrics.all().delete()
            for network, source_type, metric_name, value, delta in metrics:
                ReportMetric.objects.create(
                    report=report,
                    network=network,
                    source_type=source_type,
                    metric_name=metric_name,
                    value=Decimal(str(value)),
                    period_comparison=delta,
                )

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

            # Delete-then-create for idempotency (rerun must not duplicate).
            TopContent.objects.filter(report=report).delete()
            OneLinkAttribution.objects.filter(report=report).delete()

            for i, (handle, fname) in enumerate(top_content_specs, start=1):
                tc = TopContent(
                    report=report,
                    kind=TopContent.Kind.CREATOR if handle else TopContent.Kind.POST,
                    network=ReportMetric.Network.INSTAGRAM,
                    source_type=(
                        ReportMetric.SourceType.INFLUENCER if handle
                        else ReportMetric.SourceType.ORGANIC
                    ),
                    rank=i,
                    handle=handle,
                    caption=f"Contenido destacado #{i}",
                    metrics={"likes": 500 * i, "reach": 10000 * i, "er": 3.5 + i * 0.4},
                )
                with open(fixtures / fname, "rb") as fh:
                    tc.thumbnail.save(fname, File(fh), save=False)
                tc.save()

            for handle, clicks, downloads in onelink_specs:
                OneLinkAttribution.objects.create(
                    report=report,
                    influencer_handle=handle,
                    clicks=clicks,
                    app_downloads=downloads,
                )

        # Brand-level snapshots: one per month, keyed by (brand, network, as_of).
        for month, count in [(1, 99_500), (2, 104_568), (3, 107_072)]:
            BrandFollowerSnapshot.objects.update_or_create(
                brand=brand,
                network=ReportMetric.Network.INSTAGRAM,
                as_of=date(latest.period_start.year, month, 28),
                defaults={"followers_count": count},
            )
