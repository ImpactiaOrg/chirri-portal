"""Tests unit para TextImageBlock — subtype post DEV-116.

Cubre defaults (columns=1, image_position=top), image validators, order
uniqueness dentro del Report. Gap identificado por code review — el spec
listaba 6 per-subtype test files pero solo existían 5.
"""
import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError


@pytest.mark.django_db
def test_text_image_block_defaults(report_factory):
    """columns=1 y image_position='top' son los defaults del spec."""
    from apps.reports.models import TextImageBlock
    report = report_factory()
    block = TextImageBlock.objects.create(report=report, order=1)
    assert block.columns == 1
    assert block.image_position == "top"
    assert block.title == ""  # blank default
    assert block.body == ""
    assert block.image_alt == ""
    assert not block.image  # blank ImageField is falsy


@pytest.mark.django_db
def test_text_image_block_columns_choices(report_factory):
    """columns solo acepta 1, 2, 3 — rejecta otros enteros."""
    from apps.reports.models import TextImageBlock
    report = report_factory()
    block = TextImageBlock(report=report, order=1, columns=4)
    with pytest.raises(ValidationError):
        block.full_clean()


@pytest.mark.django_db
def test_text_image_block_image_position_choices(report_factory):
    """image_position solo acepta left / right / top."""
    from apps.reports.models import TextImageBlock
    report = report_factory()
    block = TextImageBlock(report=report, order=1, image_position="bottom")
    with pytest.raises(ValidationError):
        block.full_clean()


@pytest.mark.django_db
def test_text_image_block_accepts_rich_body(report_factory):
    """body es TextField sin límite; acepta prosa larga."""
    from apps.reports.models import TextImageBlock
    report = report_factory()
    long_body = "lorem ipsum " * 1000
    block = TextImageBlock.objects.create(
        report=report, order=1, title="Hello", body=long_body,
    )
    assert block.body == long_body


@pytest.mark.django_db
def test_text_image_block_order_unique_per_report(report_factory):
    """UniqueConstraint(report, order) vía heredado de ReportBlock base."""
    from apps.reports.models import TextImageBlock
    report = report_factory()
    TextImageBlock.objects.create(report=report, order=1, title="A")
    with pytest.raises(IntegrityError):
        TextImageBlock.objects.create(report=report, order=1, title="B")


@pytest.mark.django_db
def test_text_image_block_image_alt_optional(report_factory):
    """image_alt es blank=True (sin imagen tampoco aplica)."""
    from apps.reports.models import TextImageBlock
    report = report_factory()
    block = TextImageBlock.objects.create(
        report=report, order=1, image_alt="Foto de apertura",
    )
    assert block.image_alt == "Foto de apertura"
