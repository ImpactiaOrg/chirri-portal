"""Tests del modelo Section."""
import pytest

from apps.reports.models import Section
from apps.reports.tests.factories import make_report


@pytest.mark.django_db
def test_section_can_be_created_with_pill_and_layout():
    report = make_report()
    s = Section.objects.create(
        report=report, order=1, title="KPIs del mes",
        layout=Section.Layout.STACK,
    )
    assert s.report_id == report.id
    assert s.title == "KPIs del mes"
    assert s.layout == "stack"


@pytest.mark.django_db
def test_section_default_layout_is_stack():
    report = make_report()
    s = Section.objects.create(report=report, order=1)
    assert s.layout == Section.Layout.STACK


@pytest.mark.django_db
def test_section_supports_columns_layouts():
    report = make_report()
    Section.objects.create(report=report, order=1, layout=Section.Layout.COLUMNS_2)
    Section.objects.create(report=report, order=2, layout=Section.Layout.COLUMNS_3)
    layouts = list(Section.objects.filter(report=report).values_list("layout", flat=True))
    assert "columns_2" in layouts
    assert "columns_3" in layouts


@pytest.mark.django_db
def test_section_order_is_unique_per_report():
    from django.db import IntegrityError, transaction
    report = make_report()
    Section.objects.create(report=report, order=1)
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            Section.objects.create(report=report, order=1)


@pytest.mark.django_db
def test_section_title_is_optional():
    report = make_report()
    s = Section.objects.create(report=report, order=1)
    assert s.title == ""
