"""Tests de ImageBlock (DEV-130)."""
from io import BytesIO

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image


def _png_bytes() -> bytes:
    """Un PNG 1x1 mínimo válido para que pase validate_image_mimetype."""
    buf = BytesIO()
    Image.new("RGB", (1, 1), color="red").save(buf, format="PNG")
    return buf.getvalue()


@pytest.mark.django_db
def test_image_block_creates_with_overlay(report_factory):
    from apps.reports.models import ImageBlock
    report = report_factory()
    block = ImageBlock.objects.create(
        report=report, order=1,
        title="Cierre",
        caption="El mes en fotos.",
        overlay_position="bottom",
        image=SimpleUploadedFile("hero.png", _png_bytes(), content_type="image/png"),
    )
    assert block.title == "Cierre"
    assert block.overlay_position == "bottom"
    assert block.image.name.endswith(".png")


@pytest.mark.django_db
def test_image_block_overlay_choices_rejects_invalid(report_factory):
    from django.core.exceptions import ValidationError
    from apps.reports.models import ImageBlock
    report = report_factory()
    block = ImageBlock(
        report=report, order=1,
        overlay_position="left",  # not a valid choice
        image=SimpleUploadedFile("hero.png", _png_bytes(), content_type="image/png"),
    )
    with pytest.raises(ValidationError):
        block.full_clean()


@pytest.mark.django_db
def test_image_block_serialized_shape(report_factory):
    from apps.reports.models import ImageBlock
    from apps.reports.serializers import ImageBlockSerializer
    report = report_factory()
    block = ImageBlock.objects.create(
        report=report, order=1,
        title="Mes en fotos",
        caption="Highlights.",
        overlay_position="center",
        image_alt="collage",
        image=SimpleUploadedFile("hero.png", _png_bytes(), content_type="image/png"),
    )
    data = ImageBlockSerializer(block).data
    assert data["type"] == "ImageBlock"
    assert data["overlay_position"] == "center"
    assert data["title"] == "Mes en fotos"
    assert data["image_url"] is not None
