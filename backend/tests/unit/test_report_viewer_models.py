import pytest
from apps.reports.models import Report

pytestmark = pytest.mark.django_db


def test_report_intro_text_defaults_to_empty(balanz_published_report):
    assert balanz_published_report.intro_text == ""


def test_report_intro_text_can_be_set(balanz_published_report):
    balanz_published_report.intro_text = "Bienvenidos al reporte."
    balanz_published_report.save()
    balanz_published_report.refresh_from_db()
    assert balanz_published_report.intro_text == "Bienvenidos al reporte."
