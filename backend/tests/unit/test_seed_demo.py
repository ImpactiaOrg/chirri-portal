"""DEV-75 · Cobertura del comando `seed_demo`.

Es crítico para onboarding y para que la E2E funcione (crea al usuario
`belen.rizzo@balanz.com`), pero hasta ahora no tenía cobertura. Este módulo
verifica: (a) la forma de los datos seedeados, (b) la idempotencia del
`update_or_create` / `get_or_create`, (c) la semántica del flag `--wipe`.
"""
from __future__ import annotations

import pytest
from django.core.management import call_command

from apps.campaigns.models import Campaign, NarrativeLine, Stage
from apps.influencers.models import CampaignInfluencer, Influencer
from apps.reports.models import Report, ReportMetric
from apps.tenants.models import Brand, Client
from apps.users.models import ClientUser


@pytest.fixture
def seeded(db):
    call_command("seed_demo")


class TestSeedDemoShape:
    def test_creates_single_balanz_client(self, seeded):
        assert Client.objects.count() == 1
        client = Client.objects.get()
        assert client.name == "Balanz"
        assert client.primary_color == "#0B2D5B"

    def test_creates_single_brand_linked_to_balanz(self, seeded):
        assert Brand.objects.count() == 1
        brand = Brand.objects.get()
        assert brand.name == "Balanz"
        assert brand.client.name == "Balanz"

    def test_creates_belen_user_with_admin_role(self, seeded):
        user = ClientUser.objects.get(email="belen.rizzo@balanz.com")
        assert user.full_name == "Belén Rizzo"
        assert user.client.name == "Balanz"
        assert user.check_password("balanz2026")
        assert user.role == ClientUser.Role.ADMIN_CLIENT

    def test_creates_three_campaigns_one_active(self, seeded):
        assert Campaign.objects.count() == 3
        active = Campaign.objects.filter(status=Campaign.Status.ACTIVE)
        assert active.count() == 1
        assert active.get().name == "De Ahorrista a Inversor"

    def test_active_campaign_has_stages_and_narrative_lines(self, seeded):
        active = Campaign.objects.get(name="De Ahorrista a Inversor")
        assert active.stages.count() >= 1
        assert active.narrative_lines.count() >= 1

    def test_seeds_influencers_and_links_them_to_active_campaign(self, seeded):
        assert Influencer.objects.count() >= 1
        assert CampaignInfluencer.objects.count() >= 1
        active = Campaign.objects.get(name="De Ahorrista a Inversor")
        assert active.campaign_influencers.count() >= 1

    def test_seeds_at_least_one_published_report(self, seeded):
        published = Report.objects.filter(status=Report.Status.PUBLISHED)
        assert published.exists()
        assert ReportMetric.objects.exists()


class TestSeedDemoIdempotency:
    def test_running_twice_does_not_duplicate_tenants_or_user(self, seeded):
        call_command("seed_demo")
        assert Client.objects.count() == 1
        assert Brand.objects.count() == 1
        assert ClientUser.objects.filter(email="belen.rizzo@balanz.com").count() == 1

    def test_running_twice_keeps_campaign_count_stable(self, seeded):
        campaigns_before = Campaign.objects.count()
        stages_before = Stage.objects.count()
        narrative_before = NarrativeLine.objects.count()
        call_command("seed_demo")
        assert Campaign.objects.count() == campaigns_before
        assert Stage.objects.count() == stages_before
        assert NarrativeLine.objects.count() == narrative_before


class TestSeedDemoWipe:
    def test_wipe_removes_balanz_and_reseeds_cleanly(self, seeded):
        # Mutate something so we can prove --wipe actually reset it.
        Client.objects.filter(name="Balanz").update(primary_color="#FF00FF")

        call_command("seed_demo", wipe=True)

        assert Client.objects.count() == 1
        client = Client.objects.get()
        assert client.primary_color == "#0B2D5B"

    def test_wipe_does_not_delete_other_tenants(self, seeded):
        other = Client.objects.create(name="Plataforma Diez", primary_color="#123456")
        call_command("seed_demo", wipe=True)
        assert Client.objects.filter(pk=other.pk).exists()
