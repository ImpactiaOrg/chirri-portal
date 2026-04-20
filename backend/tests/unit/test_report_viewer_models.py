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


from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from apps.reports.validators import validate_image_size, validate_image_mimetype


def test_validate_image_size_accepts_under_5mb():
    small = SimpleUploadedFile("x.jpg", b"x" * 100, content_type="image/jpeg")
    validate_image_size(small)


def test_validate_image_size_rejects_over_5mb():
    huge = SimpleUploadedFile("x.jpg", b"x" * (6 * 1024 * 1024), content_type="image/jpeg")
    with pytest.raises(ValidationError):
        validate_image_size(huge)


def test_validate_image_mimetype_accepts_jpeg():
    img = SimpleUploadedFile("x.jpg", b"x", content_type="image/jpeg")
    validate_image_mimetype(img)


def test_validate_image_mimetype_rejects_svg():
    svg = SimpleUploadedFile("x.svg", b"<svg/>", content_type="image/svg+xml")
    with pytest.raises(ValidationError):
        validate_image_mimetype(svg)
