"""Campaigns list is auth-gated and tenant-scoped.

Regression: the ViewSet used to scope by `request.client` set by a Django
middleware that runs *before* DRF authentication — so `request.client` was
always None and the list came back empty for every logged-in user. The fix
resolves the tenant via `request.user.client_id` instead, and these tests
lock that behavior in.
"""
from datetime import date, timedelta

import pytest
from django.utils import timezone

from apps.campaigns.models import Campaign, Stage
from apps.reports.models import Report


@pytest.mark.django_db
class TestCampaignsList:
    url = "/api/campaigns/"

    def test_anonymous_is_401(self, api_client):
        response = api_client.get(self.url)
        assert response.status_code == 401

    def test_returns_only_own_tenant_campaigns(
        self, authed_balanz, balanz_brand, rival_brand
    ):
        Campaign.objects.create(brand=balanz_brand, name="Ours")
        Campaign.objects.create(brand=rival_brand, name="Theirs")

        response = authed_balanz.get(self.url)
        assert response.status_code == 200

        body = response.json()
        results = body if isinstance(body, list) else body["results"]
        names = {c["name"] for c in results}
        assert names == {"Ours"}

    def test_rival_tenant_sees_only_its_own(
        self, authed_rival, balanz_brand, rival_brand
    ):
        Campaign.objects.create(brand=balanz_brand, name="Ours")
        Campaign.objects.create(brand=rival_brand, name="Theirs")

        response = authed_rival.get(self.url)
        assert response.status_code == 200

        body = response.json()
        results = body if isinstance(body, list) else body["results"]
        names = {c["name"] for c in results}
        assert names == {"Theirs"}

    def test_empty_tenant_returns_empty_list(self, authed_balanz):
        response = authed_balanz.get(self.url)
        assert response.status_code == 200
        body = response.json()
        results = body if isinstance(body, list) else body["results"]
        assert results == []

    def test_list_uses_constant_query_count(
        self, authed_balanz, balanz_brand, django_assert_max_num_queries
    ):
        # Regression: stage_count / published_report_count / last_published_at
        # used to hit the DB per campaign (3 campañas → 9 queries extra).
        # Now they must come from annotations on the queryset.
        for i in range(3):
            c = Campaign.objects.create(brand=balanz_brand, name=f"C{i}")
            s = Stage.objects.create(campaign=c, order=1, name="S1", kind=Stage.Kind.OTHER)
            Report.objects.create(
                stage=s,
                kind=Report.Kind.MENSUAL,
                period_start=date.today() - timedelta(days=30),
                period_end=date.today(),
                status=Report.Status.PUBLISHED,
                published_at=timezone.now(),
            )

        with django_assert_max_num_queries(6):
            response = authed_balanz.get(self.url)

        assert response.status_code == 200
        body = response.json()
        results = body if isinstance(body, list) else body["results"]
        assert len(results) == 3
        for row in results:
            assert row["stage_count"] == 1
            assert row["published_report_count"] == 1
            assert row["last_published_at"] is not None
