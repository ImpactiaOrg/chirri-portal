"""Tenant scoping regression — un cliente no puede ver blocks de otro cliente.

Verifica el gotcha del repo documentado en CLAUDE.md: tenant scoping vive en
la view, no en middleware. Este test asegura que el refactor de DEV-116 no
rompió ese invariante.
"""
import pytest
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.reports.tests.factories import (
    make_brand,
    make_campaign,
    make_client,
    make_report,
    make_stage,
)


def _auth(api_client: APIClient, user) -> APIClient:
    token = RefreshToken.for_user(user).access_token
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
    return api_client


@pytest.mark.django_db
def test_blocks_scoped_by_client_via_report():
    from apps.reports.models import KpiGridBlock, ReportBlock

    # Setup: dos clientes con sus propios blocks
    client_a = make_client("Client A")
    brand_a = make_brand(client=client_a, name="Brand A")
    campaign_a = make_campaign(brand=brand_a, name="Campaign A")
    stage_a = make_stage(campaign=campaign_a, order=1, name="Stage A")
    report_a = make_report(stage=stage_a)
    KpiGridBlock.objects.create(report=report_a, order=1, title="KPIs A")

    client_b = make_client("Client B")
    brand_b = make_brand(client=client_b, name="Brand B")
    campaign_b = make_campaign(brand=brand_b, name="Campaign B")
    stage_b = make_stage(campaign=campaign_b, order=1, name="Stage B")
    report_b = make_report(stage=stage_b)
    KpiGridBlock.objects.create(report=report_b, order=1, title="KPIs B")

    # Query scoped by client_a → solo ve su block
    scoped_a = ReportBlock.objects.filter(
        report__stage__campaign__brand__client=client_a,
    )
    assert scoped_a.count() == 1
    # The filtered block resolves to its polymorphic subtype
    block = scoped_a.first()
    assert isinstance(block, KpiGridBlock)
    assert block.title == "KPIs A"


@pytest.mark.django_db
def test_api_endpoint_returns_404_for_other_tenant_report():
    """Smoke del endpoint real — user de client A no puede GET report de client B."""
    from django.contrib.auth import get_user_model

    from apps.reports.models import KpiGridBlock

    User = get_user_model()

    # Client A + user A + their report
    client_a = make_client("Client A")
    brand_a = make_brand(client=client_a, name="Brand A")
    campaign_a = make_campaign(brand=brand_a, name="Campaign A")
    stage_a = make_stage(campaign=campaign_a, order=1, name="Stage A")
    report_a = make_report(stage=stage_a)
    KpiGridBlock.objects.create(report=report_a, order=1, title="Grid A")
    user_a = User.objects.create_user(
        email="a@test.com",
        password="pw",
        client=client_a,
    )

    # Client B + their report
    client_b = make_client("Client B")
    brand_b = make_brand(client=client_b, name="Brand B")
    campaign_b = make_campaign(brand=brand_b, name="Campaign B")
    stage_b = make_stage(campaign=campaign_b, order=1, name="Stage B")
    report_b = make_report(stage=stage_b)

    api_client = _auth(APIClient(), user_a)

    # User A tries to access report_b → 404 (not 403, per repo scoping pattern)
    response = api_client.get(f"/api/reports/{report_b.id}/")
    assert response.status_code == 404, (
        f"Cross-tenant access should return 404; got {response.status_code}"
    )

    # User A accessing their own report → 200
    response = api_client.get(f"/api/reports/{report_a.id}/")
    assert response.status_code == 200
