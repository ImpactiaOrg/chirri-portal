"""Campaign detail endpoint: nested stages_with_reports.

The retrieve action returns the campaign plus its stages, each stage
carrying its list of PUBLISHED reports only. Drafts never leak.

Scoping mirrors DEV-52: cross-tenant → 404, not 403.
"""
from datetime import date, timedelta

import pytest
from django.utils import timezone

from apps.campaigns.models import Campaign, Stage
from apps.reports.models import Report


pytestmark = pytest.mark.django_db


class TestCampaignDetail:
    def _url(self, pk: int) -> str:
        return f"/api/campaigns/{pk}/"

    def test_returns_401_without_auth(self, api_client, balanz_campaign):
        res = api_client.get(self._url(balanz_campaign.pk))
        assert res.status_code == 401

    def test_returns_campaign_with_nested_stages_and_reports(
        self, authed_balanz, balanz_campaign
    ):
        stage = Stage.objects.create(
            campaign=balanz_campaign, order=1, name="Etapa 1", kind=Stage.Kind.AWARENESS
        )
        Report.objects.create(
            stage=stage,
            kind=Report.Kind.MENSUAL,
            period_start=date(2026, 3, 1),
            period_end=date(2026, 3, 31),
            title="Mensual marzo",
            status=Report.Status.PUBLISHED,
            published_at=timezone.now(),
        )
        res = authed_balanz.get(self._url(balanz_campaign.pk))
        assert res.status_code == 200
        assert res.data["id"] == balanz_campaign.pk
        assert res.data["brand_name"] == "Balanz"
        stages = res.data["stages_with_reports"]
        assert len(stages) == 1
        assert stages[0]["name"] == "Etapa 1"
        assert stages[0]["kind"] == "AWARENESS"
        assert len(stages[0]["reports"]) == 1
        assert stages[0]["reports"][0]["kind"] == "MENSUAL"

    def test_filters_draft_reports_from_stage(self, authed_balanz, balanz_campaign):
        stage = Stage.objects.create(
            campaign=balanz_campaign, order=1, name="Etapa 1", kind=Stage.Kind.AWARENESS
        )
        Report.objects.create(
            stage=stage,
            kind=Report.Kind.MENSUAL,
            period_start=date(2026, 3, 1),
            period_end=date(2026, 3, 31),
            status=Report.Status.DRAFT,
        )
        res = authed_balanz.get(self._url(balanz_campaign.pk))
        assert res.status_code == 200
        assert res.data["stages_with_reports"][0]["reports"] == []

    def test_cross_tenant_returns_404(self, authed_rival, balanz_campaign):
        res = authed_rival.get(self._url(balanz_campaign.pk))
        assert res.status_code == 404

    def test_unknown_id_returns_404(self, authed_balanz):
        res = authed_balanz.get(self._url(99999))
        assert res.status_code == 404

    def test_user_without_client_returns_404(
        self, api_client, balanz_campaign
    ):
        from apps.users.models import ClientUser
        from rest_framework_simplejwt.tokens import RefreshToken
        orphan = ClientUser.objects.create_user(
            email="orphan@nowhere.com", password="x", client=None
        )
        token = RefreshToken.for_user(orphan).access_token
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
        res = api_client.get(self._url(balanz_campaign.pk))
        assert res.status_code == 404

    def test_empty_stages_returns_empty_array(self, authed_balanz, balanz_campaign):
        res = authed_balanz.get(self._url(balanz_campaign.pk))
        assert res.status_code == 200
        assert res.data["stages_with_reports"] == []

    def test_stage_with_no_published_reports_has_empty_reports_array(
        self, authed_balanz, balanz_campaign
    ):
        Stage.objects.create(
            campaign=balanz_campaign, order=1, name="Etapa vacía", kind=Stage.Kind.OTHER
        )
        res = authed_balanz.get(self._url(balanz_campaign.pk))
        assert res.status_code == 200
        stages = res.data["stages_with_reports"]
        assert len(stages) == 1
        assert stages[0]["reports"] == []

    def test_detail_uses_constant_query_count(
        self, authed_balanz, balanz_campaign, django_assert_max_num_queries
    ):
        stage = Stage.objects.create(
            campaign=balanz_campaign, order=1, name="Etapa 1", kind=Stage.Kind.AWARENESS
        )
        for i in range(3):
            Report.objects.create(
                stage=stage,
                kind=Report.Kind.MENSUAL,
                period_start=date(2026, 1, 1) + timedelta(days=30 * i),
                period_end=date(2026, 1, 31) + timedelta(days=30 * i),
                status=Report.Status.PUBLISHED,
                published_at=timezone.now(),
            )
        with django_assert_max_num_queries(8):
            res = authed_balanz.get(self._url(balanz_campaign.pk))
        assert res.status_code == 200
        assert len(res.data["stages_with_reports"][0]["reports"]) == 3
