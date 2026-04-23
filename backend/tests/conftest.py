"""Shared fixtures: tenants, users, auth'd API clients, and a Balanz sample.

The fixtures are intentionally small — each test builds only what it needs via
these helpers. For richer scenarios, tests can still call `seed_demo` directly.
"""
from __future__ import annotations

from datetime import date, timedelta

import pytest
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.campaigns.models import Campaign, Stage
from apps.reports.models import Report, ReportMetric
from apps.reports.tests.factories import make_report
from apps.tenants.models import Brand, Client
from apps.users.models import ClientUser


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def balanz():
    return Client.objects.create(name="Balanz", primary_color="#0B2D5B")


@pytest.fixture
def rival():
    """A second tenant used to prove tenant isolation."""
    return Client.objects.create(name="Rival Corp")


@pytest.fixture
def balanz_brand(balanz):
    return Brand.objects.create(client=balanz, name="Balanz")


@pytest.fixture
def rival_brand(rival):
    return Brand.objects.create(client=rival, name="Rival")


@pytest.fixture
def balanz_user(balanz):
    return ClientUser.objects.create_user(
        email="belen@balanz.com",
        password="balanz2026",
        full_name="Belén Rizzo",
        client=balanz,
        role=ClientUser.Role.ADMIN_CLIENT,
    )


@pytest.fixture
def rival_user(rival):
    return ClientUser.objects.create_user(
        email="alice@rival.com",
        password="rival2026",
        client=rival,
    )


def _auth(client: APIClient, user: ClientUser) -> APIClient:
    token = RefreshToken.for_user(user).access_token
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
    return client


@pytest.fixture
def authed_balanz(api_client, balanz_user):
    return _auth(api_client, balanz_user)


@pytest.fixture
def authed_rival(rival_user):
    return _auth(APIClient(), rival_user)


@pytest.fixture
def balanz_campaign(balanz_brand):
    return Campaign.objects.create(
        brand=balanz_brand,
        name="De Ahorrista a Inversor",
        brief="Campaña de educación financiera.",
        status=Campaign.Status.ACTIVE,
    )


@pytest.fixture
def balanz_stage(balanz_campaign):
    return Stage.objects.create(
        campaign=balanz_campaign,
        order=1,
        name="Validación",
        kind=Stage.Kind.VALIDATION,
    )


@pytest.fixture
def balanz_published_report(balanz_stage):
    r = Report.objects.create(
        stage=balanz_stage,
        kind=Report.Kind.MENSUAL,
        period_start=date.today().replace(day=1) - timedelta(days=30),
        period_end=date.today().replace(day=1) - timedelta(days=1),
        title="Reporte mensual de prueba",
        status=Report.Status.PUBLISHED,
        published_at=timezone.now(),
        conclusions_text="Cerramos bien.",
    )
    ReportMetric.objects.create(
        report=r,
        network=ReportMetric.Network.INSTAGRAM,
        source_type=ReportMetric.SourceType.ORGANIC,
        metric_name="reach",
        value=123456,
    )
    return r


@pytest.fixture
def report_factory(db):
    """Fixture: callable que crea un Report nuevo cada vez (DEV-116)."""
    return make_report
