import pytest
from django.core.exceptions import ValidationError

from apps.reports.models import Report, ReportBlock

pytestmark = pytest.mark.django_db


def test_create_report_block(balanz_published_report):
    block = ReportBlock.objects.create(
        report=balanz_published_report,
        type=ReportBlock.Type.KPI_GRID,
        order=1,
        config={"tiles": [{"label": "Reach", "source": "reach_total"}]},
    )
    assert block.pk is not None
    assert block.report_id == balanz_published_report.pk


def test_unique_order_per_report(balanz_published_report):
    # save() now calls full_clean() (see ReportBlock.save), which surfaces
    # the UniqueConstraint violation as a ValidationError at the Python
    # layer before hitting the DB IntegrityError. This is the intended
    # behavior — Django validates unique_together / UniqueConstraint inside
    # Model.validate_unique, which full_clean() runs.
    ReportBlock.objects.create(
        report=balanz_published_report, type="KPI_GRID", order=1,
        config={"tiles": [{"label": "R", "source": "reach_total"}]},
    )
    with pytest.raises(ValidationError):
        ReportBlock.objects.create(
            report=balanz_published_report, type="KPI_GRID", order=1,
            config={"tiles": [{"label": "R", "source": "reach_total"}]},
        )


def test_clean_rejects_invalid_config(balanz_published_report):
    block = ReportBlock(
        report=balanz_published_report,
        type=ReportBlock.Type.KPI_GRID,
        order=1,
        config={"tiles": []},
    )
    with pytest.raises(ValidationError):
        block.clean()


def test_clean_accepts_valid_config(balanz_published_report):
    block = ReportBlock(
        report=balanz_published_report,
        type=ReportBlock.Type.TEXT_IMAGE,
        order=1,
        config={"columns": 2, "image_position": "left"},
    )
    block.clean()  # no raise


def test_ordering_by_report_then_order(balanz_published_report):
    for i in (3, 1, 2):
        ReportBlock.objects.create(
            report=balanz_published_report, type="KPI_GRID", order=i,
            config={"tiles": [{"label": "R", "source": "reach_total"}]},
        )
    orders = list(
        ReportBlock.objects.filter(report=balanz_published_report).values_list("order", flat=True)
    )
    assert orders == [1, 2, 3]


def test_report_has_original_pdf_field():
    field = Report._meta.get_field("original_pdf")
    assert field.blank is True
    assert field.null is True
