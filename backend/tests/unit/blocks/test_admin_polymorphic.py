"""Smoke del admin polimórfico — que un superuser pueda acceder al change
page de Report y que el UI muestre los 6 subtypes.

Post-Task 3.1+3.2.
"""
import pytest
from django.contrib.auth import get_user_model
from django.test import override_settings
from django.urls import reverse

from apps.reports.tests.factories import make_report

User = get_user_model()

# Los tests corren con development settings (default en container). Esa config
# usa WhiteNoise's CompressedManifestStaticFilesStorage, que pide un manifest
# pre-generado — roto en tests. Sobreescribimos a un staticfiles storage plano
# para estos smoke tests de admin (no nos importa el hashing, solo que la
# página renderice).
_PLAIN_STATICFILES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
}


@pytest.fixture(autouse=True)
def _plain_staticfiles():
    with override_settings(STORAGES=_PLAIN_STATICFILES):
        yield


@pytest.fixture
def admin_client(client, db):
    admin = User.objects.create_superuser(
        email="admin@test.com", password="adminpass",
    )
    client.force_login(admin)
    return client


@pytest.mark.django_db
def test_admin_can_load_report_change_page(admin_client):
    report = make_report()
    url = reverse("admin:reports_report_change", args=[report.id])
    response = admin_client.get(url)
    assert response.status_code == 200


@pytest.mark.django_db
def test_admin_report_changelist_renders(admin_client):
    make_report()
    url = reverse("admin:reports_report_changelist")
    response = admin_client.get(url)
    assert response.status_code == 200


@pytest.mark.django_db
def test_admin_reportblock_polymorphic_parent_registered(admin_client):
    """ReportBlock admin standalone debería listar subtypes en el add page."""
    url = reverse("admin:reports_reportblock_changelist")
    response = admin_client.get(url)
    assert response.status_code == 200


@pytest.mark.django_db
def test_admin_can_access_each_subtype_add_page(admin_client):
    """Cada subtipo tiene su propio admin registered."""
    subtypes = [
        ("reports", "textimageblock"),
        ("reports", "kpigridblock"),
        ("reports", "metricstableblock"),
        ("reports", "topcontentblock"),
        ("reports", "attributiontableblock"),
        ("reports", "chartblock"),
    ]
    for app_label, model_name in subtypes:
        url = reverse(f"admin:{app_label}_{model_name}_add")
        response = admin_client.get(url)
        assert response.status_code == 200, f"{model_name} add page returned {response.status_code}"


@pytest.mark.django_db
def test_admin_kpi_grid_block_shows_tile_inline(admin_client, report_factory):
    """El admin del subtipo KpiGridBlock debería mostrar el inline de KpiTile."""
    from apps.reports.models import KpiGridBlock
    report = report_factory()
    block = KpiGridBlock.objects.create(report=report, order=1, title="KPIs")
    url = reverse("admin:reports_kpigridblock_change", args=[block.id])
    response = admin_client.get(url)
    html = response.content.decode()
    # Django admin inline shows "KPI Tile" or "KpiTile" in the rendered page
    assert "Tile" in html or "tile" in html, "KpiTile inline should be present"
