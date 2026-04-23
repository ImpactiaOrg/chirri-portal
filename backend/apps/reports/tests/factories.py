"""Test factories para DEV-116. Factories minimalistas (sin factory_boy
para no agregar deps — helpers funcionales alcanzan).

Brand vive en apps.tenants.models (no en apps.campaigns.models), cuidado
con el import.
"""
from datetime import date, datetime, timezone

from apps.campaigns.models import Campaign, Stage
from apps.reports.models import Report
from apps.tenants.models import Brand, Client


def make_client(name="Test Client"):
    return Client.objects.create(name=name)


def make_brand(client=None, name="Test Brand"):
    if client is None:
        client = make_client()
    return Brand.objects.create(client=client, name=name)


def make_campaign(brand=None, name="Test Campaign"):
    if brand is None:
        brand = make_brand()
    return Campaign.objects.create(
        brand=brand,
        name=name,
        status=Campaign.Status.ACTIVE,
        start_date=date(2026, 1, 1),
    )


def make_stage(campaign=None, order=1, name="Test Stage"):
    if campaign is None:
        campaign = make_campaign()
    return Stage.objects.create(
        campaign=campaign,
        order=order,
        name=name,
        kind=Stage.Kind.AWARENESS,
    )


def make_report(stage=None, kind=Report.Kind.GENERAL):
    if stage is None:
        stage = make_stage()
    return Report.objects.create(
        stage=stage,
        kind=kind,
        period_start=date(2026, 3, 1),
        period_end=date(2026, 3, 31),
        title="Test Report",
        status=Report.Status.PUBLISHED,
        published_at=datetime(2026, 4, 2, 12, 0, tzinfo=timezone.utc),
    )
