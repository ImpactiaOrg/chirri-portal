"""Admin integration del importer/exporter xlsx (DEV-83 · Etapa 2).

Verifica que los 3 endpoints del admin (download-template, download-example,
import) funcionan end-to-end, respetan permisos, y que el import crea un
Report DRAFT con rollback si algo falla.
"""
from datetime import date

import pytest
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse

from apps.reports.importers.excel_exporter import export
from apps.reports.importers.excel_writer import build_template
from apps.reports.models import (
    ImageBlock,
    Report,
    TextImageBlock,
)
from apps.reports.tests.factories import make_stage


@pytest.fixture
def superuser(db):
    User = get_user_model()
    return User.objects.create_superuser(email="admin-tester@x.com", password="pass")


@pytest.fixture
def staff_no_perms(db):
    User = get_user_model()
    return User.objects.create_user(
        email="staff-no-perms@x.com", password="pass", is_staff=True,
    )


@pytest.fixture
def minimal_report(db):
    """Report con 1 TextImageBlock + 1 ImageBlock (para probar download_example)."""
    from django.core.files.base import ContentFile
    stage = make_stage()
    report = Report.objects.create(
        stage=stage, kind=Report.Kind.MENSUAL,
        period_start=date(2026, 4, 1), period_end=date(2026, 4, 30),
        title="Minimal", intro_text="", conclusions_text="",
        status=Report.Status.DRAFT,
    )
    TextImageBlock.objects.create(
        report=report, order=1, title="Intro", body="B",
        image_position="top", columns=1,
    )
    img = ImageBlock(report=report, order=2, title="Hero", caption="")
    img.image.save("hero.jpg", ContentFile(b"fake"), save=False)
    img.save()
    return report


# ---------------------------------------------------------------------------
# Download template
# ---------------------------------------------------------------------------
def test_download_template_requires_permission(client, db):
    url = reverse("admin:reports_report_download_template")
    resp = client.get(url)
    assert resp.status_code in (302, 403)  # admin redirect to login or deny


def test_download_template_works_for_superuser(client, superuser):
    client.force_login(superuser)
    url = reverse("admin:reports_report_download_template")
    resp = client.get(url)
    assert resp.status_code == 200
    assert "xlsx" in resp["Content-Type"] or "spreadsheetml" in resp["Content-Type"]
    assert b"PK" in resp.content[:4]  # xlsx es un zip → magic bytes PK
    assert "reporte-template.xlsx" in resp["Content-Disposition"]


# ---------------------------------------------------------------------------
# Download example (per-report export)
# ---------------------------------------------------------------------------
def test_download_example_works_for_superuser(client, superuser, minimal_report):
    client.force_login(superuser)
    url = reverse(
        "admin:reports_report_download_example", args=[minimal_report.pk],
    )
    resp = client.get(url)
    assert resp.status_code == 200
    assert b"PK" in resp.content[:4]
    assert f"reporte-{minimal_report.pk}-export.xlsx" in resp["Content-Disposition"]


def test_download_example_404_on_missing_report(client, superuser):
    client.force_login(superuser)
    url = reverse("admin:reports_report_download_example", args=[999_999])
    resp = client.get(url)
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Import
# ---------------------------------------------------------------------------
def test_import_get_shows_form(client, superuser):
    client.force_login(superuser)
    url = reverse("admin:reports_report_import")
    resp = client.get(url)
    assert resp.status_code == 200
    assert b"Importar reporte desde Excel" in resp.content
    assert b"Descargar template" in resp.content


def test_import_post_valid_xlsx_creates_draft(client, superuser, minimal_report):
    """Roundtrip: export(minimal_report) → admin POST → nuevo Report DRAFT."""
    client.force_login(superuser)
    # Generar xlsx exportado del report existente; la columna `imagen` del
    # ImageBlock lo hace relevante pero solo con xlsx pelado (sin ZIP) el
    # parser espera que no haya imágenes referenciadas. Usamos minimal_report
    # pero borramos su ImageBlock para simplificar.
    ImageBlock.objects.filter(report=minimal_report).delete()
    xlsx_bytes = export(minimal_report).getvalue()

    upload = SimpleUploadedFile(
        "reporte-abril.xlsx", xlsx_bytes,
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )

    pre_count = Report.objects.count()
    url = reverse("admin:reports_report_import")
    resp = client.post(url, _cascade_payload(minimal_report, file=upload))

    # Debe redirigir al change form del nuevo report
    assert resp.status_code == 302
    assert Report.objects.count() == pre_count + 1
    new_report = Report.objects.exclude(pk=minimal_report.pk).order_by("-pk").first()
    assert new_report.status == Report.Status.DRAFT
    assert str(new_report.pk) in resp["Location"]


def test_import_post_invalid_xlsx_re_renders_with_errors(client, superuser, minimal_report):
    """Upload sin scalars obligatorios → errors visibles, DB intacta."""
    client.force_login(superuser)
    # Template vacío no tiene tipo/fechas → parser falla
    empty_xlsx = build_template().getvalue()
    upload = SimpleUploadedFile("vacio.xlsx", empty_xlsx)
    pre_count = Report.objects.count()

    url = reverse("admin:reports_report_import")
    resp = client.post(url, _cascade_payload(minimal_report, file=upload))

    assert resp.status_code == 200
    assert Report.objects.count() == pre_count
    assert b"error" in resp.content.lower()
    # La tabla de errores menciona "tipo" y "fecha_inicio" como obligatorios
    assert b"obligatorio" in resp.content.lower()


def test_import_rejects_bad_extension(client, superuser, minimal_report):
    client.force_login(superuser)
    upload = SimpleUploadedFile("malo.txt", b"no soy un xlsx")
    url = reverse("admin:reports_report_import")
    resp = client.post(url, _cascade_payload(minimal_report, file=upload))
    # El FileExtensionValidator debería rechazar .txt
    assert resp.status_code == 200
    text = resp.content.decode(errors="ignore").lower()
    assert "txt" in text or "extensión" in text or "extension" in text


def test_import_requires_add_permission(client, staff_no_perms, minimal_report):
    client.force_login(staff_no_perms)
    url = reverse("admin:reports_report_import")
    resp = client.get(url)
    assert resp.status_code == 403


def test_changelist_shows_buttons(client, superuser):
    client.force_login(superuser)
    url = reverse("admin:reports_report_changelist")
    resp = client.get(url)
    assert resp.status_code == 200
    assert b"Descargar template" in resp.content
    assert b"Importar desde Excel" in resp.content


def test_change_form_shows_download_button(client, superuser, minimal_report):
    client.force_login(superuser)
    url = reverse("admin:reports_report_change", args=[minimal_report.pk])
    resp = client.get(url)
    assert resp.status_code == 200
    assert b"Descargar como Excel" in resp.content


def test_cascade_endpoint_returns_brands_of_client(client, superuser, minimal_report):
    client.force_login(superuser)
    cli = minimal_report.stage.campaign.brand.client
    url = reverse("admin:reports_report_import_cascade", args=["brand"])
    resp = client.get(url, {"parent": cli.pk})
    assert resp.status_code == 200
    data = resp.json()
    ids = [r["id"] for r in data["results"]]
    assert minimal_report.stage.campaign.brand.pk in ids


def test_import_rejects_mismatched_hierarchy(client, superuser, minimal_report, db):
    """Stage de una campaña distinta a la elegida → form invalido."""
    from apps.campaigns.models import Campaign, Stage
    # Creamos una campaña extra dentro del MISMO brand para no chocar con la
    # UNIQUE de Client.name, pero Stage fuera de la campaña elegida.
    other_campaign = Campaign.objects.create(
        brand=minimal_report.stage.campaign.brand,
        name="Otra campaña", status=Campaign.Status.ACTIVE,
        start_date=minimal_report.stage.campaign.start_date,
    )
    other_stage = Stage.objects.create(
        campaign=other_campaign, order=1, name="Otra etapa",
        kind=Stage.Kind.AWARENESS,
    )
    client.force_login(superuser)
    upload = SimpleUploadedFile("ok.xlsx", build_template().getvalue())
    url = reverse("admin:reports_report_import")
    resp = client.post(url, {
        "client": minimal_report.stage.campaign.brand.client.pk,
        "brand": minimal_report.stage.campaign.brand.pk,
        "campaign": minimal_report.stage.campaign.pk,
        "stage": other_stage.pk,  # pertenece a other_campaign, no a la elegida
        "file": upload,
    })
    assert resp.status_code == 200
    assert b"no pertenece" in resp.content


def _cascade_payload(minimal_report, *, file):
    """Arma el POST completo de ImportReportForm desde un Report existente."""
    stage = minimal_report.stage
    return {
        "client": stage.campaign.brand.client.pk,
        "brand": stage.campaign.brand.pk,
        "campaign": stage.campaign.pk,
        "stage": stage.pk,
        "file": file,
    }
