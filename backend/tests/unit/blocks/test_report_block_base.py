"""Tests para ReportBlock base post-DEV-116.

Verifica que ReportBlock ahora es PolymorphicModel, tiene campos base
(report, order, instructions, timestamps) y NO tiene los campos viejos
(type, config, image).
"""
import pytest
from django.db import IntegrityError


@pytest.mark.django_db
def test_report_block_is_polymorphic_model():
    from polymorphic.models import PolymorphicModel
    from apps.reports.models import ReportBlock
    assert issubclass(ReportBlock, PolymorphicModel)


@pytest.mark.django_db
def test_report_block_base_fields_exist():
    from apps.reports.models import ReportBlock
    fields = {f.name for f in ReportBlock._meta.get_fields()}
    assert {"report", "order", "instructions", "created_at", "updated_at"}.issubset(fields)


@pytest.mark.django_db
def test_report_block_old_fields_gone():
    from apps.reports.models import ReportBlock
    fields = {f.name for f in ReportBlock._meta.get_fields()}
    assert "config" not in fields
    assert "type" not in fields
    assert "image" not in fields


@pytest.mark.django_db
def test_report_block_uniq_order_per_report(report_factory):
    """El constraint UniqueConstraint(report, order) sigue vigente.
    TextImageBlock se crea en Task 2.3 — test va a fallar con ImportError
    hasta entonces."""
    from apps.reports.models import TextImageBlock
    report = report_factory()
    TextImageBlock.objects.create(report=report, order=1, title="A")
    with pytest.raises(IntegrityError):
        TextImageBlock.objects.create(report=report, order=1, title="B")


@pytest.mark.django_db
def test_instructions_field_defaults_blank(report_factory):
    """TextImageBlock.instructions (heredado de la base) default a ''."""
    from apps.reports.models import TextImageBlock
    report = report_factory()
    block = TextImageBlock.objects.create(report=report, order=1)
    assert block.instructions == ""
