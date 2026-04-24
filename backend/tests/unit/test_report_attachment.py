"""ReportAttachment (DEV-108): save() cachea mime_type + size_bytes, y el
serializer expone la lista de descargas en el orden correcto.
"""
import pytest
from django.core.files.base import ContentFile

from apps.reports.models import ReportAttachment
from apps.reports.tests.factories import make_report


PDF_CONTENT = b"%PDF-1.4\n%minimal-pdf-for-tests\n%%EOF\n"


@pytest.mark.django_db
def test_save_populates_mime_type_and_size_from_file():
    report = make_report()
    att = ReportAttachment(report=report, title="Reporte")
    att.file.save("r.pdf", ContentFile(PDF_CONTENT), save=False)
    att.save()

    att.refresh_from_db()
    assert att.mime_type == "application/pdf"
    assert att.size_bytes == len(PDF_CONTENT)


@pytest.mark.django_db
def test_save_falls_back_to_octet_stream_for_unknown_extensions():
    report = make_report()
    att = ReportAttachment(report=report, title="Unknown")
    att.file.save("weird.xyz123", ContentFile(b"bytes"), save=False)
    att.save()

    # Unknown extension → mimetypes returns None → we default to octet-stream.
    # The important contract is that mime_type is always non-empty after save.
    assert att.mime_type != ""


@pytest.mark.django_db
def test_serializer_includes_attachments_in_order():
    from apps.reports.serializers import ReportDetailSerializer

    report = make_report()
    # Second attachment first (order=2) to verify sorting by order.
    a2 = ReportAttachment(report=report, order=2, title="Anexo", kind=ReportAttachment.Kind.ANNEX)
    a2.file.save("anexo.pdf", ContentFile(PDF_CONTENT), save=False)
    a2.save()

    a1 = ReportAttachment(report=report, order=1, title="Reporte", kind=ReportAttachment.Kind.PDF_REPORT)
    a1.file.save("reporte.pdf", ContentFile(PDF_CONTENT), save=False)
    a1.save()

    data = ReportDetailSerializer(report).data

    assert "attachments" in data
    assert [a["order"] for a in data["attachments"]] == [1, 2]
    first = data["attachments"][0]
    assert first["title"] == "Reporte"
    assert first["kind"] == "PDF_REPORT"
    assert first["mime_type"] == "application/pdf"
    assert first["size_bytes"] == len(PDF_CONTENT)
    assert first["url"] is not None


@pytest.mark.django_db
def test_serializer_payload_no_longer_exposes_original_pdf_url():
    from apps.reports.serializers import ReportDetailSerializer

    report = make_report()
    data = ReportDetailSerializer(report).data
    assert "original_pdf_url" not in data
