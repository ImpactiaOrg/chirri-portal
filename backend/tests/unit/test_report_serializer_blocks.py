import pytest
from django.core.files.uploadedfile import SimpleUploadedFile

from apps.reports.models import ReportBlock
from apps.reports.serializers import ReportDetailSerializer

pytestmark = pytest.mark.django_db


def _kpi_block(report, order):
    return ReportBlock.objects.create(
        report=report, order=order, type="KPI_GRID",
        config={"tiles": [{"label": "Reach", "source": "reach_total"}]},
    )


def test_empty_blocks_serializes_as_empty_list(balanz_published_report):
    data = ReportDetailSerializer(balanz_published_report).data
    assert data["blocks"] == []


def test_blocks_serialize_in_order(balanz_published_report):
    _kpi_block(balanz_published_report, 3)
    _kpi_block(balanz_published_report, 1)
    _kpi_block(balanz_published_report, 2)

    data = ReportDetailSerializer(balanz_published_report).data
    orders = [b["order"] for b in data["blocks"]]
    assert orders == [1, 2, 3]
    for block in data["blocks"]:
        assert block["type"] == "KPI_GRID"
        assert "config" in block
        assert block["image_url"] is None


def test_original_pdf_url_null_when_empty(balanz_published_report):
    data = ReportDetailSerializer(balanz_published_report).data
    assert data["original_pdf_url"] is None


def test_original_pdf_url_populated(balanz_published_report):
    balanz_published_report.original_pdf = SimpleUploadedFile(
        "report.pdf", b"%PDF-1.4 payload", content_type="application/pdf",
    )
    balanz_published_report.save()
    data = ReportDetailSerializer(balanz_published_report).data
    assert data["original_pdf_url"] is not None
    assert data["original_pdf_url"].endswith(".pdf")
