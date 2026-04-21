import pytest
from django.core.management import call_command

from apps.reports.models import Report, ReportBlock

pytestmark = pytest.mark.django_db


def test_seed_demo_creates_blocks_for_full_reports():
    call_command("seed_demo", "--wipe")

    full_reports = Report.objects.filter(
        title="Reporte general · Marzo",
        stage__kind__in=["EDUCATION", "VALIDATION"],
    )
    assert full_reports.count() == 2
    for report in full_reports:
        blocks = list(report.blocks.order_by("order"))
        assert len(blocks) == 11, f"{report.title} has {len(blocks)} blocks"
        # Primer bloque siempre es KPI_GRID
        assert blocks[0].type == ReportBlock.Type.KPI_GRID
        # El último es METRICS_TABLE con Q1 rollup
        assert blocks[-1].type == ReportBlock.Type.METRICS_TABLE
        assert blocks[-1].config["source"] == "q1_rollup"
        # Orden es 1..11 consecutivo
        assert [b.order for b in blocks] == list(range(1, 12))
