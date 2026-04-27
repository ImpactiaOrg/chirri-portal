"""Seed demo data — fictional client "Aurora Foods" with full sample report set.

Idempotent: running multiple times updates existing rows rather than duplicating.
Usage:
    python manage.py seed_demo
    python manage.py seed_demo --wipe    # delete demo client first, then reseed

Post-DEV-116: usa blocks tipados (KpiGridBlock, TableBlock, TopContentBlock,
ChartBlock). ReportMetric fue eliminado. MetricsTableBlock y AttributionTableBlock
reemplazados por TableBlock (DEV-Task 7).
"""
import random
import shutil
from datetime import date, datetime, timezone
from decimal import Decimal
from pathlib import Path

from django.conf import settings
from django.core.files import File
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from django.db import transaction

from apps.campaigns.models import Campaign, Stage
from apps.reports.choices import Network, SourceType
from apps.reports.models import (
    BrandFollowerSnapshot,
    ChartBlock,
    ChartDataPoint,
    ImageBlock,
    KpiGridBlock,
    KpiTile,
    Report,
    ReportAttachment,
    TableBlock,
    TableRow,
    TextImageBlock,
    TopContentsBlock,
    TopContentItem,
    TopCreatorsBlock,
    TopCreatorItem,
)
from apps.tenants.models import Brand, Client
from apps.users.models import ClientUser

DEMO_CLIENT_NAME = "Aurora Foods"
DEMO_BRAND_NAME = "Aurora"
DEMO_USER_EMAIL = "demo@chirripeppers.com"
DEMO_USER_NAME = "Usuario Demo"
DEMO_PASSWORD = "demo2026"

# Superadmins globales (sin client). Idempotente: si el usuario ya existe en
# la DB con password seteada, no se la pisamos — solo se crea si falta.
SUPERADMINS = [
    ("daniel@impactia.ai", "Daniel Zacharias"),
    ("eugenio@impactia.ai", "Eugenio de Tomaso"),
    ("vicky@chirripeppers.com", "Victoria de Tomaso"),
    ("julian@chirripeppers.com", "Julián Montero Ciancio"),
]

DEMO_PRIMARY_COLOR = "#E85A2C"   # terracotta — neutro y cálido
DEMO_ACCENT_COLOR = "#F4C95D"    # mostaza

_FIXTURES_DIR = Path(__file__).parent / "fixtures"
_IMAGE_POOL_DIR = _FIXTURES_DIR / "images_pool"
_IMG_EXTS = {".jpg", ".jpeg", ".png", ".webp"}
_FALLBACK_IMAGES = [
    "placeholder_post_1.jpg",
    "placeholder_post_2.jpg",
    "placeholder_creator_1.jpg",
]
# Subpaths debajo de MEDIA_ROOT que el seed regenera en cada run. Se borran
# al inicio para que re-ejecutar no acumule archivos con sufijo random de
# FileSystemStorage.get_available_name (top_content llegó a tener 4500+).
_SEED_MEDIA_SUBPATHS = (
    "top_content", "top_creators", "report_blocks", "image_blocks",
    "reports/attachments",
)


def _pick_image(kind: str) -> Path:
    """Elige aleatoriamente una imagen de `images_pool/{kind}/`.

    kind="post" → feed/lifestyle/contenido (TopContent POST + intro TextImage).
    kind="creator" → retrato para TopContent CREATOR.

    Si la subcarpeta está vacía o no existe, cae a los placeholders históricos
    — así el seed sigue funcionando incluso sin poblar el pool.
    """
    pool = _IMAGE_POOL_DIR / kind
    if pool.is_dir():
        candidates = [
            p for p in pool.iterdir()
            if p.is_file() and p.suffix.lower() in _IMG_EXTS
        ]
        if candidates:
            return random.choice(candidates)
    return _FIXTURES_DIR / random.choice(_FALLBACK_IMAGES)


def _wipe_seed_media() -> None:
    """Borra subpaths de MEDIA_ROOT que el seed regenera, solo en
    FileSystemStorage. Con R2/S3 no tocamos nada: el bucket es compartido y
    un rmtree remoto sería destructivo.
    """
    backend = settings.STORAGES.get("default", {}).get("BACKEND", "")
    if "FileSystemStorage" not in backend:
        return
    media_root = Path(settings.MEDIA_ROOT)
    for sub in _SEED_MEDIA_SUBPATHS:
        target = media_root / sub
        if target.exists():
            shutil.rmtree(target, ignore_errors=True)


class Command(BaseCommand):
    help = "Seed demo data — fictional Aurora Foods client."

    def add_arguments(self, parser):
        parser.add_argument("--wipe", action="store_true", help="Delete demo client data before seeding.")

    @transaction.atomic
    def handle(self, *args, wipe: bool = False, **options):
        if wipe:
            self.stdout.write(f"Wiping existing {DEMO_CLIENT_NAME} data…")
            Client.objects.filter(name=DEMO_CLIENT_NAME).delete()

        _wipe_seed_media()

        client = self._seed_client()
        brand = self._seed_brand(client)
        self._seed_user(client)
        admins_created = self._seed_superadmins()
        campaigns = self._seed_campaigns(brand)
        stages = self._seed_stages(campaigns["ahorrista-inversor"])
        self._seed_reports(stages)
        self._seed_report_viewer_fixtures(brand)

        self.stdout.write(self.style.SUCCESS("\n✓ Demo data loaded."))
        self.stdout.write(f"  Client: {client.name}")
        self.stdout.write(f"  Brand: {brand.name}")
        self.stdout.write(f"  Campaigns: {len(campaigns)} (1 active + 2 finished)")
        self.stdout.write(f"  Stages (active campaign): {len(stages)}")
        self.stdout.write("\n  Login portal:")
        self.stdout.write(self.style.WARNING(f"    email:    {DEMO_USER_EMAIL}"))
        self.stdout.write(self.style.WARNING(f"    password: {DEMO_PASSWORD}"))
        if admins_created:
            self.stdout.write(f"\n  Superadmins creados con password '{DEMO_PASSWORD}': {', '.join(admins_created)}")
        self.stdout.write(self.style.SUCCESS(
            f"  Total superadmins: {len(SUPERADMINS)} (passwords pre-existentes preservadas)"
        ))

    def _seed_client(self) -> Client:
        client, _ = Client.objects.update_or_create(
            name=DEMO_CLIENT_NAME,
            defaults={
                "logo_url": "",
                "primary_color": DEMO_PRIMARY_COLOR,
                "secondary_color": DEMO_ACCENT_COLOR,
            },
        )
        return client

    def _seed_brand(self, client: Client) -> Brand:
        brand, _ = Brand.objects.update_or_create(
            client=client,
            name=DEMO_BRAND_NAME,
            defaults={"description": f"{DEMO_BRAND_NAME} · marca demo para mostrar el portal."},
        )
        return brand

    def _seed_user(self, client: Client) -> ClientUser:
        user, created = ClientUser.objects.get_or_create(
            email=DEMO_USER_EMAIL,
            defaults={
                "full_name": DEMO_USER_NAME,
                "client": client,
                "role": ClientUser.Role.ADMIN_CLIENT,
                "is_active": True,
            },
        )
        if created or not user.has_usable_password():
            user.set_password(DEMO_PASSWORD)
            user.save()
        return user

    def _seed_superadmins(self) -> list[str]:
        """Crea/asegura los 4 superadmins globales del equipo (sin client).

        Idempotente. Si el user ya existe (p.ej. lo creaste a mano en Hetzner
        antes), NO toca el password ni los datos — solo garantiza que tenga
        is_superuser/is_staff y client=None.

        Devuelve la lista de emails que se crearon nuevos en este run.
        """
        created_emails: list[str] = []
        for email, full_name in SUPERADMINS:
            user, created = ClientUser.objects.get_or_create(
                email=email,
                defaults={
                    "full_name": full_name,
                    "client": None,
                    "role": ClientUser.Role.ADMIN_CLIENT,
                    "is_active": True,
                    "is_staff": True,
                    "is_superuser": True,
                },
            )
            if created:
                user.set_password(DEMO_PASSWORD)
                user.save()
                created_emails.append(email)
            elif not (user.is_staff and user.is_superuser and user.client_id is None):
                # User pre-existente sin flags de superadmin → upgrade in-place,
                # sin tocar password.
                user.is_staff = True
                user.is_superuser = True
                user.client = None
                user.save(update_fields=["is_staff", "is_superuser", "client"])
        return created_emails

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

            # Kitchen-sink: usa TODOS los block types (TextImage + KpiGrid +
            # MetricsTable + TopContent + Attribution + Chart bar+line).
            # Sirve de fixture visual para QA del viewer de reportes.
            ("conversion", Report.Kind.GENERAL, date(2026, 4, 1), date(2026, 4, 30),
             "Reporte general · Abril", Report.Status.PUBLISHED, pub(2026, 5, 2),
             (
                 "Abril arrancó la etapa de conversión. Flor Sosa debutó con el "
                 "reel 'lo saqué del colchón' y disparó un pico de downloads "
                 "sostenido. El mes cerró con el mejor ratio click→download de "
                 "la campaña y la cohorte de usuarios nuevos duplicó a la de "
                 "marzo."
             )),
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

            if title == "Reporte general · Abril":
                _seed_all_blocks_layout(report)
            elif (
                kind == Report.Kind.GENERAL
                and stage.kind in {Stage.Kind.EDUCATION, Stage.Kind.VALIDATION}
                and start.month == 3
            ):
                _seed_full_layout(report)
            elif status == Report.Status.PUBLISHED:
                _seed_minimal_layout(report)

            # Descargable mínimo: todo reporte publicado viene con un PDF
            # dummy (placeholder hasta que subamos el real desde admin).
            if status == Report.Status.PUBLISHED:
                _seed_pdf_attachment(report)

    def _seed_report_viewer_fixtures(self, brand: Brand) -> None:
        """Populate the Report Viewer fixtures (TopContent, OneLink, FollowerSnapshots).

        Applies to every published report tied at the latest period_start so the
        viewer has renderable data regardless of tie-breaking. Idempotent via
        delete-then-create for per-report fixtures and update_or_create for
        brand-level snapshots.
        """
        # Poblar fixtures (TopContent, OneLink) en TODO reporte publicado.
        # Antes filtrábamos a la última period_start, pero eso dejaba a los
        # reportes Marzo sin datos en cuanto aparecía un reporte Abril, y
        # el smoke E2E navega al Marzo Educación esperando POSTS DEL MES.
        # El inner loop ya hace `if block is None: continue` para reportes
        # cuyo layout no incluya el block correspondiente.
        target_reports = Report.objects.filter(status=Report.Status.PUBLISHED)
        if not target_reports.exists():
            return

        intro = (
            "Cerramos un mes con crecimiento sostenido en alcance orgánico y un pico "
            "de downloads vía influencers. Acá va el detalle."
        )

        # Posts destacados (5 items, todos con la métrica "guardados").
        # Captions inspirados en reportes reales (Ken Brown).
        content_item_specs = [
            {
                "caption": "La web cam ideal para tu set up!",
                "source_type": SourceType.PAID,
                "views": 34_500, "likes": 6, "comments": 0, "shares": 1, "saves": 1,
            },
            {
                "caption": "Infaltables para volver a la oficina",
                "source_type": SourceType.INFLUENCER,
                "views": 621, "likes": 6, "comments": 0, "shares": 0, "saves": 1,
            },
            {
                "caption": "POV: Dejaste la incomodidad atrás",
                "source_type": SourceType.ORGANIC,
                "views": 26_900, "likes": 6, "comments": 0, "shares": 1, "saves": 2,
            },
            {
                "caption": "POV: Tenés unos auriculares super versátiles",
                "source_type": SourceType.INFLUENCER,
                "views": 20_600, "likes": 6, "comments": 0, "shares": 0, "saves": 1,
            },
            {
                "caption": "",
                "source_type": SourceType.ORGANIC,
                "views": 353, "likes": 8, "comments": 0, "shares": 0, "saves": 1,
            },
        ]
        # Creadores destacados (3 items, sin saves).
        creator_item_specs = [
            {
                "handle": "@antoroncatti",
                "views": 8_849, "likes": None, "comments": 15, "shares": 2,
            },
            {
                "handle": "@florsosa.ok",
                "views": 4_210, "likes": 52, "comments": 9, "shares": 3,
            },
            {
                "handle": "@pasaje.en.mano",
                "views": 2_180, "likes": 34, "comments": 6, "shares": 1,
            },
        ]
        onelink_specs = [
            ("@pasaje.en.mano", 1200, 180),
            ("@financierapopular", 800, 95),
            ("@pymes_ar", 400, 30),
        ]

        for report in target_reports:
            report.intro_text = intro
            report.save(update_fields=["intro_text"])

            contents_block = TopContentsBlock.objects.filter(report=report).first()
            creators_block = TopCreatorsBlock.objects.filter(report=report).first()
            onelink_block = TableBlock.objects.filter(
                report=report, title="Atribución OneLink",
            ).first()

            # Delete-then-create for idempotency (rerun must not duplicate).
            if contents_block is not None:
                TopContentItem.objects.filter(block=contents_block).delete()
            if creators_block is not None:
                TopCreatorItem.objects.filter(block=creators_block).delete()
            if onelink_block is not None:
                onelink_block.rows.all().delete()

            if contents_block is not None:
                for i, spec in enumerate(content_item_specs, start=1):
                    item = TopContentItem(
                        block=contents_block,
                        order=i,
                        caption=spec["caption"],
                        source_type=spec["source_type"],
                        views=spec["views"],
                        likes=spec["likes"],
                        comments=spec["comments"],
                        shares=spec["shares"],
                        saves=spec["saves"],
                    )
                    source = _pick_image("post")
                    stable_name = f"topcontent-{contents_block.id}-{i}{source.suffix}"
                    with open(source, "rb") as fh:
                        item.thumbnail.save(stable_name, File(fh), save=False)
                    item.save()

            if creators_block is not None:
                for i, spec in enumerate(creator_item_specs, start=1):
                    item = TopCreatorItem(
                        block=creators_block,
                        order=i,
                        handle=spec["handle"],
                        views=spec["views"],
                        likes=spec["likes"],
                        comments=spec["comments"],
                        shares=spec["shares"],
                    )
                    source = _pick_image("creator")
                    stable_name = f"topcreator-{creators_block.id}-{i}{source.suffix}"
                    with open(source, "rb") as fh:
                        item.thumbnail.save(stable_name, File(fh), save=False)
                    item.save()

            if onelink_block is not None:
                TableRow.objects.bulk_create([
                    TableRow(table_block=onelink_block, order=1, is_header=True,
                             cells=["Influencer", "Clicks", "Descargas"]),
                    *[
                        TableRow(
                            table_block=onelink_block,
                            order=i + 2,
                            cells=[handle, str(clicks), str(downloads)],
                        )
                        for i, (handle, clicks, downloads) in enumerate(onelink_specs)
                    ],
                ])

        # Brand-level snapshots: one per month, keyed by (brand, network, as_of).
        snapshot_year = target_reports.order_by("-period_start").first().period_start.year
        for month, count in [(1, 99_500), (2, 104_568), (3, 107_072), (4, 110_240)]:
            BrandFollowerSnapshot.objects.update_or_create(
                brand=brand,
                network=Network.INSTAGRAM,
                as_of=date(snapshot_year, month, 28),
                defaults={"followers_count": count},
            )


# ---------------------------------------------------------------------------
# Layout seeders — typed blocks (DEV-116)
# ---------------------------------------------------------------------------

# Follower counts per month (used by follower charts; mirrors BrandFollowerSnapshot).
_IG_FOLLOWERS = [("Enero", 99_500), ("Febrero", 104_568), ("Marzo", 107_072)]
_TIKTOK_FOLLOWERS = [("Enero", 42_000), ("Febrero", 48_300), ("Marzo", 54_100)]
_X_FOLLOWERS = [("Enero", 18_200), ("Febrero", 19_400), ("Marzo", 20_850)]


_PDF_DUMMY = (
    b"%PDF-1.4\n"
    b"1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
    b"2 0 obj<</Type/Pages/Count 0/Kids[]>>endobj\n"
    b"xref\n0 3\n0000000000 65535 f \n"
    b"0000000009 00000 n \n0000000052 00000 n \n"
    b"trailer<</Size 3/Root 1 0 R>>startxref\n98\n%%EOF\n"
)


def _seed_pdf_attachment(report) -> None:
    """Adjunta un PDF dummy al reporte (idempotente: borra los existentes
    y recrea). El contenido es un PDF 1.4 mínimo válido — suficiente para
    que el browser lo sirva como application/pdf.
    """
    report.attachments.all().delete()
    period = report.period_start.strftime("%Y-%m")
    file_name = f"reporte-{report.id}-{period}.pdf"
    attachment = ReportAttachment(
        report=report,
        order=0,
        title="Reporte (PDF)",
        kind=ReportAttachment.Kind.PDF_REPORT,
    )
    attachment.file.save(file_name, ContentFile(_PDF_DUMMY), save=False)
    attachment.save()


def _seed_full_layout(report) -> None:
    """11 typed blocks for the rich monthly General report (Educación/Validación Marzo).

    Layout (order 1..11):
      1 KpiGridBlock — "KPIs del mes" (3 tiles)
      2 TableBlock   — "Mes a mes" (cross-network, delta vs prev month)
      3 TableBlock   — "Instagram" (reach por source_type)
      4 TableBlock   — "TikTok"    (reach por source_type)
      5 TableBlock   — "X / Twitter" (reach por source_type)
      6 TopContentsBlock — "Posts del mes"   (kind=POST)
      7 TopCreatorsBlock — "Creators del mes" (kind=CREATOR)
      8 TableBlock   — "Atribución OneLink" (show_total=True)
      9 ChartBlock   — "Followers IG"      (line, data puntos mensuales)
     10 ChartBlock   — "Followers TikTok"  (bar)
     11 ChartBlock   — "Followers X"       (bar)
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
                period_comparison=Decimal("6.1"),
                period_comparison_label="vs feb"),
        KpiTile(kpi_grid_block=kpi_grid, order=3,
                label="Reach influencer", value=Decimal("2430000"),
                period_comparison=Decimal("14.8"),
                period_comparison_label="vs feb"),
    ])

    # 2) Mes a mes — cross-network (network=null)
    mtm = TableBlock.objects.create(
        report=report, order=2, title="Mes a mes",
    )
    TableRow.objects.bulk_create([
        TableRow(table_block=mtm, order=1, is_header=True,
                 cells=["Métrica", "Valor", "Δ"]),
        TableRow(table_block=mtm, order=2,
                 cells=["ORGANIC · engagement_rate", "4.8", "+0.3%"]),
        TableRow(table_block=mtm, order=3,
                 cells=["ORGANIC · followers_gained", "18400", "+24%"]),
    ])

    # 3) Instagram — reach per source_type
    ig = TableBlock.objects.create(
        report=report, order=3, title="Instagram",
    )
    TableRow.objects.bulk_create([
        TableRow(table_block=ig, order=1, is_header=True,
                 cells=["Métrica", "Valor", "Δ"]),
        TableRow(table_block=ig, order=2,
                 cells=["ORGANIC · reach", "284000", "+6.1%"]),
        TableRow(table_block=ig, order=3,
                 cells=["PAID · reach", "512000", ""]),
        TableRow(table_block=ig, order=4,
                 cells=["INFLUENCER · reach", "1640000", "+14.8%"]),
    ])

    # 4) TikTok
    tk = TableBlock.objects.create(
        report=report, order=4, title="TikTok",
    )
    TableRow.objects.bulk_create([
        TableRow(table_block=tk, order=1, is_header=True,
                 cells=["Métrica", "Valor", "Δ"]),
        TableRow(table_block=tk, order=2,
                 cells=["ORGANIC · reach", "98000", ""]),
        TableRow(table_block=tk, order=3,
                 cells=["PAID · reach", "180000", ""]),
        TableRow(table_block=tk, order=4,
                 cells=["INFLUENCER · reach", "620000", ""]),
    ])

    # 5) X / Twitter
    x = TableBlock.objects.create(
        report=report, order=5, title="X / Twitter",
    )
    TableRow.objects.bulk_create([
        TableRow(table_block=x, order=1, is_header=True,
                 cells=["Métrica", "Valor", "Δ"]),
        TableRow(table_block=x, order=2,
                 cells=["ORGANIC · reach", "30000", ""]),
        TableRow(table_block=x, order=3,
                 cells=["PAID · reach", "42000", ""]),
        TableRow(table_block=x, order=4,
                 cells=["INFLUENCER · reach", "170000", ""]),
    ])

    # 6) Top Contenidos
    TopContentsBlock.objects.create(
        report=report, order=6, title="Posts del mes",
        network=Network.INSTAGRAM, limit=6,
    )
    # 7) Top Creadores
    TopCreatorsBlock.objects.create(
        report=report, order=7, title="Creators del mes",
        network=Network.INSTAGRAM, limit=6,
    )

    # 8) Attribution table
    TableBlock.objects.create(
        report=report, order=8, title="Atribución OneLink", show_total=True,
    )

    # 9) Chart IG — line (DEV-128: follower growth es una curva temporal)
    ig_chart = ChartBlock.objects.create(
        report=report, order=9, title="Followers",
        description="Cuántas personas nos siguen al cierre de cada mes.",
        network=Network.INSTAGRAM, chart_type="line",
    )
    ChartDataPoint.objects.bulk_create([
        ChartDataPoint(chart_block=ig_chart, order=i, label=label,
                       value=Decimal(str(value)))
        for i, (label, value) in enumerate(_IG_FOLLOWERS, start=1)
    ])

    # 10) Chart TikTok
    tk_chart = ChartBlock.objects.create(
        report=report, order=10, title="Followers",
        description="Cuántas personas nos siguen al cierre de cada mes.",
        network=Network.TIKTOK, chart_type="bar",
    )
    ChartDataPoint.objects.bulk_create([
        ChartDataPoint(chart_block=tk_chart, order=i, label=label,
                       value=Decimal(str(value)))
        for i, (label, value) in enumerate(_TIKTOK_FOLLOWERS, start=1)
    ])

    # 11) Chart X
    x_chart = ChartBlock.objects.create(
        report=report, order=11, title="Followers",
        description="Cuántas personas nos siguen al cierre de cada mes.",
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
    TopContentsBlock.objects.create(
        report=report, order=1, title="Posts del mes",
        network=Network.INSTAGRAM, limit=6,
    )
    TopCreatorsBlock.objects.create(
        report=report, order=2, title="Creators del mes",
        network=Network.INSTAGRAM, limit=6,
    )


# Follower trend para el reporte Abril (incluye 4 meses de historia).
_IG_FOLLOWERS_APRIL = [
    ("Enero", 99_500), ("Febrero", 104_568),
    ("Marzo", 107_072), ("Abril", 110_240),
]
_ENGAGEMENT_RATE_APRIL = [
    ("Enero", Decimal("3.9")), ("Febrero", Decimal("4.2")),
    ("Marzo", Decimal("4.8")), ("Abril", Decimal("5.3")),
]


def _seed_all_blocks_layout(report) -> None:
    """Kitchen-sink layout: usa los 8 subtipos de ReportBlock.

    Pensado como fixture visual para QA del viewer de reportes — permite
    ver en una sola página cómo se renderiza cada block type con data real.
    Variantes incluidas:
      · TextImageBlock (con imagen, position=left) y (solo texto, 2 columnas)
      · ImageBlock (hero con overlay)
      · KpiGridBlock con 4 tiles (con y sin delta)
      · TableBlock cross-network y por-red (Instagram)
      · TopContentsBlock + TopCreatorsBlock (DEV-129)
      · TableBlock con show_total (atribución OneLink)
      · ChartBlock bar (followers IG) y line (engagement rate)
    """
    # 1) TextImageBlock — intro narrativa con imagen
    intro_img = TextImageBlock(
        report=report, order=1,
        title="Contexto del mes",
        body=(
            "Abril fue la primera bajada real del mensaje de conversión. "
            "Flor Sosa entró con un reel testimonial que marcó la agenda "
            "del mes y el resto de la comunidad orgánica lo amplificó con "
            "comentarios propios.\n\n"
            "La conversión medida por OneLink creció 32% mes a mes y la "
            "app sumó 310 descargas atribuidas directamente a la campaña."
        ),
        columns=1,
        image_position="left",
        image_alt="Creator Flor Sosa grabando el reel de abril",
    )
    source = _pick_image("post")
    with open(source, "rb") as fh:
        intro_img.image.save(f"intro-{report.id}{source.suffix}", File(fh), save=False)
    intro_img.save()

    # 2) KpiGridBlock — 4 tiles
    kpi_grid = KpiGridBlock.objects.create(
        report=report, order=2, title="KPIs del mes",
    )
    KpiTile.objects.bulk_create([
        KpiTile(kpi_grid_block=kpi_grid, order=1,
                label="Reach total", value=Decimal("3120000"),
                period_comparison=Decimal("9.9"),
                period_comparison_label="vs mar"),
        KpiTile(kpi_grid_block=kpi_grid, order=2,
                label="Engagement rate", value=Decimal("5.3"), unit="%",
                period_comparison=Decimal("0.5"),
                period_comparison_label="vs mar"),
        KpiTile(kpi_grid_block=kpi_grid, order=3,
                label="App downloads", value=Decimal("310")),
        KpiTile(kpi_grid_block=kpi_grid, order=4,
                label="Click→download", value=Decimal("12.8"), unit="%",
                period_comparison=Decimal("3.1"),
                period_comparison_label="vs mar"),
    ])

    # 3) TableBlock — cross-network (Mes a mes)
    mtm = TableBlock.objects.create(
        report=report, order=3, title="Mes a mes",
    )
    TableRow.objects.bulk_create([
        TableRow(table_block=mtm, order=1, is_header=True,
                 cells=["Métrica", "Valor", "Δ"]),
        TableRow(table_block=mtm, order=2,
                 cells=["ORGANIC · engagement_rate", "5.3", "+0.5%"]),
        TableRow(table_block=mtm, order=3,
                 cells=["ORGANIC · followers_gained", "21300", "+15.7%"]),
        TableRow(table_block=mtm, order=4,
                 cells=["INFLUENCER · app_downloads", "310", "+32%"]),
    ])

    # 4) TableBlock — Instagram
    ig = TableBlock.objects.create(
        report=report, order=4, title="Instagram",
    )
    TableRow.objects.bulk_create([
        TableRow(table_block=ig, order=1, is_header=True,
                 cells=["Métrica", "Valor", "Δ"]),
        TableRow(table_block=ig, order=2,
                 cells=["ORGANIC · reach", "312000", "+9.9%"]),
        TableRow(table_block=ig, order=3,
                 cells=["PAID · reach", "594000", "+16.0%"]),
        TableRow(table_block=ig, order=4,
                 cells=["INFLUENCER · reach", "1810000", "+10.4%"]),
    ])

    # 5) TopContentsBlock — Posts
    TopContentsBlock.objects.create(
        report=report, order=5, title="Posts del mes",
        network=Network.INSTAGRAM, limit=6,
    )
    # 6) TopCreatorsBlock — Creators
    TopCreatorsBlock.objects.create(
        report=report, order=6, title="Creators del mes",
        network=Network.INSTAGRAM, limit=6,
    )

    # 7) Attribution table
    TableBlock.objects.create(
        report=report, order=7, title="Atribución OneLink", show_total=True,
    )

    # 8) ChartBlock bar — Followers IG
    ig_chart = ChartBlock.objects.create(
        report=report, order=8, title="Followers",
        description="Cuántas personas nos siguen al cierre de cada mes.",
        network=Network.INSTAGRAM, chart_type="bar",
    )
    ChartDataPoint.objects.bulk_create([
        ChartDataPoint(chart_block=ig_chart, order=i, label=label,
                       value=Decimal(str(value)))
        for i, (label, value) in enumerate(_IG_FOLLOWERS_APRIL, start=1)
    ])

    # 9) ChartBlock line — Engagement rate evolution
    er_chart = ChartBlock.objects.create(
        report=report, order=9, title="Engagement rate",
        description="Evolución mensual del engagement rate de la marca.",
        network=None, chart_type="line",
    )
    ChartDataPoint.objects.bulk_create([
        ChartDataPoint(chart_block=er_chart, order=i, label=label, value=value)
        for i, (label, value) in enumerate(_ENGAGEMENT_RATE_APRIL, start=1)
    ])

    # 10) ImageBlock — hero visual antes del cierre textual
    hero = ImageBlock(
        report=report, order=10,
        title="El mes en fotos",
        caption="Momentos destacados del contenido publicado.",
        image_alt="Collage visual del mes",
    )
    source = _pick_image("post")
    with open(source, "rb") as fh:
        hero.image.save(f"hero-{report.id}{source.suffix}", File(fh), save=False)
    hero.save()

    # 11) TextImageBlock — cierre solo texto, multicol
    TextImageBlock.objects.create(
        report=report, order=11,
        title="Qué probamos para mayo",
        body=(
            "Seguimos apostando al formato reel testimonial — los saves "
            "duplicaron a los carruseles educativos del mes anterior. "
            "Vamos a sumar un creator asesor para reforzar la narrativa "
            "'rol del asesor' y cerrar el embudo antes de la pauta final. "
            "El ratio click→download de abril (12.8%) es el piso para mayo "
            "— si cae habrá que revisar creativos antes que audiencias."
        ),
        columns=2,
        image_position="top",
    )
