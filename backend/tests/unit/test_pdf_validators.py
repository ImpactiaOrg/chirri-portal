import io
import pytest
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile

from apps.reports.validators import (
    MAX_PDF_SIZE_BYTES,
    validate_pdf_size,
    validate_pdf_mimetype,
)


def _pdf_file(size_bytes: int, content_type: str = "application/pdf"):
    return SimpleUploadedFile(
        name="report.pdf",
        content=b"0" * size_bytes,
        content_type=content_type,
    )


def test_validate_pdf_size_accepts_under_limit():
    validate_pdf_size(_pdf_file(1024))  # no raise


def test_validate_pdf_size_rejects_over_limit():
    with pytest.raises(ValidationError):
        validate_pdf_size(_pdf_file(MAX_PDF_SIZE_BYTES + 1))


def test_validate_pdf_mimetype_accepts_pdf():
    validate_pdf_mimetype(_pdf_file(10, "application/pdf"))


@pytest.mark.parametrize("bad_type", ["image/jpeg", "application/octet-stream", "text/plain"])
def test_validate_pdf_mimetype_rejects_non_pdf(bad_type):
    with pytest.raises(ValidationError):
        validate_pdf_mimetype(_pdf_file(10, bad_type))
